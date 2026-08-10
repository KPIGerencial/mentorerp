"""
login_visuals.py — Slide (carrossel) de ilustrações com tema agro para a
TELA DE LOGIN. As ilustrações são SVGs próprios embutidos (não dependem de
link externo de imagem — evita tela de login quebrada se um serviço de
imagem cair) animados em CSS puro (crossfade), sem depender de JavaScript.
"""

from src.theme import BG_CARD, BORDER

# Cada slide é um SVG completo (viewBox 800x420) com paleta consistente com
# o tema do dashboard (azuis/violeta de fundo + verde/laranja de destaque).
_SLIDE_1_CANAVIAL = """
<svg viewBox="0 0 800 420" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="sky1" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#2A2B6B"/>
      <stop offset="55%" stop-color="#E08A4C"/>
      <stop offset="100%" stop-color="#F5C15D"/>
    </linearGradient>
    <linearGradient id="field1" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#3DDC84"/>
      <stop offset="100%" stop-color="#1E7A4C"/>
    </linearGradient>
  </defs>
  <rect width="800" height="420" fill="url(#sky1)"/>
  <circle cx="640" cy="120" r="60" fill="#FFE7A8" opacity="0.9"/>
  <rect x="0" y="230" width="800" height="190" fill="url(#field1)"/>
  <g stroke="#F5C15D" stroke-width="3" opacity="0.55">
    <path d="M40 420 L80 240"/><path d="M100 420 L140 240"/><path d="M160 420 L200 240"/>
    <path d="M220 420 L260 240"/><path d="M280 420 L320 240"/><path d="M340 420 L380 240"/>
    <path d="M400 420 L440 240"/><path d="M460 420 L500 240"/><path d="M520 420 L560 240"/>
    <path d="M580 420 L620 240"/><path d="M640 420 L680 240"/><path d="M700 420 L740 240"/>
  </g>
  <text x="40" y="395" font-family="Arial, sans-serif" font-size="22" font-weight="700" fill="#ffffff" opacity="0.92">Canavial ao amanhecer</text>
</svg>
"""

_SLIDE_2_TRATOR = """
<svg viewBox="0 0 800 420" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="sky2" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#4F7DF3"/>
      <stop offset="100%" stop-color="#A9CBFF"/>
    </linearGradient>
  </defs>
  <rect width="800" height="420" fill="url(#sky2)"/>
  <ellipse cx="150" cy="90" rx="70" ry="24" fill="#ffffff" opacity="0.85"/>
  <ellipse cx="210" cy="80" rx="55" ry="20" fill="#ffffff" opacity="0.75"/>
  <rect x="0" y="260" width="800" height="160" fill="#2E8B57"/>
  <rect x="0" y="250" width="800" height="14" fill="#256E45"/>
  <g transform="translate(300,240)">
    <rect x="0" y="30" width="140" height="55" rx="8" fill="#F5B942"/>
    <rect x="90" y="-10" width="55" height="45" rx="6" fill="#FF8A5C"/>
    <rect x="100" y="-2" width="30" height="24" rx="3" fill="#0B1130" opacity="0.7"/>
    <circle cx="30" cy="95" r="34" fill="#121936"/>
    <circle cx="30" cy="95" r="16" fill="#F5C15D"/>
    <circle cx="150" cy="95" r="22" fill="#121936"/>
    <circle cx="150" cy="95" r="10" fill="#F5C15D"/>
  </g>
  <text x="40" y="395" font-family="Arial, sans-serif" font-size="22" font-weight="700" fill="#ffffff" opacity="0.95">Colheita mecanizada</text>
</svg>
"""

