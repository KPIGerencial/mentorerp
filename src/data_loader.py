"""
data_loader.py
==============
Camada única de acesso aos dados. Toda a aplicação lê a planilha Excel
através deste módulo — se a estrutura da planilha mudar (novas colunas,
nova aba), o ajuste é feito aqui, não em cada página.

A planilha é tratada como "banco de dados": cada aba = uma tabela.
"""

from io import BytesIO
import os
import re
import zipfile
import pandas as pd
import requests
import streamlit as st

# Planilha oficial agora vive no Dropbox (não mais no Google Sheets nem em
# /data) — cada tabela que antes era uma aba dentro de UM arquivo grande
# agora é um arquivo .xlsx próprio, hospedado separadamente. A fonte
# principal ("KPIS - COLHEITA - TRANSPORTE (OK)") ainda concentra várias
# abas (transporte, colhedora, transbordo, disponibilidade, diesel,
# colheita, meses, empresas, prod) — só ATR, Cidades e Estimativas viraram
# arquivos isolados.
# IMPORTANTE: os links precisam continuar com o compartilhamento público
# ativo (o "Qualquer pessoa com o link"/"dl=0" do Dropbox), senão o
# download falha.
#
# DEPLOY (Render): os links abaixo são usados como FALLBACK apenas. Em
# produção, defina as variáveis de ambiente DROPBOX_URL_PRINCIPAL,
# DROPBOX_URL_ATR, DROPBOX_URL_CIDADES, DROPBOX_URL_ESTIMATIVAS,
# DROPBOX_URL_AGR500 e DROPBOX_URL_HISTORICO no painel do Render
# (Environment > Environment Variables) ou em st.secrets — assim os links
# não ficam expostos no código-fonte/repositório.


def _env_ou_secret(nome: str, padrao: str) -> str:
    """Busca a URL primeiro em variável de ambiente, depois em st.secrets,
    e só usa o valor padrão (hardcoded) se nenhum dos dois existir."""
    valor = os.environ.get(nome)
    if valor:
        return valor
    try:
        if nome in st.secrets:
            return st.secrets[nome]
    except Exception:
        pass
    return padrao


DROPBOX_URLS = {
    "principal": _env_ou_secret("DROPBOX_URL_PRINCIPAL", "https://www.dropbox.com/scl/fi/qyibfra2pwjringkn56zc/KPIS-COLHEITA-TRANSPORTE-OK.xlsx?rlkey=2fuzztvrp1fhdnhre1d8u6ofa&st=yk0c19n4&dl=0"),
    "atr": _env_ou_secret("DROPBOX_URL_ATR", "https://www.dropbox.com/scl/fi/wp0w65huafqxcjvya5mfv/BASE-ART.xlsx?rlkey=9ajpm980q32nk6v4y1a9juyxl&st=jo1lx6yo&dl=0"),
    "cidades": _env_ou_secret("DROPBOX_URL_CIDADES", "https://www.dropbox.com/scl/fi/i4cq9o0zz4j5ilg038zbu/CIDADES.xlsx?rlkey=kfwjiwe8gmw7hkozctdnftc56&st=an94j4xh&dl=0"),
    "estimativas": _env_ou_secret("DROPBOX_URL_ESTIMATIVAS", "https://www.dropbox.com/scl/fi/juzhvc09rubcg7t9lbthg/BASE-ESTIMATIVAS.xlsx?rlkey=dg9a2bw32mnau27xqhn9ehwez&st=c0yau0nh&dl=0"),
    "agr500": _env_ou_secret("DROPBOX_URL_AGR500", "https://www.dropbox.com/scl/fi/yycoxxbndjkozd6zjjjuj/AGR500.xlsx?rlkey=uj7ste99lenguy4gl9lzkg9m8&st=fqt1ogm1&dl=0"),
}

# Planilha separada com o histórico de safras (página "Histórico de Safras").
DROPBOX_HISTORICO_URL = _env_ou_secret("DROPBOX_URL_HISTORICO", "https://www.dropbox.com/scl/fi/oe9ohm3i50rsicqd4zeco/SAFRAS-COLHEITA.xlsx?rlkey=0q8sjloinpae2jw6d9o07ve3q&st=3itilh6e&dl=0")

# A planilha é lida exclusivamente do Dropbox (ou de um upload manual feito
# na hora, na barra lateral) — sem arquivo .xlsx embutido no projeto.


def _dropbox_direct(url: str) -> str:
    """Converte um link de compartilhamento do Dropbox (.../arquivo.xlsx?...&dl=0)
    num link de download direto (dl=1), que devolve os bytes do arquivo em vez
    da página de preview do Dropbox."""
    if "dropbox.com" not in url:
        return url
    if "dl=0" in url:
        return url.replace("dl=0", "dl=1")
    if "dl=1" in url:
        return url
    separador = "&" if "?" in url else "?"
    return f"{url}{separador}dl=1"

# Cada chave lógica lista TODOS os nomes de aba já vistos para ela — a
# planilha nova trocou a caixa de várias abas (ex: "BaseTransporte" em vez de
# "BASETRANSPORTE") e a aba de ATR mudou de "BASEATR" para "BASEART". A
# busca abaixo é sempre case-insensitive, então "BaseTransporte" já bate com
# o candidato "BASETRANSPORTE" — as variações extras aqui cobrem mudanças de
# singular/plural e grafias que a caixa sozinha não resolve.
SHEETS = {
    "transporte": ["BASETRANSPORTE", "BASE TRANSPORTE"],
    "colhedora": ["BASECOLHEDORA", "BASECOLHEDORAS", "BASE COLHEDORA", "BASE COLHEDORAS"],
    "transbordo": ["BASETRANSBORDO", "BASE TRANSBORDO"],
    "disponibilidade": ["DISPONIBILIDADE"],
    "diesel": ["BASEDIESEL", "BASE DIESEL"],
    "colheita": ["COLHEITA"],  # fallback: se não achar essa aba isolada, get_data() monta a partir do Histórico de Safras (ver _build_colheita_de_safras)
    "estimativa": ["ESTIMATIVA", "ESTIMATIVAS", "BASE ESTIMATIVAS", "BASE-ESTIMATIVAS"],  # a planilha nova usa "ESTIMATIVAS" (plural)
    "meses": ["MES", "MESES"],
    "empresas": ["BASEEMPRESA", "BASE EMPRESA"],
    "prod": ["PROD.", "PROD", "PRODUCAO", "PRODUÇÃO", "AGR500"],  # a planilha nova usa "AGR500"
    "atr": ["BASEATR", "BASEART", "BASE ATR", "BASE ART"],  # a planilha nova usa "BASEART"
}

