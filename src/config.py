"""
Uppa! - Arquivo de Configuração Centralizado
Todas as constantes e configurações do aplicativo em um único lugar.
"""

import os
import logging
from pathlib import Path

# =============================================================================
# PATHS
# =============================================================================
APP_NAME = "Uppa!"
APP_VERSION = "0.2.8"
APP_AUTHOR = "David"

# Diretório base do app (compatível com PyInstaller)
if getattr(os.sys, 'frozen', False):
    BASE_DIR = Path(os.sys._MEIPASS)
else:
    BASE_DIR = Path(__file__).parent

ASSETS_DIR = BASE_DIR / "assets"
SOUNDS_DIR = ASSETS_DIR / "sounds"
IMAGES_DIR = ASSETS_DIR / "images"
DB_PATH = BASE_DIR.parent / "uppa_data.db"

# =============================================================================
# XP & PROGRESSÃO
# =============================================================================
XP_GANHO_FOCO = 5          # +5 XP a cada 2 min focado
XP_PUNICAO = 15            # -15 XP por distração
XP_COMBO = 50              # +50 XP por 25 min sem distrações
TEMPO_RECOMPENSA = 120     # 2 minutos (intervalo de ganho passivo)
COMBO_TIME = 1500          # 25 minutos (tempo para combo)
TEMPO_PUNICAO = 30         # 30 segundos em app distrator = punição

# XP por nível de tarefa
XP_POR_NIVEL = {
    1: 10,
    2: 20,
    3: 30,
    4: 40,
    5: 50
}

# =============================================================================
# MANA (MOEDA)
# =============================================================================
MANA_POR_NIVEL = {
    1: 5,
    2: 15,
    3: 30,
    4: 60,
    5: 100
}
MANA_POMODORO = 10  # +10 Mana ao completar ciclo

# =============================================================================
# UI & JANELA
# =============================================================================
WINDOW_TITLE = f"{APP_NAME} - Seu mascote de produtividade (Alpha {APP_VERSION})"
WINDOW_DEFAULT_SIZE = "1280x720"
WINDOW_MIN_WIDTH = 1024
WINDOW_MIN_HEIGHT = 600

# Tema
DEFAULT_THEME = "dark"  # "dark" ou "light"
COLOR_THEME = "blue"

# Tema (Neo-Black com Roxo e Amarelo)
THEME = {
    "bg_main": "#0D0D0D",      # Preto profundo / Fundo base
    "bg_card": "#1A1A1A",      # Cinza super escuro / Cartões
    "text_main": "#FDFBFF",    # Branco perolado / Textos
    "text_sec": "#A3A3A3",     # Cinza médio / Secundário
    "border": "#361D59",       # Bordas roxas escuras
    "success": "#00E676",      # Verde vivo
    "warning": "#FFEA00",      # Amarelo alerta
    "danger": "#FF1744",       # Vermelho vivo
    "primary": "#8A2BE2",      # Azul Violeta (Roxo vibrante)
    "primary_hover": "#6A1B9A",# Roxo escuro no hover
    "secondary": "#261635",    # Roxo desativado/fundo
    "bg_container": "#121212"
}

# Cores fixas e Acentos
COLORS = {
    "accent": "#FFC857",      # Amarelo Ouro
    "accent_hover": "#FFD54F",
    "gold": "#FFC857",        
    "mana": "#00E5FF",        # Ciano para Mana
    "xp": "#FFC857",          # XP Amarelo
    "health": "#FF1744"
}

# =============================================================================
# POMODORO PRESETS
# =============================================================================
POMODORO_PRESETS = {
    "curto": {"foco": 15, "descanso": 5},
    "medio": {"foco": 30, "descanso": 5},
    "longo": {"foco": 50, "descanso": 10}
}

# =============================================================================
# VALIDAÇÃO DE INPUTS
# =============================================================================
MAX_TITULO_LENGTH = 100
MAX_DESCRICAO_LENGTH = 500
MIN_TITULO_LENGTH = 3

# =============================================================================
# LOGGING
# =============================================================================
LOG_LEVEL = logging.INFO
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FILE = BASE_DIR.parent / "uppa.log"
LOG_MAX_BYTES = 5 * 1024 * 1024  # 5MB
LOG_BACKUP_COUNT = 3

# =============================================================================
# DESAFIOS DIÁRIOS
# =============================================================================
DAILY_CHALLENGES_COUNT = 3  # Quantidade de desafios por dia