_SLIDE_3_CLIMA = """
<svg viewBox="0 0 800 420" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="sky3" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#161F45"/>
      <stop offset="100%" stop-color="#4F7DF3"/>
    </linearGradient>
  </defs>
  <rect width="800" height="420" fill="url(#sky3)"/>
  <g fill="#ffffff" opacity="0.85">
    <ellipse cx="180" cy="110" rx="80" ry="30"/>
    <ellipse cx="250" cy="95" rx="60" ry="26"/>
    <ellipse cx="560" cy="140" rx="90" ry="32"/>
    <ellipse cx="640" cy="120" rx="55" ry="24"/>
  </g>
  <g stroke="#A9CBFF" stroke-width="4" stroke-linecap="round" opacity="0.7">
    <path d="M170 170 L155 210"/><path d="M200 170 L185 210"/><path d="M230 170 L215 210"/>
    <path d="M560 190 L545 230"/><path d="M590 190 L575 230"/><path d="M620 190 L605 230"/>
  </g>
  <rect x="0" y="290" width="800" height="130" fill="#1E7A4C"/>
  <g stroke="#3DDC84" stroke-width="3" opacity="0.7">
    <path d="M60 420 L90 300"/><path d="M140 420 L170 300"/><path d="M220 420 L250 300"/>
    <path d="M300 420 L330 300"/><path d="M380 420 L410 300"/><path d="M460 420 L490 300"/>
    <path d="M540 420 L570 300"/><path d="M620 420 L650 300"/><path d="M700 420 L730 300"/>
  </g>
  <text x="40" y="395" font-family="Arial, sans-serif" font-size="22" font-weight="700" fill="#ffffff" opacity="0.95">Monitoramento climático das unidades</text>
</svg>
"""

_SLIDE_4_TRANSPORTE = """
<svg viewBox="0 0 800 420" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="sky4" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#6C5CE7"/>
      <stop offset="60%" stop-color="#E08A4C"/>
      <stop offset="100%" stop-color="#F5C15D"/>
    </linearGradient>
  </defs>
  <rect width="800" height="420" fill="url(#sky4)"/>
  <circle cx="140" cy="110" r="46" fill="#FFE7A8" opacity="0.9"/>
  <rect x="0" y="300" width="800" height="120" fill="#2b2f4a"/>
  <rect x="0" y="292" width="800" height="10" fill="#F5C15D" opacity="0.7"/>
  <g transform="translate(420,220)">
    <rect x="0" y="40" width="220" height="55" rx="6" fill="#4F7DF3"/>
    <rect x="220" y="0" width="70" height="95" rx="6" fill="#3a4270"/>
    <rect x="232" y="14" width="26" height="22" rx="3" fill="#A9CBFF"/>
    <circle cx="50" cy="102" r="22" fill="#121936"/>
    <circle cx="50" cy="102" r="9" fill="#F5C15D"/>
    <circle cx="170" cy="102" r="22" fill="#121936"/>
    <circle cx="170" cy="102" r="9" fill="#F5C15D"/>
    <circle cx="255" cy="102" r="22" fill="#121936"/>
    <circle cx="255" cy="102" r="9" fill="#F5C15D"/>
  </g>
  <text x="40" y="395" font-family="Arial, sans-serif" font-size="22" font-weight="700" fill="#ffffff" opacity="0.95">Logística e transporte da safra</text>
</svg>
"""

_SLIDES = [_SLIDE_1_CANAVIAL, _SLIDE_2_TRATOR, _SLIDE_3_CLIMA, _SLIDE_4_TRANSPORTE]

_DURACAO_TOTAL_S = 4 * len(_SLIDES)  # 4s por slide


def render_agro_carousel(height_px: int = 260) -> None:
    """Renderiza o slide de ilustrações agro em crossfade automático, em
    CSS puro (sem JavaScript — funciona mesmo com scripts bloqueados)."""
    import streamlit as st

    slots = []
    for i, svg in enumerate(_SLIDES):
        delay = i * 4
        slots.append(
            f'<div class="agro-slide" style="animation-delay:{delay}s;">{svg}</div>'
        )

    html = f"""
    <style>
    .agro-carousel {{
        position: relative;
        width: 100%;
        height: {height_px}px;
        border-radius: 16px;
        overflow: hidden;
        background: {BG_CARD};
        border: 1px solid {BORDER};
        box-shadow: 0 8px 28px rgba(0,0,0,0.35);
        margin-bottom: 14px;
    }}
    .agro-slide {{
        position: absolute;
        inset: 0;
        opacity: 0;
        animation: agroFade {_DURACAO_TOTAL_S}s ease-in-out infinite;
    }}
    .agro-slide svg {{
        width: 100%;
        height: 100%;
        display: block;
    }}
    @keyframes agroFade {{
        0%   {{ opacity: 0; }}
        3%   {{ opacity: 1; }}
        22%  {{ opacity: 1; }}
        28%  {{ opacity: 0; }}
        100% {{ opacity: 0; }}
    }}
    </style>
    <div class="agro-carousel">
        {''.join(slots)}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)