# Nome da aba com o cruzamento Cidade x Estado (UF) — usada para agregar o
# mapa por estado. O nome exato pode variar, por isso a busca abaixo é
# case-insensitive e cobre as variações mais comuns (a planilha nova usa "CIDADES").
CIDADE_SHEET_CANDIDATES = ["CLIMA", "CIDADE", "CIDADES", "UF", "Estados", "Cidade x Estado"]  # a planilha nova usa "CLIMA"

# Na aba BASEATR/BASEART, a coluna que identifica a fazenda vem como "Fundo
# Agrícola" (a planilha nova não tem coluna "Fazenda" nessa aba) — tratado
# como equivalente a Fazenda para o cruzamento com o Histórico de Safras.
ATR_FAZENDA_CANDIDATES = ["Fazenda", "Cod. fazenda", "Código Fazenda", "Fundo Agrícola", "Fundo Agricola"]


def _find_sheet(sheet_names_lower: dict, candidatos: list) -> str | None:
    """Localiza o nome real de uma aba a partir de uma lista de candidatos,
    ignorando maiúsculas/minúsculas e espaços nas pontas."""
    for candidato in candidatos:
        real = sheet_names_lower.get(candidato.strip().lower())
        if real is not None:
            return real
    return None


def _clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [str(c).strip() for c in df.columns]
    return df


def _e_arquivo_xlsx_unico(zf: zipfile.ZipFile) -> bool:
    """Um .xlsx é, por baixo dos panos, também um .zip (formato Office Open
    XML) — pra não confundir um .xlsx único com uma pasta zipada de vários
    arquivos (ex: pasta do Dropbox baixada com `dl=1`), procura a marca
    registrada da estrutura interna de um xlsx."""
    nomes = zf.namelist()
    return "[Content_Types].xml" in nomes or any(n.startswith("xl/") for n in nomes)


def _extrair_workbooks(file_bytes_or_path) -> list:
    """Devolve uma lista de fontes prontas para pd.ExcelFile.

    Se `file_bytes_or_path` for bytes de um .zip que É uma PASTA zipada com
    vários arquivos dentro (ex: uma pasta do Dropbox baixada com o parâmetro
    `dl=1` — o Dropbox zippa a pasta inteira nesse caso), extrai todo
    `.xlsx` de dentro e devolve um BytesIO para cada um. Caso contrário (um
    único .xlsx, em bytes ou caminho — um .xlsx TAMBÉM é um .zip por dentro,
    por isso a checagem extra), devolve só ele.
    """
    if isinstance(file_bytes_or_path, (bytes, bytearray)):
        buf = BytesIO(file_bytes_or_path)
        if zipfile.is_zipfile(buf):
            with zipfile.ZipFile(buf) as zf:
                if not _e_arquivo_xlsx_unico(zf):
                    workbooks = []
                    for nome in zf.namelist():
                        if nome.lower().endswith(".xlsx") and "__MACOSX" not in nome:
                            workbooks.append(BytesIO(zf.read(nome)))
                    return workbooks
        return [BytesIO(file_bytes_or_path)]
    return [file_bytes_or_path]


def _ler_abas_de_um_workbook(fonte, data: dict) -> None:
    """Lê as abas reconhecidas de UM workbook e preenche `data` — só grava
    uma chave que ainda não tenha sido encontrada em outro workbook (o
    primeiro arquivo, entre vários, que tiver a aba "ganha")."""
    try:
        xls = pd.ExcelFile(fonte)
    except Exception:
        return
    sheet_names_lower = {s.strip().lower(): s for s in xls.sheet_names}

    for key, candidatos in SHEETS.items():
        if key in data:
            continue
        sheet_name = _find_sheet(sheet_names_lower, candidatos)
        if sheet_name is None:
            continue
        df = pd.read_excel(xls, sheet_name=sheet_name)
        df = _clean_columns(df)
        df = df.dropna(how="all")
        data[key] = df

    if "cidade_uf" not in data:
        cidade_sheet = _find_sheet(sheet_names_lower, CIDADE_SHEET_CANDIDATES)
        if cidade_sheet is not None:
            df_cidade = pd.read_excel(xls, sheet_name=cidade_sheet)
            data["cidade_uf"] = _clean_columns(df_cidade).dropna(how="all")


def load_excel(file_bytes_or_path) -> dict:
    """Lê todas as abas relevantes e devolve um dict {nome_logico: DataFrame}.

    Aceita: um caminho (str), os bytes brutos de um único .xlsx, OU os bytes
    de um .zip contendo vários .xlsx (ex: uma pasta do Dropbox baixada com
    `dl=1`) — nesse caso, cada aba reconhecida pode vir de um arquivo
    diferente dentro da pasta (a busca por aba já é feita em todos).

    Receber bytes (em vez de um objeto de arquivo/BytesIO já aberto) é o que
    permite ao st.cache_data reconhecer quando o conteúdo baixado não mudou
    e pular o reparsing do(s) workbook(s) inteiro(s) a cada rerun — é o
    ganho de performance real da troca de fonte de dados.
    """
    data = {}
    for workbook in _extrair_workbooks(file_bytes_or_path):
        _ler_abas_de_um_workbook(workbook, data)
    return _normalizar(data)


