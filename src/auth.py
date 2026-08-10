"""
auth.py — Camada de login do dashboard, usando streamlit-authenticator.

Protege o acesso ao app quando ele estiver publicado numa URL pública
(ex: Render) — sem login, qualquer pessoa com o link entra. Enquanto o
usuário não faz login, NENHUM menu/página do app é montado (ver app.py:
`pages = [...]` e `st.navigation(...)` só rodam depois de exigir_login()
retornar) — a tela mostrada aqui é só o formulário de login, o clima das
unidades e o slide de imagens do agro.

COMO CADASTRAR SEU USUÁRIO (login único — só você acessa):

1) Localmente (para testar no seu PC):
   Copie ".streamlit/secrets.toml.example" para ".streamlit/secrets.toml"
   e preencha com seu nome/senha/e-mail reais. Esse arquivo NUNCA deve ir
   pro GitHub (já está no .gitignore).

2) No Render (produção):
   Settings > Environment > Secret Files > adicione um arquivo chamado
   "secrets.toml" com o mesmo conteúdo do .example, montado no caminho
   ".streamlit/secrets.toml". (Alternativa: cole o mesmo conteúdo numa
   variável de ambiente chamada AUTH_SECRETS_TOML — o código abaixo lê
   dali se st.secrets não tiver a seção [auth].)

As senhas podem ficar em texto puro no secrets — a biblioteca hasheia
automaticamente (bcrypt) na hora do login. O que importa é que o
secrets.toml/variável de ambiente NUNCA seja commitado no repositório.
"""

import os

import streamlit as st
import streamlit_authenticator as stauth
import toml

from src.theme import inject_theme
from src.weather import get_cidades_login, render_weather_login_panel
from src.login_visuals import render_agro_carousel


def _secrets_to_plain_dict(value):
    if isinstance(value, dict):
        return {k: _secrets_to_plain_dict(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_secrets_to_plain_dict(v) for v in value]
    try:
        return {k: _secrets_to_plain_dict(v) for k, v in value.items()}
    except Exception:
        return value


def _carregar_config_auth() -> dict:
    """Busca a configuração de login em st.secrets primeiro (funciona
    local com .streamlit/secrets.toml, e no Render via Secret Files) e,
    se não achar, em uma variável de ambiente com o TOML colado inteiro."""
    try:
        if "auth" in st.secrets:
            return _secrets_to_plain_dict(st.secrets["auth"])
    except Exception:
        pass

    bruto = os.environ.get("AUTH_SECRETS_TOML")
    if bruto:
        return toml.loads(bruto).get("auth", {})

    return {}


def _render_tela_login(authenticator: "stauth.Authenticate") -> None:
    """Monta a tela de login completa: cabeçalho da marca, formulário de
    usuário/senha à esquerda e, à direita, o slide de imagens do agro +
    a previsão do tempo das unidades — tudo isso SEM nenhum menu/dado do
    dashboard, que só aparece depois do login bem-sucedido."""
    st.markdown(
        """
        <div style="text-align:center; margin-top:8px; margin-bottom:18px;">
            <div style="font-size:40px; line-height:1;">🌾</div>
            <div style="font-size:26px; font-weight:800; color:rgba(255,255,255,0.95); margin-top:6px;">
                Mentor Agro ERP
            </div>
            <div style="font-size:13px; color:rgba(255,255,255,0.55); margin-top:2px;">
                Faça login para acessar o painel de gestão agrícola
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_login, col_visual = st.columns([1, 1.3], gap="large")

    with col_login:
        st.markdown(
            """
            <div class="ndb-card" style="margin-bottom:10px;">
                <div class="ndb-eyebrow">Acesso</div>
                <div style="font-size:13px;color:rgba(255,255,255,0.6);">
                    Informe seu usuário e senha cadastrados.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        authenticator.login(location="main", max_login_attempts=5)

        status = st.session_state.get("authentication_status")
        if status is False:
            st.error("Usuário ou senha incorretos.")
        elif status is None:
            st.info("Aguardando login…")

    with col_visual:
        render_agro_carousel()
        cidades = get_cidades_login()
        render_weather_login_panel(cidades)


def exigir_login() -> None:
    """Bloqueia o app até o usuário fazer login com sucesso. Deve ser a
    PRIMEIRA coisa chamada em app.py, logo após st.set_page_config()."""
    config = _carregar_config_auth()

    if not config or "usernames" not in config:
        inject_theme()
        st.error(
            "🔒 Login não configurado.\n\n"
            "Defina as credenciais em `.streamlit/secrets.toml` (veja "
            "`.streamlit/secrets.toml.example`) ou na variável de ambiente "
            "`AUTH_SECRETS_TOML`. Detalhes no topo de `src/auth.py`."
        )
        st.stop()

    credentials = {"usernames": config["usernames"]}

    authenticator = stauth.Authenticate(
        credentials,
        config.get("cookie_name", "ndb_dashboard_auth"),
        config.get("cookie_key", "troque-esta-chave-por-uma-aleatoria"),
        config.get("cookie_expiry_days", 7),
    )

    ja_autenticado = st.session_state.get("authentication_status") is True

    if ja_autenticado:
        # Sessão/cookie já válidos — só roda o componente (mantém o cookie
        # vivo); a biblioteca não redesenha o formulário nesse caso.
        authenticator.login(location="main", max_login_attempts=5)
    else:
        inject_theme()
        _render_tela_login(authenticator)

    status = st.session_state.get("authentication_status")

    if status is not True:
        # Formulário (ou erro/instrução) já foi mostrado em _render_tela_login.
        st.stop()

    # status is True → login ok, segue para o app (menus/páginas só são
    # montados por app.py DEPOIS que esta função retorna).
    with st.sidebar:
        st.caption(f"Conectado como **{st.session_state.get('name')}**")
        authenticator.logout("Sair", "sidebar")
