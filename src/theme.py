"""
theme.py — CSS compartilhado por todas as páginas do dashboard, chamado uma
vez no início de cada página (inject_theme()). Mantém a identidade visual
consistente (cores, cards, tipografia) em vez de cada página estilizar do
seu jeito.

Paleta e componentes inspirados no painel de referência "Mentor" (fundo
azul-marinho profundo, cards arredondados, barras de destaque coloridas por
categoria, tabelas com acabamento tipo heatmap) — só a CAMADA VISUAL, nenhuma
lógica de dados foi alterada aqui.
"""

import streamlit as st

# ---------------------------------------------------------------------------
# Paleta central — mude aqui para afetar o app inteiro.
# ---------------------------------------------------------------------------
BG = "#080B18"              # fundo base, azul-marinho quase preto (ref. Mentor)
BG_GLOW_1 = "#161F45"       # glow superior esquerdo
BG_GLOW_2 = "#0B1130"       # glow inferior
BG_CARD = "#121936"         # cards / métricas
BG_CARD_SOFT = "#0F1530"    # sidebar / superfícies secundárias
BORDER = "rgba(255,255,255,0.08)"
BORDER_SOFT = "rgba(255,255,255,0.05)"

ACCENT_1 = "#4F7DF3"        # azul primário (ref. Mentor)
ACCENT_2 = "#6C5CE7"        # violeta — par do gradiente de destaque
ACCENT_GREEN = "#3DDC84"    # positivo / bom desempenho
ACCENT_YELLOW = "#F5B942"   # alerta / desempenho mediano
ACCENT_RED = "#FF6B6B"      # negativo / abaixo da meta
ACCENT_ORANGE = "#FF8A5C"   # rótulos de destaque (eyebrow), como no painel de referência

TEXT_MAIN = "rgba(255,255,255,0.92)"
TEXT_MUTED = "rgba(255,255,255,0.62)"
TEXT_FAINT = "rgba(255,255,255,0.42)"