def _normalizar(data: dict) -> dict:
    """Aplica as normalizações pontuais (datas, nomes de coluna, coluna Mês
    derivada) — chamada tanto por load_excel (upload manual) quanto por
    get_data (download multi-arquivo do Dropbox)."""
    # --- normalizações pontuais ---
    if "transporte" in data:
        data["transporte"]["Data"] = pd.to_datetime(data["transporte"]["Data"], errors="coerce")
    if "colhedora" in data:
        data["colhedora"]["Data"] = pd.to_datetime(data["colhedora"]["Data"], errors="coerce")
    if "transbordo" in data:
        data["transbordo"]["Data"] = pd.to_datetime(data["transbordo"]["Data"], errors="coerce")
    if "diesel" in data and "DATA" in data["diesel"].columns:
        data["diesel"]["DATA"] = pd.to_datetime(data["diesel"]["DATA"], errors="coerce")
    if "colheita" in data:
        for col in ("Data Ultima Entrega",):
            if col in data["colheita"].columns:
                data["colheita"][col] = pd.to_datetime(
                    data["colheita"][col], errors="coerce", dayfirst=True
                )
    if "estimativa" in data:
        for col in ("Data Colheita/Plantio",):
            if col in data["estimativa"].columns:
                data["estimativa"][col] = pd.to_datetime(
                    data["estimativa"][col], errors="coerce", dayfirst=True
                )
    if "atr" in data and "Data Produção" in data["atr"].columns:
        data["atr"]["Data Produção"] = pd.to_datetime(
            data["atr"]["Data Produção"], errors="coerce", dayfirst=True
        )
    # A aba BASETRANSPORTE traz a coluna de empresa como "EMPRESA" (maiúsculas),
    # mas as páginas do dashboard leem "Empresa" — normaliza aqui, na fonte
    # única dos dados, para não precisar editar cada página que usa esse campo.
    if "transporte" in data and "EMPRESA" in data["transporte"].columns and "Empresa" not in data["transporte"].columns:
        data["transporte"] = data["transporte"].rename(columns={"EMPRESA": "Empresa"})

    # Várias páginas filtram por "Mês" (abreviação em português: jan, fev...),
    # mas nem toda aba (ex: BaseColhedoras) traz essa coluna pronta — deriva
    # a partir de "Data" quando existir, pra não quebrar o filtro.
    _MESES_PT = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
    for chave in ("transporte", "colhedora", "transbordo"):
        if chave in data and "Mês" not in data[chave].columns and "Data" in data[chave].columns:
            data[chave]["Mês"] = data[chave]["Data"].dt.month.map(
                lambda m: _MESES_PT[m - 1] if pd.notna(m) else None
            )

    # A coluna que identifica o equipamento, na aba Disponibilidade, pode
    # vir com nomes diferentes conforme a planilha — resolve para
    # "Equipamento" a partir do primeiro candidato encontrado.
    if "disponibilidade" in data and "Equipamento" not in data["disponibilidade"].columns:
        col_equip = _find_column(
            data["disponibilidade"],
            ["Equipamento", "Modelo Equipamento", "Frota", "Código", "Ativo", "Máquina", "ID Equipamento", "Placa"],
        )
        if col_equip is not None:
            data["disponibilidade"] = data["disponibilidade"].rename(columns={col_equip: "Equipamento"})

    return data


@st.cache_data(ttl=600, show_spinner="Baixando planilha do Dropbox...")
def _download_dropbox_bytes(url: str) -> bytes:
    resp = requests.get(_dropbox_direct(url), timeout=30)
    resp.raise_for_status()
    return resp.content


def get_data(quiet: bool = False) -> dict:
    """
    Ponto único usado pelas páginas.
    Prioridade: arquivo enviado pelo usuário na sessão (upload manual, feito
    na hora — não fica salvo no projeto) > arquivos do Dropbox (fonte
    única, um .xlsx por tabela — ver DROPBOX_URLS). Sem fallback para
    arquivo local: se algum link do Dropbox falhar, a página para com uma
    mensagem clara em vez de mostrar dado desatualizado.

    quiet=True: não chama st.error()/st.stop() em caso de falha — em vez
    disso relança a exceção, para chamadores que precisam de uma tentativa
    "silenciosa" e não podem travar a página (ex: tela de login, que roda
    ANTES do usuário entrar e não pode depender da planilha estar no ar).
    """
    uploaded = st.session_state.get("uploaded_file")
    if uploaded is not None:
        return load_excel(uploaded.getvalue())

    data = {}
    try:
        for url in DROPBOX_URLS.values():
            conteudo = _download_dropbox_bytes(url)
            for workbook in _extrair_workbooks(conteudo):
                _ler_abas_de_um_workbook(workbook, data)

        # A aba "COLHEITA" isolada não existe mais na planilha principal — os
        # dados de colheita agora vivem na planilha de Histórico de Safras
        # (uma aba por ano: 2026, 2025, 2024...), com as mesmas colunas que a
        # Visão Geral já espera (Total Área O.S., TCH Real, % Variação TCH,
        # Data Ultima Entrega...). Só busca aqui se não achou de outro jeito,
        # reaproveitando o cache de _download_dropbox_bytes (mesma URL que
        # get_historico_safras() já usa, sem custo extra de rede).
        if "colheita" not in data:
            conteudo_hist = _download_dropbox_bytes(DROPBOX_HISTORICO_URL)
            colheita_hist = _build_colheita_de_safras(_extrair_workbooks(conteudo_hist))
            if not colheita_hist.empty:
                data["colheita"] = colheita_hist
    except Exception:
        if quiet:
            raise
        st.error(
            "Não foi possível ler uma das planilhas do Dropbox. Verifique se os "
            "links continuam com o compartilhamento público ativo (qualquer "
            "pessoa com o link pode visualizar). Ou envie o arquivo manualmente "
            "na barra lateral, em 'Fonte de dados'."
        )
        st.stop()

    return _normalizar(data)


# Colunas esperadas na página Histórico de Safras (Fazenda | Setor |
# Toneladas | TCH | ATR | Safra | Área Colhida). Cada entrada lista os nomes
# possíveis para aquela coluna na planilha — a busca é case-insensitive.
HISTORICO_COLUMN_CANDIDATES = {
    "Fazenda": ["Fazenda", "Cod. fazenda", "Código Fazenda"],
    "Setor": ["Setor"],
    "Safra": ["Safra"],
    "Toneladas": ["Toneladas", "Tonelada Real", "Prod. Real", "Produção"],
    "TCH": ["TCH", "TCH Real", "TCH Estimado"],
    "Área Colhida": ["Área Colhida", "Area Colhida", "Total Área O.S."],
}


def _find_column(df: pd.DataFrame, candidatos: list) -> str | None:
    cols_lower = {str(c).strip().lower(): c for c in df.columns}
    for candidato in candidatos:
        real = cols_lower.get(candidato.lower())
        if real is not None:
            return real
    return None


def _ano_do_nome_aba(nome: str) -> int | None:
    """Extrai um ano de 4 dígitos (20xx) do nome da aba, ex: 'SAFRA 2026' -> 2026."""
    m = re.search(r"(20\d{2})", str(nome))
    return int(m.group(1)) if m else None


