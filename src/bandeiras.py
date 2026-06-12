# Mapeamento estático de bandeiras

MAPA_BANDEIRAS = {
    "Argentina": "🇦🇷",
    "Brazil": "🇧🇷",
    "France": "🇫🇷",
    "Spain": "🇪🇸",
    "England": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", # ISO-3166-2:GB-ENG
    "Germany": "🇩🇪",
    "Portugal": "🇵🇹",
    "Netherlands": "🇳🇱",
    "Italy": "🇮🇹",
    "Croatia": "🇭🇷",
    "Belgium": "🇧🇪",
    "Uruguay": "🇺🇾",
    "Colombia": "🇨🇴",
    "United States": "🇺🇸",
    "Mexico": "🇲🇽",
    "Senegal": "🇸🇳",
    "Morocco": "🇲🇦",
    "Japan": "🇯🇵",
    "South Korea": "🇰🇷",
    "Iran": "🇮🇷",
    "Australia": "🇦🇺",
    "Switzerland": "🇨🇭",
    "Denmark": "🇩🇰",
    "Sweden": "🇸🇪",
    "Serbia": "🇷🇸",
    "Poland": "🇵🇱",
    "Wales": "🏴󠁧󠁢󠁷󠁬󠁳󠁿",
    "Scotland": "🏴󠁧󠁢󠁳󠁣󠁴󠁿",
    "Tunisia": "🇹🇳",
    "Cape Verde": "🇨🇻",
    "DR Congo": "🇨🇩",
    "Czech Republic": "🇨🇿"
}

def obter_bandeira(selecao: str) -> str:
    """Retorna o Emoji da Bandeira se mapeado, ou a bandeira branca como fallback."""
    return MAPA_BANDEIRAS.get(selecao, "🏳️")

def com_bandeira(selecao: str) -> str:
    """Retorna o nome formatado ex: 🇧🇷 Brazil"""
    return f"{obter_bandeira(selecao)} {selecao}"