CSS = f"""
<style>
    /* ---------------------------------------------------------------- */
    /* Fundo geral                                                      */
    /* ---------------------------------------------------------------- */
    .stApp {{
        background:
            radial-gradient(1100px 550px at 8% -8%, {BG_GLOW_1} 0%, transparent 55%),
            radial-gradient(900px 500px at 100% 0%, #1A1440 0%, transparent 45%),
            radial-gradient(1000px 700px at 50% 120%, {BG_GLOW_2} 0%, transparent 60%),
            {BG};
        color: {TEXT_MAIN};
    }}

    /* ---------------------------------------------------------------- */
    /* Navegação superior (st.navigation position="top")                */
    /* ---------------------------------------------------------------- */
    div[data-testid="stTopNav"] {{
        background: linear-gradient(90deg, #0D1330 0%, #161C3E 60%, #171339 100%);
        border-bottom: 1px solid {BORDER};
        box-shadow: 0 6px 24px rgba(0,0,0,0.35);
    }}
    div[data-testid="stTopNav"] button {{
        border-radius: 10px !important;
        color: {TEXT_MUTED} !important;
        transition: all 0.15s ease-in-out;
    }}
    div[data-testid="stTopNav"] button:hover {{
        background: rgba(255,255,255,0.06) !important;
        color: {TEXT_MAIN} !important;
    }}
    div[data-testid="stTopNav"] button[aria-selected="true"] {{
        background: linear-gradient(90deg, {ACCENT_1}, {ACCENT_2}) !important;
        border-radius: 10px !important;
        color: white !important;
        box-shadow: 0 3px 12px rgba(79,125,243,0.35);
    }}

    /* ---------------------------------------------------------------- */
    /* Sidebar                                                           */
    /* ---------------------------------------------------------------- */
    section[data-testid="stSidebar"] {{
        background: linear-gradient(180deg, {BG_CARD_SOFT} 0%, #0A0E22 100%);
        border-right: 1px solid {BORDER};
    }}
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {{
        color: {TEXT_MAIN};
    }}
    section[data-testid="stSidebar"] hr {{
        border-color: {BORDER_SOFT};
    }}

    /* ---------------------------------------------------------------- */
    /* Tipografia                                                        */
    /* ---------------------------------------------------------------- */
    h1, h2, h3 {{
        letter-spacing: -0.01em;
        color: {TEXT_MAIN};
    }}
    /* Barra de destaque colorida antes de cada subtítulo de seção,
       no espírito das barras por categoria do painel de referência. */
    h3 {{
        position: relative;
        padding-left: 12px;
        border-left: 3px solid {ACCENT_1};
    }}
    p, span, label, .stMarkdown {{
        color: {TEXT_MUTED};
    }}
    .stCaption, [data-testid="stCaptionContainer"] {{
        color: {TEXT_FAINT} !important;
    }}

    /* ---------------------------------------------------------------- */
    /* Cards genéricos usados via .ndb-card                             */
    /* ---------------------------------------------------------------- */
    .ndb-card {{
        background: {BG_CARD};
        border: 1px solid {BORDER};
        border-radius: 14px;
        padding: 16px 18px;
        box-shadow: 0 4px 18px rgba(0,0,0,0.28);
    }}
    .ndb-card-accent {{
        background: linear-gradient(135deg, rgba(79,125,243,0.20), rgba(108,92,231,0.12));
        border: 1px solid rgba(79,125,243,0.35);
        border-radius: 14px;
        padding: 14px 16px;
        box-shadow: 0 4px 18px rgba(0,0,0,0.28);
    }}
    .ndb-eyebrow {{
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: {ACCENT_ORANGE};
        margin-bottom: 2px;
    }}

    /* ---------------------------------------------------------------- */
    /* Métricas nativas do Streamlit (st.metric) com acabamento premium */
    /* ---------------------------------------------------------------- */
    div[data-testid="stMetric"] {{
        background: {BG_CARD};
        border: 1px solid {BORDER};
        border-left: 3px solid {ACCENT_1};
        border-radius: 14px;
        padding: 14px 16px;
        box-shadow: 0 4px 18px rgba(0,0,0,0.28);
    }}
    div[data-testid="stMetricLabel"] {{
        color: {TEXT_MUTED} !important;
    }}

    /* ---------------------------------------------------------------- */
    /* Botões                                                            */
    /* ---------------------------------------------------------------- */
    .stButton > button, .stDownloadButton > button {{
        background: linear-gradient(90deg, {ACCENT_1}, {ACCENT_2});
        color: white;
        border: none;
        border-radius: 10px;
        font-weight: 600;
        box-shadow: 0 3px 12px rgba(79,125,243,0.30);
        transition: transform 0.12s ease-in-out, box-shadow 0.12s ease-in-out;
    }}
    .stButton > button:hover, .stDownloadButton > button:hover {{
        transform: translateY(-1px);
        box-shadow: 0 5px 16px rgba(79,125,243,0.45);
        color: white;
    }}

    /* ---------------------------------------------------------------- */
    /* Inputs (multiselect, selectbox, date_input, file_uploader...)    */
    /* ---------------------------------------------------------------- */
    div[data-baseweb="select"] > div,
    div[data-testid="stDateInput"] input,
    div[data-testid="stTextInput"] input {{
        background: {BG_CARD} !important;
        border: 1px solid {BORDER} !important;
        border-radius: 10px !important;
    }}
    span[data-baseweb="tag"] {{
        background: linear-gradient(90deg, {ACCENT_1}, {ACCENT_2}) !important;
        border-radius: 6px !important;
    }}
    [data-testid="stFileUploaderDropzone"] {{
        background: {BG_CARD_SOFT} !important;
        border: 1px dashed {BORDER} !important;
        border-radius: 12px !important;
    }}

    /* ---------------------------------------------------------------- */
    /* Tabelas / dataframes                                              */
    /* ---------------------------------------------------------------- */
    div[data-testid="stDataFrame"], div[data-testid="stTable"] {{
        border: 1px solid {BORDER};
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 4px 18px rgba(0,0,0,0.25);
    }}

    /* ---------------------------------------------------------------- */
    /* Expanders                                                         */
    /* ---------------------------------------------------------------- */
    div[data-testid="stExpander"] {{
        background: {BG_CARD};
        border: 1px solid {BORDER};
        border-radius: 12px;
    }}

    /* ---------------------------------------------------------------- */
    /* Alertas (info/success/warning) com acabamento tipo card           */
    /* ---------------------------------------------------------------- */
    div[data-testid="stAlertContainer"] {{
        background: {BG_CARD} !important;
        border-radius: 12px !important;
        border: 1px solid {BORDER} !important;
    }}

    /* Divisórias mais discretas */
    hr {{
        border-color: {BORDER_SOFT};
    }}
</style>
"""


def inject_theme():
    """Injeta o CSS compartilhado — chamar uma vez no topo de cada página."""
    st.markdown(CSS, unsafe_allow_html=True)


def card(titulo: str, valor: str, subtitulo: str = "", accent: bool = False) -> str:
    """Monta o HTML de um card de métrica no estilo do dashboard (usado fora
    do st.metric nativo quando queremos mais controle visual, como nos cards
    de clima e no cabeçalho)."""
    classe = "ndb-card-accent" if accent else "ndb-card"
    sub_html = f'<div style="font-size:11px;color:{TEXT_MUTED};margin-top:4px;">{subtitulo}</div>' if subtitulo else ""
    return f"""
    <div class="{classe}">
        <div class="ndb-eyebrow">{titulo}</div>
        <div style="font-size:24px;font-weight:700;color:{TEXT_MAIN};">{valor}</div>
        {sub_html}
    </div>
    """


# ---------------------------------------------------------------------------
# Helpers de cor por faixa de desempenho — para colorir células/valores no
# espírito do heatmap do painel de referência (verde/amarelo/vermelho),
# reaproveitáveis por qualquer página sem duplicar a lógica de cor.
# ---------------------------------------------------------------------------
def status_color(pct: float, bom: float = 90, medio: float = 70) -> str:
    """Devolve a cor (verde/amarelo/vermelho) para um percentual de
    desempenho, usando os mesmos limiares em todo o app."""
    if pct is None:
        return TEXT_FAINT
    if pct >= bom:
        return ACCENT_GREEN
    if pct >= medio:
        return ACCENT_YELLOW
    return ACCENT_RED