def _safra_da_aba(nome: str) -> str | None:
    """Converte o nome da aba (ano) no rótulo de Safra no formato
    'AAAA/AAAA+1' — regra fixa da planilha de Histórico de Safras: a aba
    '2026' representa a safra '2026/2027', '2025' representa '2025/2026',
    e assim por diante (sempre o ano seguinte). Devolve None se o nome da
    aba não tiver um ano reconhecível."""
    ano = _ano_do_nome_aba(nome)
    return f"{ano}/{ano + 1}" if ano is not None else None


def _build_colheita_de_safras(workbooks: list) -> pd.DataFrame:
    """Monta a tabela 'colheita' (usada pela Visão Geral) a partir da
    planilha de Histórico de Safras — uma aba por ano (2026, 2025, 2024...).
    Diferente de get_historico_safras(), NÃO renomeia as colunas: cada aba já
    traz Setor, Total Área O.S., TCH Real, % Variação TCH, Data Ultima
    Entrega etc. com os mesmos nomes que a Visão Geral espera, então só
    empilha (concat) as abas de ano encontradas em qualquer um dos
    workbooks. A coluna 'Safra' de cada linha é SEMPRE sobrescrita a partir
    do nome da aba (ver _safra_da_aba) — regra fixa e confiável da planilha,
    em vez de depender do preenchimento manual da coluna 'Safra' dentro da
    aba (que pode ter espaço a mais, formato diferente ou célula em branco).
    Devolve DataFrame vazio se nenhuma aba de ano tiver a coluna 'Setor'
    (heurística mínima para não pegar aba errada)."""
    partes = []
    for workbook in workbooks:
        try:
            xls = pd.ExcelFile(workbook)
        except Exception:
            continue
        for nome_aba in xls.sheet_names:
            safra = _safra_da_aba(nome_aba)
            if safra is None:
                continue
            try:
                df = _clean_columns(pd.read_excel(xls, sheet_name=nome_aba)).dropna(how="all")
            except Exception:
                continue
            if df.empty or "Setor" not in df.columns:
                continue
            df["Safra"] = safra  # sempre a partir do nome da aba, não do preenchimento manual
            partes.append(df)
    if not partes:
        return pd.DataFrame()
    return pd.concat(partes, ignore_index=True)


@st.cache_data(ttl=600, show_spinner="Baixando histórico de safras...")
def get_historico_safras() -> pd.DataFrame:
    """Lê a planilha dedicada de Histórico de Safras (link separado) e
    normaliza as colunas para Fazenda | Setor | Safra | Toneladas | TCH |
    Área Colhida. O ATR não costuma estar nessa planilha — é cruzado depois,
    por Fazenda + Safra, com a aba BASEATR/BASEART da planilha principal
    (ver enrich_historico_com_atr).

    A fonte tem UMA ABA POR SAFRA (ex: 2026, 2025, 2024, 2023) — a função lê
    todas as abas cujo nome contém um ano de 4 dígitos, em TODOS os workbooks
    encontrados (suporta tanto um único .xlsx quanto uma pasta zipada com
    vários arquivos — ver _extrair_workbooks), empilha (concat) e preenche a
    coluna Safra com o ano do NOME da aba (ignora eventual coluna "Safra"
    dentro da própria aba, pra não haver conflito). Se nenhuma aba tiver nome
    de ano, cai no modo antigo: escolhe a única aba com mais colunas
    esperadas preenchidas. Devolve DataFrame vazio (sem lançar exceção) se a
    planilha ainda estiver privada ou fora do padrão esperado — a página
    trata isso com uma mensagem em vez de quebrar."""
    try:
        conteudo = _download_dropbox_bytes(DROPBOX_HISTORICO_URL)
    except Exception:
        return pd.DataFrame()

    workbooks = _extrair_workbooks(conteudo)
    candidatos_sem_safra = {k: v for k, v in HISTORICO_COLUMN_CANDIDATES.items() if k != "Safra"}

    abas_ano = []  # [(ano, df_normalizado)]
    for workbook in workbooks:
        try:
            xls = pd.ExcelFile(workbook)
        except Exception:
            continue
        for nome_aba in xls.sheet_names:
            ano = _ano_do_nome_aba(nome_aba)
            if ano is None:
                continue
            try:
                candidata = _clean_columns(pd.read_excel(xls, sheet_name=nome_aba)).dropna(how="all")
            except Exception:
                continue
            if candidata.empty:
                continue
            score = sum(1 for c in candidatos_sem_safra.values() if _find_column(candidata, c) is not None)
            if score < 2:
                continue
            renomeia = {}
            for nome_final, candidatos in candidatos_sem_safra.items():
                col = _find_column(candidata, candidatos)
                if col is not None:
                    renomeia[col] = nome_final
            candidata = candidata.rename(columns=renomeia)
            candidata["Safra"] = ano
            abas_ano.append((ano, candidata))

    if abas_ano:
        return pd.concat([df for _, df in sorted(abas_ano, key=lambda t: t[0], reverse=True)], ignore_index=True)

    # Fallback: fonte não organizada por aba/ano — escolhe a única aba (em
    # qualquer um dos workbooks) com mais colunas esperadas preenchidas,
    # incluindo a coluna Safra dela mesma.
    melhor_df = None
    melhor_score = 0
    for workbook in workbooks:
        try:
            xls = pd.ExcelFile(workbook)
        except Exception:
            continue
        for nome_aba in xls.sheet_names:
            try:
                candidata = _clean_columns(pd.read_excel(xls, sheet_name=nome_aba)).dropna(how="all")
            except Exception:
                continue
            if candidata.empty:
                continue
            score = sum(1 for candidatos in HISTORICO_COLUMN_CANDIDATES.values() if _find_column(candidata, candidatos) is not None)
            if score > melhor_score:
                melhor_score = score
                melhor_df = candidata

    if melhor_df is None or melhor_score < 2:
        return pd.DataFrame()

    df = melhor_df
    renomeia = {}
    for nome_final, candidatos in HISTORICO_COLUMN_CANDIDATES.items():
        col = _find_column(df, candidatos)
        if col is not None:
            renomeia[col] = nome_final
    df = df.rename(columns=renomeia)
    return df