# Pool de desafios disponíveis
DAILY_CHALLENGES_POOL = [
    {
        "code": "foco_matinal",
        "name": "🌅 Foco Matinal",
        "description": "Complete 1 Pomodoro antes das 10h",
        "condition": "pomodoro_before_10",
        "xp_reward": 30,
        "mana_reward": 15
    },
    {
        "code": "produtivo",
        "name": "✅ Produtivo",
        "description": "Complete 3 tarefas hoje",
        "condition": "tasks_completed_3",
        "xp_reward": 50,
        "mana_reward": 25
    },
    {
        "code": "maratonista",
        "name": "🔥 Maratonista",
        "description": "Acumule 2h de foco hoje",
        "condition": "focus_2h",
        "xp_reward": 100,
        "mana_reward": 50
    },
    {
        "code": "impecavel",
        "name": "🛡️ Impecável",
        "description": "Nenhuma distração hoje",
        "condition": "no_distractions",
        "xp_reward": 75,
        "mana_reward": 40
    },
    {
        "code": "comecou_bem",
        "name": "🎯 Começou Bem",
        "description": "Complete 1 tarefa até 9h",
        "condition": "task_before_9",
        "xp_reward": 25,
        "mana_reward": 10
    },
    {
        "code": "streak_fire",
        "name": "🔥 Em Chamas",
        "description": "Mantenha 3 combos no dia",
        "condition": "combos_3",
        "xp_reward": 60,
        "mana_reward": 30
    },
    {
        "code": "noturno",
        "name": "🦉 Coruja Noturna",
        "description": "Complete 1 Pomodoro após 22h",
        "condition": "pomodoro_after_22",
        "xp_reward": 30,
        "mana_reward": 15
    },
    {
        "code": "focus_total",
        "name": "⏰ Foco Total",
        "description": "Complete 4 Pomodoros hoje",
        "condition": "pomodoros_4",
        "xp_reward": 80,
        "mana_reward": 40
    }
]

# =============================================================================
# LICENCIAMENTO
# =============================================================================
LICENSE_PROVIDER = "lemonsqueezy"
LICENSE_API_URL = "https://api.lemonsqueezy.com/v1"
LICENSE_PRODUCT_ID = ""  # Preencher após criar produto no LemonSqueezy

# =============================================================================
# FUNÇÕES AUXILIARES
# =============================================================================

def setup_logging():
    """Configura o sistema de logging do app."""
    from logging.handlers import RotatingFileHandler
    
    # Criar logger raiz
    logger = logging.getLogger("uppa")
    logger.setLevel(LOG_LEVEL)
    
    # Handler para arquivo (rotativo)
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(file_handler)
    
    # Handler para console (apenas em dev)
    if not getattr(os.sys, 'frozen', False):
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
        logger.addHandler(console_handler)
    
    return logger


def get_logger(name: str = "uppa"):
    """Retorna um logger com o nome especificado."""
    return logging.getLogger(name)


import re

def sanitize_input(text: str) -> str:
    """Limpa caracteres perigosos de texto livre (Defensive Coding)"""
    if not text:
        return ""
    # Remove tags HTML simples
    text = re.sub(r'<[^>]*>', '', text)
    # Escapa pipes e aspas duplas abusivas para evitar quebras em logs
    return text.replace('"', '\"')

def validate_task_title(title: str) -> tuple[bool, str, str]:
    """
    Valida e higieniza o título de uma tarefa.
    
    Returns:
        (is_valid, error_message, sanitized_title)
    """
    if not title or not title.strip():
        return False, "Título não pode ser vazio", ""
    
    title = title.strip()
    
    if len(title) < MIN_TITULO_LENGTH:
        return False, f"Título deve ter pelo menos {MIN_TITULO_LENGTH} caracteres", ""
    
    if len(title) > MAX_TITULO_LENGTH:
        return False, f"Título deve ter no máximo {MAX_TITULO_LENGTH} caracteres", ""
    
    return True, "", sanitize_input(title)


def validate_task_description(description: str) -> tuple[bool, str, str]:
    """
    Valida e higieniza a descrição de uma tarefa.
    
    Returns:
        (is_valid, error_message, sanitized_description)
    """
    if description and len(description) > MAX_DESCRICAO_LENGTH:
        return False, f"Descrição deve ter no máximo {MAX_DESCRICAO_LENGTH} caracteres", ""
    
    return True, "", sanitize_input(description)