def _norm_fazenda(valor) -> str | None:
    """Normaliza o nome da Fazenda só para efeito de CASAMENTO entre as duas
    planilhas (espaços duplicados, espaço nas pontas, maiúscula/minúscula) —
    o nome exibido na tela continua o da planilha de histórico, sem alteração.
    Sem isso, uma fazenda salva como "Faz. São José " numa planilha e
    "FAZ. SAO JOSE" na outra nunca bate, e o ATR/TAH fica em branco sem erro
    nenhum."""
    if pd.isna(valor):
        return None
    return re.sub(r"\s+", " ", str(valor).strip()).upper()


def diagnostico_atr(atr: pd.DataFrame) -> str | None:
    """Explica por que o cruzamento com o ATR pode não estar funcionando, ou
    devolve None se a aba BASEATR/BASEART parece OK (tem Fazenda e ATR
    identificáveis). Usado pela página de Histórico de Safras pra mostrar um
    aviso específico em vez de só deixar TAH/ATR em branco sem dizer o
    motivo."""
    if atr is None or atr.empty:
        return "a aba BASEATR/BASEART não foi encontrada (ou está vazia) na planilha principal."
    col_fazenda = _find_column(atr, ATR_FAZENDA_CANDIDATES)
    col_atr = _find_column(atr, ["ATR", "Atr"])
    faltando = [nome for nome, col in [("Fazenda/Fundo Agrícola", col_fazenda), ("ATR", col_atr)] if col is None]
    if faltando:
        return (
            f"a aba BASEATR/BASEART não tem a(s) coluna(s) {', '.join(faltando)} identificável(is). "
            f"Colunas disponíveis nela: {', '.join(atr.columns.astype(str))}."
        )
    return None


def enrich_historico_com_atr(historico: pd.DataFrame, atr: pd.DataFrame) -> pd.DataFrame:
    """Cruza o histórico de safras com a aba BASEATR/BASEART (planilha
    principal, o 'outro link') por Fazenda + Safra, pra calcular o TAH. A
    Safra do lado do ATR é derivada do ANO da 'Data Produção' (a aba BASEATR
    não tem coluna Safra própria) — isso evita misturar leituras de ATR de
    anos diferentes na mesma Fazenda numa média só, que é o que causava valor
    errado/duplicado. O casamento por Fazenda é normalizado (ver
    _norm_fazenda) pra não falhar por espaço/maiúscula diferente entre as
    duas planilhas. Se BASEATR não tiver Fazenda/ATR identificáveis, devolve
    o histórico sem alterações."""
    if historico is None or historico.empty or atr is None or atr.empty:
        return historico

    col_fazenda_atr = _find_column(atr, ATR_FAZENDA_CANDIDATES)
    col_atr = _find_column(atr, ["ATR", "Atr"])
    if col_fazenda_atr is None or col_atr is None or "Fazenda" not in historico.columns:
        return historico

    atr_trab = atr[[col_fazenda_atr, col_atr]].rename(columns={col_fazenda_atr: "Fazenda", col_atr: "ATR"})
    atr_trab["_fazenda_chave"] = atr_trab["Fazenda"].map(_norm_fazenda)

    col_data_atr = _find_column(atr, ["Data Produção", "Data Producao", "Data"])
    usar_safra = False
    if col_data_atr is not None and "Safra" in historico.columns:
        datas = pd.to_datetime(atr[col_data_atr], errors="coerce", dayfirst=True)
        if datas.notna().any():
            atr_trab = atr_trab.assign(Safra=datas.dt.year)
            usar_safra = True

    chaves = ["_fazenda_chave", "Safra"] if usar_safra else ["_fazenda_chave"]
    atr_resumo = atr_trab.dropna(subset=chaves).groupby(chaves, as_index=False)["ATR"].mean()

    historico = historico.copy()
    historico["_fazenda_chave"] = historico["Fazenda"].map(_norm_fazenda)
    if usar_safra:
        atr_resumo["Safra"] = pd.to_numeric(atr_resumo["Safra"], errors="coerce")
        historico["Safra"] = pd.to_numeric(historico["Safra"], errors="coerce")

    resultado = historico.merge(atr_resumo, on=chaves, how="left")
    return resultado.drop(columns=["_fazenda_chave"])


def _agg_historico(historico: pd.DataFrame, by: str) -> pd.DataFrame:
    """Agrega o histórico de safras por `by` ('Fazenda' ou 'Safra'):
    Toneladas (soma), TCH (média), Área Colhida (soma), ATR (média, quando
    disponível). Só agrega as colunas que realmente existirem."""
    if historico is None or historico.empty or by not in historico.columns:
        return pd.DataFrame()
    agg = {}
    if "Toneladas" in historico.columns:
        agg["Toneladas"] = "sum"
    if "TCH" in historico.columns:
        agg["TCH"] = "mean"
    if "Área Colhida" in historico.columns:
        agg["Área Colhida"] = "sum"
    if "ATR" in historico.columns:
        agg["ATR"] = "mean"
    if not agg:
        return pd.DataFrame()
    return historico.groupby(by, as_index=False).agg(agg)


def add_tah(df: pd.DataFrame) -> pd.DataFrame:
    """TAH (Toneladas de Açúcar por Hectare) = TCH × ATR ÷ 100. O TCH mede o
    volume de massa colhida; o ATR atesta a qualidade/doçura da matéria-prima
    — o TAH junta as duas coisas numa métrica só. Calculado sobre os valores
    já agregados (TCH médio x ATR médio da Safra/Fazenda); devolve o
    DataFrame sem alterar se faltar TCH ou ATR."""
    if df is None or df.empty or "TCH" not in df.columns or "ATR" not in df.columns:
        return df
    out = df.copy()
    out["TAH"] = out["TCH"] * out["ATR"] / 100
    return out


def agrupar_historico_por_fazenda(historico: pd.DataFrame) -> pd.DataFrame:
    """Visão padrão da página Histórico de Safras: uma linha por Fazenda —
    Toneladas (soma), TCH (média), Área Colhida (soma), ATR (média), TAH
    (TCH x ATR / 100)."""
    out = _agg_historico(historico, "Fazenda")
    out = add_tah(out)
    return out.sort_values("Toneladas", ascending=False) if not out.empty else out


def agrupar_historico_por_safra(historico: pd.DataFrame) -> pd.DataFrame:
    """Quebra ano a ano (Safra) — usada quando uma Fazenda específica é
    escolhida na busca, para mostrar 2026/2025/2024/2023... lado a lado.
    Inclui TAH (TCH x ATR / 100)."""
    out = _agg_historico(historico, "Safra")
    out = add_tah(out)
    return out.sort_values("Safra", ascending=False) if not out.empty else out


# Nomes possíveis da coluna de cidade/município na aba PROD./COLHEITA/ESTIMATIVA.
# A comparação é case-insensitive (ex: "cidade" minúsculo bate com "Cidade").
CITY_COLUMN_CANDIDATES = ["Cidade", "Município", "Municipio", "City", "Cidade/Município"]


def _find_city_column(df: pd.DataFrame) -> str | None:
    """Localiza a coluna de cidade num DataFrame, ignorando maiúsculas/minúsculas."""
    cols_lower = {str(c).strip().lower(): c for c in df.columns}
    for candidato in CITY_COLUMN_CANDIDATES:
        real = cols_lower.get(candidato.lower())
        if real is not None:
            return real
    return None


def get_prod_cities(prod: pd.DataFrame) -> list:
    """Localiza a coluna de cidade na aba PROD. (o nome pode variar) e devolve
    a lista de cidades únicas, usada para montar a área de clima por unidade.
    Devolve lista vazia se a coluna ainda não existir na planilha (o chamador
    cai para a cidade padrão nesse caso)."""
    if prod is None or prod.empty:
        return []
    col = _find_city_column(prod)
    if col is None:
        return []
    cidades = sorted(prod[col].dropna().astype(str).str.strip().unique().tolist())
    return [c for c in cidades if c]


# Candidatos de coluna para a seção "Realizado e Previsto" (aba AGR500/PROD) —
# nomes de coluna ainda não confirmados pelo usuário, por isso a busca é
# flexível (candidatos mais prováveis primeiro); se nenhum bater, a seção
# mostra uma mensagem em vez de quebrar.
ESTAGIO_CANDIDATES = ["Estágio da Cultura", "Estagio da Cultura", "Estágio", "Estagio"]
# Confirmado na planilha AGR500 (aba "PRODUÇÃO"): TCH Previsto vem na coluna
# "TON/ha" e TCH Realizado vem na coluna "Produtividade (TON/ha)" — nomes
# que não tinham nada a ver com "TCH Previsto/Realizado", por isso o app
# não achava antes. Mantidos os nomes antigos na lista como fallback, caso
# a planilha volte a usar esse padrão no futuro.
TCH_PREVISTO_CANDIDATES = ["TON/ha", "TCH Previsto", "TCH Prev.", "TCH Prev", "TCH Estimado"]
TCH_REALIZADO_CANDIDATES = ["Produtividade (TON/ha)", "TCH Realizado", "TCH Real", "TCH Real (Colheita)"]


def tch_previsto_realizado_por_estagio(prod: pd.DataFrame) -> pd.DataFrame:
    """Agrupa TCH Previsto x Realizado por Estágio da Cultura, a partir da aba
    de produção (AGR500 / aba "PRODUÇÃO"). TCH Previsto = coluna "TON/ha",
    TCH Realizado = coluna "Produtividade (TON/ha)" (ver
    TCH_PREVISTO_CANDIDATES/TCH_REALIZADO_CANDIDATES); devolve DataFrame
    vazio se não achar nenhuma das duas, e a página mostra um aviso em vez
    de quebrar."""
    if prod is None or prod.empty:
        return pd.DataFrame()
    col_estagio = _find_column(prod, ESTAGIO_CANDIDATES)
    col_previsto = _find_column(prod, TCH_PREVISTO_CANDIDATES)
    col_realizado = _find_column(prod, TCH_REALIZADO_CANDIDATES)
    if col_estagio is None or (col_previsto is None and col_realizado is None):
        return pd.DataFrame()

    renomeia = {col_estagio: "Estágio da Cultura"}
    value_cols = []
    if col_previsto is not None:
        renomeia[col_previsto] = "TCH Previsto"
        value_cols.append("TCH Previsto")
    if col_realizado is not None:
        renomeia[col_realizado] = "TCH Realizado"
        value_cols.append("TCH Realizado")

    df = prod.rename(columns=renomeia)
    return df.groupby("Estágio da Cultura", as_index=False)[value_cols].mean()


def get_fazenda_city_map(*dfs: pd.DataFrame) -> dict:
    """Procura a coluna de cidade/município e a coluna Fazenda em qualquer uma
    das abas passadas (ex: COLHEITA, ESTIMATIVA, PROD.) e monta um mapa
    {Fazenda: Cidade}. Devolve {} se a coluna de cidade ainda não existir em
    nenhuma delas — o mapa fica pendente até a planilha ser atualizada."""
    mapa: dict = {}
    for df in dfs:
        if df is None or df.empty or "Fazenda" not in df.columns:
            continue
        col = _find_city_column(df)
        if col is None:
            continue
        sub = df[["Fazenda", col]].dropna()
        for fazenda, cidade in zip(sub["Fazenda"], sub[col]):
            mapa[str(fazenda).strip()] = str(cidade).strip()
    return mapa


def build_mapa_colheita(colheita: pd.DataFrame, estimativa: pd.DataFrame, fazenda_city_map: dict) -> pd.DataFrame:
    """Agrega Toneladas Colhidas (COLHEITA, coluna 'Prod. Real') e Área
    Estimada (ESTIMATIVA, coluna 'Área Estimada') por Fazenda e junta a
    cidade correspondente — base de dados para o mapa de bolhas em
    map_view.render_mapa_colheita. Fazendas sem cidade mapeada ficam de fora
    do mapa, mas continuam normalmente nos KPIs e gráficos do dashboard."""
    ton = (
        colheita.groupby("Fazenda", as_index=False)["Prod. Real"]
        .sum()
        .rename(columns={"Prod. Real": "Toneladas Colhidas"})
        if not colheita.empty and "Fazenda" in colheita.columns and "Prod. Real" in colheita.columns
        else pd.DataFrame(columns=["Fazenda", "Toneladas Colhidas"])
    )
    area = (
        estimativa.groupby("Fazenda", as_index=False)["Área Estimada"]
        .sum()
        .rename(columns={"Área Estimada": "Área Estimada (ha)"})
        if not estimativa.empty and "Fazenda" in estimativa.columns and "Área Estimada" in estimativa.columns
        else pd.DataFrame(columns=["Fazenda", "Área Estimada (ha)"])
    )

    if ton.empty and area.empty:
        return pd.DataFrame(columns=["Fazenda", "Toneladas Colhidas", "Área Estimada (ha)", "Cidade"])

    out = ton.merge(area, on="Fazenda", how="outer")
    out["Toneladas Colhidas"] = out["Toneladas Colhidas"].fillna(0)
    out["Área Estimada (ha)"] = out["Área Estimada (ha)"].fillna(0)
    out["Cidade"] = out["Fazenda"].astype(str).str.strip().map(fazenda_city_map)
    return out.dropna(subset=["Cidade"])


UF_COLUMN_CANDIDATES = ["UF", "Estado", "Sigla UF", "Sigla"]


def build_mapa_municipio(mapa_colheita_df: pd.DataFrame) -> pd.DataFrame:
    """Agrega o resultado de build_mapa_colheita (uma linha por Fazenda) por
    MUNICÍPIO (Cidade) — evita bolhas sobrepostas no mapa quando há mais de
    uma fazenda na mesma cidade, e calcula o TCH (Toneladas Colhidas / Área
    Estimada) por município para aparecer na legenda/hover do mapa."""
    if mapa_colheita_df is None or mapa_colheita_df.empty:
        return pd.DataFrame(columns=["Cidade", "Toneladas Colhidas", "Área Estimada (ha)", "TCH"])
    out = mapa_colheita_df.groupby("Cidade", as_index=False)[["Toneladas Colhidas", "Área Estimada (ha)"]].sum()
    out["TCH"] = (out["Toneladas Colhidas"] / out["Área Estimada (ha)"].replace(0, pd.NA)).fillna(0)
    return out


def _find_uf_column(df: pd.DataFrame) -> str | None:
    """Localiza a coluna de UF/Estado num DataFrame, ignorando maiúsculas/minúsculas."""
    cols_lower = {str(c).strip().lower(): c for c in df.columns}
    for candidato in UF_COLUMN_CANDIDATES:
        real = cols_lower.get(candidato.lower())
        if real is not None:
            return real
    return None


def get_cidade_uf_map(cidade_uf_df: pd.DataFrame) -> dict:
    """Lê a aba de Cidade x UF e devolve {cidade: UF}. Devolve {} se a aba
    ainda não existir na planilha ou não tiver as colunas esperadas — nesse
    caso o mapa cai para a visão por fazenda/cidade (bolhas) em vez de estado."""
    if cidade_uf_df is None or cidade_uf_df.empty:
        return {}
    col_cidade = _find_city_column(cidade_uf_df)
    col_uf = _find_uf_column(cidade_uf_df)
    if col_cidade is None or col_uf is None:
        return {}
    sub = cidade_uf_df[[col_cidade, col_uf]].dropna()
    return {str(c).strip(): str(u).strip().upper() for c, u in zip(sub[col_cidade], sub[col_uf])}


def build_mapa_estado(mapa_colheita_df: pd.DataFrame, cidade_uf_map: dict) -> pd.DataFrame:
    """Cruza a aba CIDADE (cidade -> UF) com o resultado de build_mapa_colheita
    (fazenda -> cidade -> toneladas/área, vindo da ESTIMATIVA) para agregar
    Toneladas Colhidas e Área Estimada por ESTADO — a visão que o mapa deve
    priorizar. Devolve DataFrame vazio se faltar a aba CIDADE ou o cruzamento
    não achar nenhuma UF (o chamador cai para o mapa por fazenda nesse caso)."""
    if mapa_colheita_df is None or mapa_colheita_df.empty or not cidade_uf_map:
        return pd.DataFrame(columns=["UF", "Toneladas Colhidas", "Área Estimada (ha)"])
    df = mapa_colheita_df.copy()
    df["UF"] = df["Cidade"].map(cidade_uf_map)
    df = df.dropna(subset=["UF"])
    if df.empty:
        return pd.DataFrame(columns=["UF", "Toneladas Colhidas", "Área Estimada (ha)"])
    out = df.groupby("UF", as_index=False)[["Toneladas Colhidas", "Área Estimada (ha)"]].sum()
    out["TCH"] = (out["Toneladas Colhidas"] / out["Área Estimada (ha)"].replace(0, pd.NA)).fillna(0)
    return out


def require_columns(df: pd.DataFrame, colunas: list, aba_label: str) -> bool:
    """Confere se `df` tem todas as `colunas`; se faltar alguma, mostra uma
    mensagem amigável (em vez do app quebrar com KeyError) e devolve False —
    a página deve fazer `if not require_columns(...): st.stop()` em seguida."""
    faltando = [c for c in colunas if c not in df.columns]
    if faltando:
        st.warning(
            f"A aba {aba_label} não tem a(s) coluna(s) esperada(s): {', '.join(faltando)}. "
            f"Colunas disponíveis: {', '.join(df.columns.astype(str))}."
        )
        return False
    return True


def frota_summary(df: pd.DataFrame, group_cols: list, date_col: str = "Data",
                   value_col: str = "Toneladas", extra_agg: dict | None = None) -> pd.DataFrame:
    """
    Resume um DataFrame por grupo (ex: Frota, Empresa) com três métricas padrão:
      - "Ton dia": soma de value_col na última data presente no recorte filtrado
      - "Ton dia Anterior": soma de value_col na penúltima data presente
      - "Acumulado (t)": soma total de value_col no período filtrado

    extra_agg: dict opcional {nome_da_coluna_final: (coluna_origem, função_agregação)}
               para métricas adicionais (ex: média de distância).
    """
    base_cols = list(group_cols) + ["Ton dia", "Ton dia Anterior", "Acumulado (t)"]
    if df.empty:
        return pd.DataFrame(columns=base_cols)

    datas = sorted(df[date_col].dropna().unique())
    ultima = datas[-1] if len(datas) >= 1 else None
    penultima = datas[-2] if len(datas) >= 2 else None

    acumulado = (
        df.groupby(group_cols, as_index=False)[value_col]
        .sum()
        .rename(columns={value_col: "Acumulado (t)"})
    )

    if ultima is not None:
        ton_dia = (
            df[df[date_col] == ultima]
            .groupby(group_cols, as_index=False)[value_col]
            .sum()
            .rename(columns={value_col: "Ton dia"})
        )
    else:
        ton_dia = pd.DataFrame(columns=list(group_cols) + ["Ton dia"])

    if penultima is not None:
        ton_dia_ant = (
            df[df[date_col] == penultima]
            .groupby(group_cols, as_index=False)[value_col]
            .sum()
            .rename(columns={value_col: "Ton dia Anterior"})
        )
    else:
        ton_dia_ant = pd.DataFrame(columns=list(group_cols) + ["Ton dia Anterior"])

    out = acumulado.merge(ton_dia, on=group_cols, how="left").merge(ton_dia_ant, on=group_cols, how="left")
    out["Ton dia"] = out["Ton dia"].fillna(0)
    out["Ton dia Anterior"] = out["Ton dia Anterior"].fillna(0)

    if extra_agg:
        for new_name, (col, func) in extra_agg.items():
            extra = df.groupby(group_cols, as_index=False)[col].agg(func).rename(columns={col: new_name})
            out = out.merge(extra, on=group_cols, how="left")

    out = out.sort_values("Acumulado (t)", ascending=False).reset_index(drop=True)
    return out


def milhar_config(cols: list, decimals: int = 0) -> dict:
    """Gera um dict de column_config do Streamlit aplicando separador de milhares às colunas dadas."""
    fmt = f"%,.{decimals}f"
    return {c: st.column_config.NumberColumn(c, format=fmt) for c in cols}


def add_pct_entrega(df: pd.DataFrame, value_col: str = "Acumulado (t)", out_col: str = "% Entrega") -> pd.DataFrame:
    """Adiciona a coluna % Entrega = participação da linha no acumulado total (como nos relatórios KPIs)."""
    out = df.copy()
    total = out[value_col].sum()
    out[out_col] = (out[value_col] / total * 100) if total else 0
    return out


def join_disponibilidade_diesel(
    resumo: pd.DataFrame,
    frota_col: str,
    disponibilidade: pd.DataFrame,
    diesel: pd.DataFrame,
    tipo_diesel: str | None = None,
) -> pd.DataFrame:
    """
    Junta ao resumo por frota:
      - "Disponibilidade Mecânica" (%) — média por Equipamento (a aba tem mais de um registro por equipamento)
      - "Lt/ton" — vindo da aba de diesel, filtrando por TIPO quando informado
    """
    out = resumo.copy()

    if disponibilidade is not None and not disponibilidade.empty and "Equipamento" in disponibilidade.columns:
        disp = (
            disponibilidade.groupby("Equipamento", as_index=False)["Disponibilidade Mecânica"]
            .mean()
        )
        disp["Disponibilidade Mecânica"] = disp["Disponibilidade Mecânica"] * 100
        out = out.merge(disp, left_on=frota_col, right_on="Equipamento", how="left")
        if "Equipamento" in out.columns and "Equipamento" != frota_col:
            out = out.drop(columns=["Equipamento"])

    if diesel is not None and not diesel.empty and "Equip." in diesel.columns:
        d = diesel.copy()
        if tipo_diesel and "TIPO" in d.columns:
            d = d[d["TIPO"] == tipo_diesel]
        d = d.groupby("Equip.", as_index=False)["Lt/ton"].mean()
        out = out.merge(d, left_on=frota_col, right_on="Equip.", how="left")
        if "Equip." in out.columns and "Equip." != frota_col:
            out = out.drop(columns=["Equip."])

    return out


def build_grouped_table(
    df: pd.DataFrame, group_col: str, sub_col: str, value_cols: list,
    label_col_name: str = "Empresa/Frota", sort_value_col: str | None = None,
) -> pd.DataFrame:
    """
    Constrói uma tabela no estilo dos relatórios KPI: uma linha com o nome do grupo
    (ex: Empresa), seguida pelas linhas de detalhe (ex: Frota) indentadas abaixo,
    sem repetir o nome do grupo a cada linha.
    """
    sort_col = sort_value_col or (value_cols[-1] if value_cols else sub_col)
    ordem_grupos = (
        df.groupby(group_col)[sort_col].sum().sort_values(ascending=False).index.tolist()
    )

    rows = []
    for grupo in ordem_grupos:
        sub = df[df[group_col] == grupo]
        header = {label_col_name: grupo}
        for c in value_cols:
            header[c] = None
        rows.append(header)

        sub_sorted = sub.sort_values(sort_col, ascending=False)
        for _, r in sub_sorted.iterrows():
            row = {label_col_name: f"    {r[sub_col]}"}
            for c in value_cols:
                row[c] = r[c]
            rows.append(row)

    return pd.DataFrame(rows)


def kpi_card(col, label: str, value: str, delta: str | None = None):
    """Helper para exibir um cartão de KPI padronizado."""
    with col:
        st.metric(label, value, delta)


def period_delta(
    df: pd.DataFrame,
    date_col: str,
    value_col: str,
    agg: str = "sum",
    window_days: int = 15,
    fmt: str = "{:+.1f}%",
    mode: str = "pct_change",
) -> str | None:
    """
    Compara os últimos `window_days` dias com os `window_days` anteriores,
    usando a data mais recente disponível na própria coluna como referência
    (não "hoje", já que a planilha é histórica).

    mode="pct_change": variação percentual (padrão, para valores em unidades como t, km, kg/t).
    mode="abs_diff": diferença absoluta em pontos (para métricas que já são % —
                      evita "% de %" instável quando o valor de base oscila perto de zero).

    Retorna string tipo "▲ +8.4% vs período anterior" ou None se não houver
    dado suficiente para os dois períodos.
    """
    if df.empty or date_col not in df.columns or value_col not in df.columns:
        return None

    d = df[[date_col, value_col]].dropna()
    if d.empty:
        return None

    ultima_data = d[date_col].max()
    corte_atual = ultima_data - pd.Timedelta(days=window_days)
    corte_anterior = corte_atual - pd.Timedelta(days=window_days)

    atual = d[d[date_col] > corte_atual][value_col]
    anterior = d[(d[date_col] > corte_anterior) & (d[date_col] <= corte_atual)][value_col]

    if atual.empty or anterior.empty:
        return None

    val_atual = atual.sum() if agg == "sum" else atual.mean()
    val_anterior = anterior.sum() if agg == "sum" else anterior.mean()

    if mode == "abs_diff":
        variacao = val_atual - val_anterior
        seta = "▲" if variacao >= 0 else "▼"
        return f"{seta} {fmt.format(variacao)} p.p. ({window_days}d)"

    if not val_anterior:
        return None

    variacao = (val_atual - val_anterior) / val_anterior * 100
    seta = "▲" if variacao >= 0 else "▼"
    return f"{seta} {fmt.format(variacao)} ({window_days}d)"

