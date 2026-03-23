import customtkinter as ctk
from datetime import datetime
import sqlite3
import time
import sys
from PIL import Image
from database import (
    carregar_tarefas, adicionar_tarefa, editar_tarefa, 
    deletar_tarefa, concluir_tarefa, carregar_progresso,
    adicionar_xp, carregar_historico, adicionar_ao_historico,
    get_unlocked_achievements, get_task_stats, unlock_achievement,
    adicionar_mana, obter_mana_total,  # MANA SYSTEM
    get_inventory, restaurar_tarefa, remove_item, # INVENTORY SYSTEM
    get_all_stats, get_character_class, adicionar_stat_points,  # RPG STATS
    add_active_effect, get_active_effects, activate_pending_effect, is_effect_active, # EFFECTS SYSTEM
    log_pomodoro,  # POMODORO LOG
    get_setting, # SETTINGS
    get_user_stats, # USER STATS
    process_daily_recurrences # RECURRENCE
)
import winsound
import os
import threading
from sound_manager import get_audio_manager
from stats_visualizer import create_radar_chart
from challenges_manager import ChallengesManager
from reports_window import ReportsWindow
from onboarding import OnboardingOverlay
from config import (
    get_logger, validate_task_title, validate_task_description,
    WINDOW_TITLE, WINDOW_DEFAULT_SIZE, WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT,
    COLORS, THEME, MAX_TITULO_LENGTH, MAX_DESCRICAO_LENGTH
)
from widgets import PremiumCard, GlowFrame, AnimatedProgressBar, IconButton, create_glow_effect

# Logger para GUI
logger = get_logger("uppa.gui")

try:
    from win11toast import toast
    _toaster_gui_available = True
except ImportError:
    toast = None
    _toaster_gui_available = False

def _notificar(titulo, msg, duracao=3):
    """Helper GUI para notificações (async para não travar a interface)"""
    if not _toaster_gui_available:
        return
    
    def _enviar_toast_gui():
        try:
            toast(titulo, msg, duration='short' if duracao <= 3 else 'long')
        except Exception:
            pass
    
    # Executar em thread separada para não bloquear a UI
    threading.Thread(target=_enviar_toast_gui, daemon=True).start()

def _animar_feedback(widget, color_flash=None, duration_ms=200):
    """Animação de feedback: pisca cor e volta (thread-safe via after())"""
    if color_flash is None:
        color_flash = THEME["success"]
        
    try:
        # Pega a cor original (suporta tupla ou string)
        original_color = widget.cget("fg_color")
        widget.configure(fg_color=color_flash)
        # Restaurar cor original após duration usando after() (thread-safe)
        widget.after(duration_ms, lambda: _safe_configure(widget, "fg_color", original_color))
    except Exception as e:
        logger.warning(f"Erro na animação: {e}")

def _safe_configure(widget, prop, value):
    """Configura widget de forma segura (ignora se destruído)"""
    try:
        widget.configure(**{prop: value})
    except Exception:
        pass

class CTkToolTip:
    """Tooltip simples para CustomTkinter com delay"""
    def __init__(self, widget, text, delay=300):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.tooltip = None
        self.schedule_id = None
        
        self.widget.bind("<Enter>", self.schedule_show)
        self.widget.bind("<Leave>", self.hide)
        self.widget.bind("<ButtonPress>", self.hide) # Esconder ao clicar

    def schedule_show(self, event=None):
        self.schedule_id = self.widget.after(self.delay, self.show)

    def show(self):
        if self.tooltip: return # Já exibindo
        
        # Calcular posição
        try:
            x, y, _, _ = self.widget.bbox("insert")
            x += self.widget.winfo_rootx() + 25
            y += self.widget.winfo_rooty() + 25
            
            self.tooltip = ctk.CTkToplevel(self.widget)
            self.tooltip.wm_overrideredirect(True)
            self.tooltip.wm_geometry(f"+{x}+{y}")
            self.tooltip.attributes("-topmost", True)
            # Evitar foco
            self.tooltip.overrideredirect(True)
            
            # Container com borda
            frame = ctk.CTkFrame(
                self.tooltip,
                fg_color="#9d4edd", # Borda
                corner_radius=6
            )
            frame.pack(fill="both", expand=True)

            label = ctk.CTkLabel(
                frame, 
                text=self.text, 
                fg_color=THEME["bg_card"], # Fundo temático
                text_color=THEME["text_main"],
                font=("Roboto", 10),
                corner_radius=5,
                width=200,
                wraplength=190
            )
            label.pack(padx=1, pady=1, fill="both", expand=True)
            
        except Exception as e:
            print(f"Erro tooltip: {e}")
            if self.tooltip:
                self.tooltip.destroy()
                self.tooltip = None

    def hide(self, event=None):
        # Cancelar agendamento se existir
        if self.schedule_id:
            self.widget.after_cancel(self.schedule_id)
            self.schedule_id = None
            
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None

# Configurar theme defaults (movido para UppaApp.__init__)
ctk.set_default_color_theme("blue")

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # Em desenvolvimento, estamos em src/
        # Assets estao em src/assets
        base_path = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base_path, relative_path)


class UppaApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(WINDOW_TITLE)
        self.geometry(WINDOW_DEFAULT_SIZE)
        self.minsize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        
        # Tema inicial (padrão Dark)
        ctk.set_appearance_mode("Dark")
        self.configure(fg_color=THEME["bg_main"])  # Adapta ao tema
        
        # Dados
        self.tarefas = []
        # Presets: [foco_minutos, descanso_minutos]
        self.pomodoro_atual = 0
        self.lontra_images = {}  # Cache de imagens da lontra
        
        # VISUAL UPGRADE: Referência para spotlight (para animações)
        self.spotlight_frame = None
        self.ultimo_xp = 0  # Para detectar ganho de XP
        
        # Pomodoro & Monitoramento
        self.pomodoro_ativo = False
        self.pomodoro_pausado = False
        self.pomodoro_tempo_restante = 0  # em segundos
        self.pomodoro_em_descanso = False  # Flag se está em descanso
        self.pomodoro_ciclo_contador = 0  # Contador de ciclos (0 = pausa curta, 1 = pausa longa)
        self.timer_thread = None
        
        # Presets: (Foco, Pausa Curta, Pausa Longa)
        self.pomodoro_presets = [
            (15, 5, 10),   # 15min foco, 5min pausa curta, 10min pausa longa
            (30, 10, 15),  # 30min foco, 10min pausa curta, 15min pausa longa
            (50, 15, 20)   # 50min foco, 15min pausa curta, 20min pausa longa
        ]
        self.pomodoro_atual = 0
        
        # Setup UI
        process_daily_recurrences()  # PROCESSA RECORRÊNCIAS DIÁRIAS ANTES DE CARREGAR A UI
        self.setup_ui()
        self.carregar_tarefas()
        self.atualizar_ui()
        
        # Iniciar verificador de prazos
        self.verificar_prazos()

        # Verificar Tutorial
        try:
            if get_setting("tutorial_completed") == "0":
                # Delay pequeno para garantir que a UI carregou
                self.after(1000, lambda: OnboardingOverlay(self))
        except Exception as e:
            logger.error(f"Erro ao verificar tutorial: {e}")
        


    def setup_ui(self):
        """Cria interface com layout de 3 colunas otimizado"""
        
        # CONTAINER PRINCIPAL - 3 COLUNAS
        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Configurar GRID RESPONSIVO
        main_container.grid_rowconfigure(0, weight=1)
        main_container.grid_columnconfigure(0, weight=0, minsize=260)  # Esquerda rígida mas adaptável
        main_container.grid_columnconfigure(1, weight=1)               # Centro totalmente elástico
        main_container.grid_columnconfigure(2, weight=0, minsize=270)  # Direita rígida mas adaptável
        
        # ===== COLUNA ESQUERDA: RPG PROFILE =====
        self.left_column = ctk.CTkFrame(main_container, fg_color="transparent")
        self.left_column.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        
        self.criar_rpg_profile()
        
        # ===== COLUNA CENTRO: TASK MANAGER (expansível) =====
        self.center_column = ctk.CTkFrame(main_container, fg_color="transparent")
        self.center_column.grid(row=0, column=1, sticky="nsew", padx=5)
        
        self.criar_task_manager()
        
        # ===== COLUNA DIREITA: FOCUS ZONE =====
        self.right_column = ctk.CTkFrame(main_container, fg_color="transparent")
        self.right_column.grid(row=0, column=2, sticky="nsew", padx=(5, 0))
        
        self.criar_focus_zone()
    
    def criar_rpg_profile(self):
        """COLUNA ESQUERDA: RPG Profile - Lontra + Stats + Inventário"""
        # Card principal - PREMIUM
        card = ctk.CTkScrollableFrame(
            self.left_column,
            fg_color=THEME["bg_card"],
            corner_radius=24,
            border_width=2,
            border_color=THEME["border"],
            scrollbar_button_color=THEME["bg_card"], 
            scrollbar_button_hover_color=COLORS["accent"]
        )
        card.pack(fill="both", expand=True)
        
        # Inner removido, usando card direto (que é scrollable)
        inner = card
        
        # Avatar da Lontra (REDUZIDO: 120x120)
        self.label_imagem_lontra = ctk.CTkLabel(
            inner, text="",
            fg_color="transparent"
        )
        self.label_imagem_lontra.pack(pady=(0, 5)) # Reduced padding
        
        # Nível + Título + Toggle Button
        header_frame = ctk.CTkFrame(inner, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 5))
        
        # Level info (Left)
        level_info = ctk.CTkFrame(header_frame, fg_color="transparent")
        level_info.pack(side="left")

        self.label_nivel = ctk.CTkLabel(
            level_info, text="N1",
            font=("Roboto", 18, "bold"),
            text_color=COLORS["gold"]
        )
        self.label_nivel.pack(side="left")
        
        self.label_titulo = ctk.CTkLabel(
            level_info, text="Aprendiz",
            font=("Roboto", 10),
            text_color=THEME["text_sec"]
        )
        self.label_titulo.pack(side="left", padx=(5, 0))
        
        # Streak info (Right)
        self.label_streak = ctk.CTkLabel(
            header_frame, text="🔥 0",
            font=("Roboto", 12, "bold"),
            text_color="#ff7b00"
        )
        self.label_streak.pack(side="right", padx=(0, 5))
        

        
        # XP compacto
        self.label_xp = ctk.CTkLabel(
            inner, text="0/100 XP",
            font=("Roboto", 10),
            text_color=COLORS["accent"]
        )
        self.label_xp.pack()
        
        # Barra XP - ANIMADA
        self.progress_xp = AnimatedProgressBar(
            inner,
            fg_color="#1a0436",
            progress_color=THEME["primary"],
            height=12,
            corner_radius=6
        )
        self.progress_xp.pack(fill="x", pady=(3, 2))
        self.progress_xp.set(0)

        # Percentual XP (NOVO - Fixando erro)
        self.label_percent = ctk.CTkLabel(
            inner, text="0%",
            font=("Roboto", 9),
            text_color="#c77dff"
        )
        self.label_percent.pack()
        
        # Mana compacto
        self.label_mana = ctk.CTkLabel(
            inner, text="💎 0",
            font=("Roboto", 11, "bold"),
            text_color="#00d4ff"
        )
        self.label_mana.pack(pady=(5, 0))
        
        # Separador
        sep = ctk.CTkFrame(inner, height=1, fg_color="#2a2f4a")
        sep.pack(fill="x", pady=5) # Reduced padding
        
        # INVENTÁRIO COMPACTO
        ctk.CTkLabel(
            inner, text="🎒 Itens",
            font=("Roboto", 10, "bold"),
            text_color="#aaa"
        ).pack(anchor="w")
        
        self.inventario_hud_frame = ctk.CTkFrame(
            inner,
            fg_color="#1a0436",
            corner_radius=6,
            height=35
        )
        self.inventario_hud_frame.pack(fill="x", pady=(3, 0))
        self.inventario_hud_frame.pack_propagate(False)
        
        self.atualizar_inventario_hud()
        
        # Separador
        sep2 = ctk.CTkFrame(inner, height=1, fg_color="#2a2f4a")
        sep2.pack(fill="x", pady=5) # Reduced padding
        
        # STATS RPG com Radar Chart
        stats_header = ctk.CTkFrame(inner, fg_color="transparent")
        stats_header.pack(fill="x", pady=(0, 5))

        ctk.CTkLabel(
            stats_header, text="📊 Stats",
            font=("Roboto", 10, "bold"),
            text_color="#aaa"
        ).pack(side="left")

        # Tarefas Totais (NOVO - Fixando erro)
        self.label_stats_tarefas = ctk.CTkLabel(
            stats_header, text="0",
            font=("Roboto", 10, "bold"),
            text_color="#51cf66"
        )
        self.label_stats_tarefas.pack(side="right")
        
        # Frame para gráfico radar
        self.radar_frame = ctk.CTkFrame(
            inner,
            fg_color="transparent"
        )
        self.radar_frame.pack(fill="x")
        
        # Classe/Título RPG
        self.label_classe = ctk.CTkLabel(
            inner, text="Iniciante",
            font=("Roboto", 11, "bold"),
            text_color="#ffd60a"
        )
        self.label_classe.pack(pady=(5, 0))
        
        self.label_classe_desc = ctk.CTkLabel(
            inner, text="Sua jornada começa...",
            font=("Roboto", 8),
            text_color="#666",
            wraplength=180
        )
        self.label_classe_desc.pack()
        
        # Atualizar radar chart
        self.atualizar_radar_chart()
        
        # LEGENDA DE ATRIBUTOS
        legend_frame = ctk.CTkFrame(inner, fg_color="transparent")
        legend_frame.pack(fill="x", pady=(5, 0)) # Reduced padding
        
        atributos = [
            ("INT", "Estudo/Leitura"),
            ("DEX", "Trabalho/Projeto"),
            ("STR", "Físicas/Domésticas"),
            ("CHA", "Sociais/Reuniões"),
            ("CRI", "Arte/Criação")
        ]
        
        for sigla, desc in atributos:
            row = ctk.CTkFrame(legend_frame, fg_color="transparent", height=18)
            row.pack(fill="x", pady=1)
            
            ctk.CTkLabel(
                row, text=sigla, 
                font=("Roboto", 10, "bold"), 
                text_color="#c77dff", 
                width=50, 
                anchor="w"
            ).pack(side="left")
            
            ctk.CTkLabel(
                row, text=desc,
                font=("Roboto", 10), 
                text_color="#aaa"
            ).pack(side="left", padx=(0, 0))
            
        # Separador final
        ctk.CTkFrame(inner, height=1, fg_color="#2a2f4a").pack(fill="x", pady=10)
        
        # --- CONTROLE DE VOLUME ---
        vol_frame = ctk.CTkFrame(inner, fg_color="transparent")
        vol_frame.pack(fill="x", pady=(0, 5))
        
        # Obter Audio Manager
        am = get_audio_manager()
        
        if am.using_pygame:
            # Header Volume + Mute
            v_header = ctk.CTkFrame(vol_frame, fg_color="transparent")
            v_header.pack(fill="x")
            
            ctk.CTkLabel(
                v_header, text="🔊 Volume", 
                font=("Roboto", 10, "bold"), text_color="#aaa"
            ).pack(side="left")
            
            # Slider
            self.vol_slider = ctk.CTkSlider(
                vol_frame,
                from_=0, to=1,
                number_of_steps=20,
                height=15,
                progress_color="#7209b7",
                button_color="#b44fff",
                button_hover_color="#e0aaff",
                command=self.mudar_volume
            )
            self.vol_slider.set(0.5) # Default
            self.vol_slider.pack(fill="x", pady=(5, 0))
        else:
            # Fallback msg
            ctk.CTkLabel(
                vol_frame, 
                text="🔊 Áudio Básico (Winsound)", 
                font=("Roboto", 10, "bold"), text_color="#666"
            ).pack(anchor="w")
            ctk.CTkLabel(
                vol_frame, 
                text="Instale 'pygame' p/ volume.", 
                font=("Roboto", 9), text_color="#444"
            ).pack(anchor="w")
            
        # Botão Conquistas
        self.btn_conquistas = ctk.CTkButton(
            inner, text="🏆 Mural de Conquistas",
            fg_color="#ffd60a", text_color="#1a0436", hover_color="#facc15",
            font=("Roboto", 11, "bold"),
            command=self.abrir_mural_conquistas
        )
        self.btn_conquistas.pack(fill="x", pady=(10, 10))
        
        # --- SEÇÃO DE DESAFIOS DIÁRIOS ---
        ctk.CTkFrame(inner, height=1, fg_color=THEME["border"]).pack(fill="x", pady=10)
        
        ctk.CTkLabel(
            inner, text="🎯 Desafios do Dia",
            font=("Roboto", 11, "bold"),
            text_color="#ffd60a"
        ).pack(anchor="w")
        
        # Frame para desafios
        self.challenges_frame = ctk.CTkFrame(inner, fg_color="transparent")
        self.challenges_frame.pack(fill="x", pady=(5, 0))
        
        # Inicializar desafios
        self.atualizar_desafios_ui()
        
    def abrir_mural_conquistas(self):
        """Abre janela com o quadro de conquistas"""
        win = ctk.CTkToplevel(self)
        win.title("Mural de Conquistas")
        win.geometry("500x400")
        win.configure(fg_color="#0f111a")
        win.attributes('-topmost', True)
        win.grab_set()

        ctk.CTkLabel(
            win, text="🏆 Suas Conquistas",
            font=("Roboto", 20, "bold"), text_color="#ffd60a"
        ).pack(pady=10)

        scroll = ctk.CTkScrollableFrame(win, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10, pady=10)

        # Buscar conquistas do banco
        try:
            from database import _get_db_connection
            with _get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name, description, data_desbloqueio FROM achievements ORDER BY data_desbloqueio DESC")
                achievements = cursor.fetchall()
        except:
            achievements = []

        if not achievements:
            ctk.CTkLabel(
                scroll, text="Ainda não há conquistas desbloqueadas.\\nComplete tarefas para ganhar!",
                font=("Roboto", 12), text_color="#666"
            ).pack(pady=40)
            return

        for name, desc, data in achievements:
            card = ctk.CTkFrame(scroll, fg_color="#1a1f3a", corner_radius=8)
            card.pack(fill="x", pady=5)
            
            ctk.CTkLabel(
                card, text=f"🏅 {name}",
                font=("Roboto", 14, "bold"), text_color="#51cf66"
            ).pack(anchor="w", padx=10, pady=(5,0))
            
            data_formatada = data[:10] if data else "Recentemente"
            ctk.CTkLabel(
                card, text=f"{desc} • Desbloqueado em {data_formatada}",
                font=("Roboto", 11), text_color="#aaa"
            ).pack(anchor="w", padx=10, pady=(0,5))
    
    
    def criar_task_manager(self):
        """COLUNA CENTRO: Task Manager - Lista de Tarefas (V2 Sem Abas)"""
        # Container principal
        self.main_task_frame = ctk.CTkFrame(self.center_column, fg_color="transparent")
        self.main_task_frame.pack(fill="both", expand=True)
        
        # --- HEADER ---
        header = ctk.CTkFrame(self.main_task_frame, fg_color="transparent")
        header.pack(fill="x", pady=(0, 15))
        
        # Título
        ctk.CTkLabel(
            header, text="⚔️ Missões Ativas",
            font=("Roboto", 20, "bold"),
            text_color=THEME["text_main"]
        ).pack(side="left")
        
        # Botão Nova Tarefa (Destaque)
        ctk.CTkButton(
            header,
            text="+ Nova Missão",
            font=("Roboto", 12, "bold"),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            height=35,
            width=140,
            corner_radius=18,
            command=self.dialog_nova_tarefa
        ).pack(side="right")
        
        # Botão Relatórios
        ctk.CTkButton(
            header,
            text="📊",
            font=("Segoe UI Emoji", 16),
            fg_color="#2a1050",
            hover_color="#3c096c",
            height=35,
            width=45,
            corner_radius=18,
            command=self.abrir_relatorios
        ).pack(side="right", padx=(0, 10))
        
        # --- FILTROS (Segmented Button) ---
        self.filter_var = ctk.StringVar(value="Ativas")
        self.filter_button = ctk.CTkSegmentedButton(
            self.main_task_frame,
            values=["Ativas", "Histórico"],
            variable=self.filter_var,
            command=self.mudar_filtro_tarefas,
            selected_color="#9d4edd",
            selected_hover_color="#c77dff",
            unselected_color="#240046",
            unselected_hover_color="#3c096c",
            text_color="#e0e0e0"
        )
        self.filter_button.pack(fill="x", pady=(0, 10))
        
        # --- LISTA SCROLLÁVEL ---
        self.tarefas_scroll_frame = ctk.CTkScrollableFrame(
            self.main_task_frame,
            fg_color="transparent",
            label_text=""
        )
        self.tarefas_scroll_frame.pack(fill="both", expand=True)
        
        # Carregar tarefas iniciais
        self.atualizar_lista_tarefas()

    def mudar_filtro_tarefas(self, valor):
        """Callback para troca de filtro"""
        if valor == "Ativas":
            self.atualizar_lista_tarefas()
        else:
            self.atualizar_lista_historico()

    def mudar_volume(self, value):
        """Callback do slider de volume"""
        get_audio_manager().set_volume(value)

    # (Método criar_secao_tarefas REMOVIDO pois foi substituído por criar_task_manager)

    def criar_focus_zone(self):
        """COLUNA DIREITA: Focus Zone - Pomodoro + Loja (Alternável)"""
        # Container para conteúdo dinâmico (Timer ou Loja)
        self.right_content_frame = ctk.CTkFrame(self.right_column, fg_color="transparent")
        self.right_content_frame.pack(fill="both", expand=True)
        
        # Estado inicial
        self.right_view_mode = "POMODORO"
        self.atualizar_right_column()
        
    def atualizar_right_column(self):
        """Renderiza o conteúdo da coluna direita baseado no modo"""
        # Limpar
        for widget in self.right_content_frame.winfo_children():
            widget.destroy()
            
        if self.right_view_mode == "POMODORO":
            self._render_pomodoro_view()
        else:
            self._render_shop_view()
            
    def _render_pomodoro_view(self):
        # Pomodoro Compacto
        self.criar_pomodoro_section_compact()
        
        # Botão 'Visitar o Mercador' foi removido para focar na estética limpa e Modo Foco.

    def _render_shop_view(self):
        # Header Loja
        header = ctk.CTkFrame(self.right_content_frame, fg_color="transparent")
        header.pack(fill="x", padx=5, pady=(0, 10))
        
        ctk.CTkLabel(
            header, text="🛒 Mercador",
            font=("Roboto", 16, "bold"),
            text_color=COLORS["gold"]
        ).pack(side="left")
        
        # Botão Voltar
        ctk.CTkButton(
            header, text="🔙", width=30, height=30,
            fg_color=THEME["bg_card"], hover_color=THEME["border"],
            command=self.toggle_shop_view
        ).pack(side="right")
        
        # Saldo
        ctk.CTkLabel(
            self.right_content_frame, 
            text=f"💎 {obter_mana_total()} Mana",
            font=("Roboto", 14, "bold"),
            text_color=COLORS["mana"]
        ).pack(pady=(0, 10))
        
        # --- SEÇÃO DE EFEITOS ATIVOS (VISÍVEL NA LOJA) ---
        self.effects_frame_loja = ctk.CTkFrame(self.right_content_frame, fg_color="transparent")
        self.effects_frame_loja.pack(fill="x", pady=(0, 10), padx=5)
        # O update_ui vai popular isso
        # -------------------------------------------------
        
        # Container da Loja (usado pelo criar_loja_grid)
        self.loja_frame = ctk.CTkScrollableFrame(
            self.right_content_frame,
            fg_color="transparent",
            height=400 # Altura fixa para scroll
        )
        self.loja_frame.pack(fill="both", expand=True, padx=5)
        
        self.criar_loja_grid()

    def toggle_shop_view(self):
        """Alterna entre Pomodoro e Loja"""
        if self.right_view_mode == "POMODORO":
            self.right_view_mode = "SHOP"
        else:
            self.right_view_mode = "POMODORO"
        self.atualizar_right_column()

    def criar_pomodoro_section_compact(self):
        """Versão CIRCULAR do Pomodoro para coluna direita"""
        # Card Pomodoro - PREMIUM
        card = ctk.CTkScrollableFrame(
            self.right_content_frame,
            fg_color=THEME["bg_card"],
            corner_radius=4, # Brutalista / Menos redondo
            border_width=2,
            border_color=THEME["border"],
            scrollbar_button_color=THEME["bg_card"],
            scrollbar_button_hover_color=COLORS["accent"]
        )
        card.pack(fill="both", expand=True, padx=5, pady=5)
        
        inner = card # Usar direto o frame scrollável
        
        # Botão para abrir a Loja
        header = ctk.CTkFrame(inner, fg_color="transparent")
        header.pack(fill="x", pady=(0, 10))
        
        ctk.CTkButton(
            header, text="Loja 🪙",
            font=("Roboto", 11, "bold"),
            text_color="#1a0436", fg_color="#ffd60a", hover_color="#facc15",
            width=60, height=28,
            command=self.toggle_shop_view
        ).pack(side="right")
        
        # CANVAS CIRCULAR COM PROGRESSO
        canvas_size = 200
        self.timer_canvas = ctk.CTkCanvas(
            inner,
            width=canvas_size,
            height=canvas_size,
            bg=THEME["bg_card"], # Fundo temático invés de azul escuro fixo
            highlightthickness=0
        )
        self.timer_canvas.pack(pady=(10, 15))
        
        # Desenhar círculo de fundo
        center = canvas_size / 2
        radius = 85
        self.timer_canvas.create_oval(
            center - radius, center - radius,
            center + radius, center + radius,
            outline=THEME["bg_container"],
            width=8
        )
        
        # Arco de progresso (CUTE ACCENT)
        self.progress_arc = self.timer_canvas.create_arc(
            center - radius, center - radius,
            center + radius, center + radius,
            start=90,  # Começa no topo
            extent=-360,
            outline=COLORS["accent"],
            width=12,
            style="arc"
        )
        
        # Timer Display (dentro do círculo)
        tempo_display = f"{self.pomodoro_presets[self.pomodoro_atual][0]:02d}:00"
        self.label_timer = self.timer_canvas.create_text(
            center, center,
            text=tempo_display,
            font=("Roboto Mono", 42, "bold"),
            fill=THEME["text_main"]  # Cor do tema principal invés de lavanda fixo
        )
        
        # --- SEÇÃO DE EFEITOS ATIVOS (VISUAL NO TIMER) ---
        self.effects_frame = ctk.CTkFrame(inner, fg_color="transparent")
        self.effects_frame.pack(fill="x", pady=(5, 5))
        # O update_ui vai popular isso
        # -------------------------------------------------
        
        # INDICADOR DE STATUS (Status centralizado)
        status_frame = ctk.CTkFrame(inner, fg_color="transparent")
        status_frame.pack(pady=(0, 15))

        self.label_status_pomodoro = ctk.CTkLabel(
            status_frame,
            text="🎯 Foco",
            width=100,
            height=30,
            fg_color=THEME["primary"],
            font=("Roboto", 12, "bold"),
            corner_radius=15,
            text_color="#ffffff"
        )
        self.label_status_pomodoro.pack()

        # Presets (botões centralizados)
        preset_frame = ctk.CTkFrame(inner, fg_color="transparent")
        preset_frame.pack(pady=(0, 15))
        
        # Row de presets principais
        labels = ["15m", "30m", "50m"]
        self.preset_buttons = [] # Store buttons for visual updates
        
        for i, label in enumerate(labels):
            btn = ctk.CTkButton(
                preset_frame,
                text=label,
                width=60,
                height=30,
                fg_color=THEME["secondary"] if i != self.pomodoro_atual else THEME["primary"],
                hover_color=THEME["primary_hover"],
                text_color=THEME["text_main"],
                command=lambda idx=i: self.mudar_preset(idx),
                font=("Roboto", 11, "bold"),
                corner_radius=15,
                border_width=2 if i == self.pomodoro_atual else 0,
                border_color=THEME["primary"]
            )
            # Pack side left com padding (visual mais limpo que grid)
            btn.pack(side="left", padx=5)
            self.preset_buttons.append(btn)
        
        # Controles (Emojis com layout horizontal)
        controls_frame = ctk.CTkFrame(inner, fg_color="transparent")
        controls_frame.pack(fill="x", pady=(5, 0))
        
        # Grid para centralizar botões
        controls_frame.grid_columnconfigure(0, weight=1)
        controls_frame.grid_columnconfigure(1, weight=1)
        controls_frame.grid_columnconfigure(2, weight=1)
        
        # Start (Iniciar)
        self.btn_start = ctk.CTkButton(
            controls_frame,
            text="Iniciar ⏱️",
            font=("Roboto", 12, "bold"),
            width=80,
            height=38,
            fg_color="#51cf66",
            hover_color="#37b24d",
            command=self.iniciar_timer,
            corner_radius=19
        )
        self.btn_start.grid(row=0, column=0, padx=3)
        
        # Pause
        self.btn_pause = ctk.CTkButton(
            controls_frame,
            text="⏸️",
            font=("Segoe UI Emoji", 16),
            width=60,
            height=38,
            fg_color="#ffd43b",
            hover_color="#fab005",
            command=self.pausar_timer,
            corner_radius=19
        )
        self.btn_pause.grid(row=0, column=1, padx=3)
        
        # Stop
        self.btn_stop = ctk.CTkButton(
            controls_frame,
            text="⏹️",
            font=("Segoe UI Emoji", 16),
            width=60,
            height=38,
            fg_color="#ff6b6b",
            hover_color="#fa5252",
            command=self.resetar_timer,
            corner_radius=19
        )
        self.btn_stop.grid(row=0, column=2, padx=3)

        # HACK COGNITIVO UX: Toggle Modo Foco Total (Lei de Hick)
        self.btn_modo_foco = ctk.CTkButton(
            inner,
            text="Ativar Modo Foco 🧘‍♂️",
            font=("Roboto", 12, "bold"),
            height=38,
            fg_color=COLORS["accent"],
            text_color="#1a1124",  # Alto contraste legível
            hover_color=COLORS["accent_hover"],
            command=self.toggle_foco_total,
            corner_radius=19
        )
        self.btn_modo_foco.pack(pady=(15, 0), fill="x", padx=10)


    def toggle_foco_total(self):
        """Alterna para uma visão minimalista focada adaptada ao Grid Responsivo"""
        if getattr(self, "modo_foco_ativo", False):
            # Sair do modo Foco
            self.modo_foco_ativo = False
            self.right_column.grid_remove() # Remove a visualização espaçosa
            
            # Restaurar as outras colunas
            self.left_column.grid()
            self.center_column.grid()
            
            # Restabelece a Right Column na exata mesma posição sem TimeSpan
            self.right_column.grid(row=0, column=2, sticky="nsew", padx=(5, 0))
            
            # Restaurar botões
            self.btn_modo_foco.configure(
                text="Ativar Modo Foco 🧘‍♂️",
                fg_color=COLORS["accent"],
                text_color="#1a1124",
                hover_color=COLORS["accent_hover"]
            )
            
            if hasattr(self, "foco_spacer") and self.foco_spacer:
                self.foco_spacer.destroy()
                self.foco_spacer = None
        else:
            # Entrar no Modo Foco
            self.modo_foco_ativo = True
            
            # Esconder laterais
            self.left_column.grid_remove()
            self.center_column.grid_remove()
            
            # Reposicionar a Right Column para dominar a tela toda (span 3 colunas)
            self.right_column.grid_remove()
            self.right_column.grid(row=0, column=0, columnspan=3, sticky="nsew", padx=20, pady=20)
            
            # Adicionar um separador invisível acima para centralizar o Timer no modo paisagem
            self.foco_spacer = ctk.CTkFrame(self.right_content_frame, fg_color="transparent", height=100)
            self.foco_spacer.pack(side="top", fill="x")
            
            # Mudar Botão
            self.btn_modo_foco.configure(
                text="Sair do Modo Foco 👁️",
                fg_color=THEME["danger"],
                text_color="#ffffff",
                hover_color="#fa5252"
            )

    
    def criar_loja_grid(self):
        """Cria o grid de itens da loja"""
        from shop_manager import ShopManager
        
        # Limpar frame
        for widget in self.loja_frame.winfo_children():
            widget.destroy()
        
        catalog = ShopManager.get_catalog()
        mana_atual = obter_mana_total()
        
        # Grid com 3 itens
        for i, (item_code, item_info) in enumerate(catalog.items()):
            can_afford = mana_atual >= item_info['price']
            
            # Card do item - PREMIUM
            card = PremiumCard(
                self.loja_frame,
                border_color=COLORS["gold"] if can_afford else THEME["border"]
            )
            card.pack(fill="x", pady=8, padx=5)
            
            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(fill="both", padx=15, pady=12)
            
            # Ícone e Nome
            header = ctk.CTkFrame(inner, fg_color="transparent")
            header.pack(fill="x")
            
            ctk.CTkLabel(
                header,
                text=f"{item_info['icon']} {item_info['name']}",
                font=("Roboto", 14, "bold"),
                text_color="#fff" if can_afford else "#666"
            ).pack(side="left")
            
            ctk.CTkLabel(
                header,
                text=f"💎 {item_info['price']}",
                font=("Roboto", 13, "bold"),
                text_color=COLORS["mana"] if can_afford else THEME["text_sec"]
            ).pack(side="right")
            
            # Descrição
            ctk.CTkLabel(
                inner,
                text=item_info['description'],
                font=("Roboto", 10),
                text_color=THEME["text_sec"] if can_afford else THEME["text_sec"],
                wraplength=300
            ).pack(fill="x", pady=(5, 8))
            
            # Efeito
            ctk.CTkLabel(
                inner,
                text=f"⚡ {item_info['effect']}",
                font=("Roboto", 9),
                text_color="#888" if can_afford else "#444"
            ).pack(fill="x", pady=(0, 10))
            
            # Botão Comprar
            btn = ctk.CTkButton(
                inner,
                text="Comprar" if can_afford else "Mana Insuficiente",
                font=("Roboto", 11, "bold"),
                fg_color=COLORS["accent"] if can_afford else THEME["bg_main"],
                hover_color=COLORS["accent_hover"] if can_afford else THEME["bg_main"],
                state="normal" if can_afford else "disabled",
                command=lambda code=item_code: self.comprar_item(code)
            )
            btn.pack(fill="x")
    
    def comprar_item(self, item_code: str):
        """Compra um item da loja"""
        from shop_manager import ShopManager
        
        if ShopManager.buy_item(item_code):
            # Atualizar UI
            self.criar_loja_grid()
            self.atualizar_inventario_hud()  # Atualizar HUD compacto
            self.atualizar_ui()
        else:
            print("Falha ao comprar item")
    
    def usar_item(self, item_code: str):
        """Usa um item do inventário"""
        from shop_manager import ShopManager
        # remove_item já importado no topo
        
        item_info = ShopManager.get_item_info(item_code)
        if not item_info:
            return
        
        # Lógica específica por item
        if item_code == 'hourglass':
            # Ampulheta: +5min no descanso
            if not self.pomodoro_em_descanso:
                _notificar("⏳ Ampulheta", "Só pode ser usada durante o descanso!")
                print("⏳ Ampulheta só pode ser usada durante o descanso!")
                return
            
            # Adicionar 5 minutos
            self.pomodoro_tempo_restante += 300
            remove_item('hourglass', 1)
            print("⏳ +5 minutos adicionados ao descanso!")
            get_audio_manager().play_sfx('task_complete')
            _notificar("⏳ Ampulheta ativada!", "+5 minutos de descanso.")
            
        elif item_code == 'potion_focus':
            # Poção de Foco: 15min de escudo
            if remove_item('potion_focus', 1):
                 add_active_effect('potion_focus', 15, 'active')
                 get_audio_manager().play_sfx('potion_use')
                 print("🧪 Poção de Foco ativada! (15min)")
                 _notificar("🧪 Poção de Foco", "Imunidade a distrações por 15 minutos!")
            
        elif item_code == 'potion_xp':
            # Poção de XP: dobrar XP (Pendente -> Ativa no timer)
            if remove_item('potion_xp', 1):
                # Cria com status 'pending' e sem duração definida ainda
                add_active_effect('potion_xp', duration_minutes=None, status='pending')
                get_audio_manager().play_sfx('potion_use')
                print("⚗️ Poção de XP preparada! Inicie um Pomodoro para ativar.")
                _notificar("⚗️ Poção de XP", "Preparada! Inicie o timer para ativar o dobro de XP.")

        # Atualizar UI Geral
        self.atualizar_inventario_hud()
        self.atualizar_ui()
    
    def atualizar_inventario_hud(self):
        """Atualiza inventário no HUD (versão compacta)"""
        from shop_manager import ShopManager
        
        # Limpar
        for widget in self.inventario_hud_frame.winfo_children():
            widget.destroy()
        
        inv = get_inventory()
        has_items = any(qty > 0 for qty in inv.values())
        
        if not has_items:
            ctk.CTkLabel(
                self.inventario_hud_frame,
                text="Vazio - Compre itens na loja!",
                text_color="#666",
                font=("Roboto", 9)
            ).pack(pady=10)
            return
        
        # Grid horizontal compacto
        items_container = ctk.CTkFrame(self.inventario_hud_frame, fg_color="transparent")
        items_container.pack(fill="x", padx=8, pady=8)
        
        for item_code, qty in inv.items():
            if qty > 0:
                item_info = ShopManager.get_item_info(item_code)
                if item_info:
                    # Botão MUITO compacto
                    btn = ctk.CTkButton(
                        items_container,
                        text=f"{item_info['icon']}{qty}",  # Sem espaço e sem 'x'
                        font=("Roboto", 10, "bold"),
                        width=50,  # Reduzido de 70 para 50
                        height=24,  # Mantido pequeno
                        fg_color="#3c096c",
                        hover_color="#7209b7",
                        command=lambda code=item_code: self.usar_item(code)
                    )
                    btn.pack(side="left", padx=2)  # Menos padding
    
    def atualizar_radar_chart(self):
        """Atualiza gráfico de radar dos stats RPG"""
        try:
            # Limpar gráfico anterior
            for widget in self.radar_frame.winfo_children():
                widget.destroy()
            
            # Pegar stats do banco
            stats = get_all_stats()
            
            # Criar gráfico radar
            # Restaurado para 170x170 (Premium)
            canvas = create_radar_chart(self.radar_frame, stats, size=(170, 170))
            canvas.get_tk_widget().pack()
            
            # Atualizar classe/título
            titulo, descricao = get_character_class()
            self.label_classe.configure(text=f"🏆 {titulo}")
            self.label_classe_desc.configure(text=descricao)
            
        except Exception as e:
            print(f"[ERRO] atualizar_radar_chart: {e}")
            # Fallback: mostrar mensagem
            ctk.CTkLabel(
                self.radar_frame,
                text="Stats indisponíveis",
                text_color="#666"
            ).pack(pady=20)

    def atualizar_desafios_ui(self):
        """Atualiza a seção de desafios diários"""
        try:
            # Verificar progresso dos desafios
            ChallengesManager.check_progress_all()
            
            # Limpar frame
            for widget in self.challenges_frame.winfo_children():
                widget.destroy()
            
            # Buscar desafios do dia
            challenges = ChallengesManager.get_today_challenges()
            
            if not challenges:
                ctk.CTkLabel(
                    self.challenges_frame,
                    text="Nenhum desafio disponível",
                    font=("Roboto", 9),
                    text_color="#666"
                ).pack(anchor="w")
                return
            
            for challenge in challenges:
                is_completed = challenge.get('is_completed', False)
                claimed = challenge.get('claimed', False)
                
                # Row do desafio
                row = ctk.CTkFrame(self.challenges_frame, fg_color="transparent", height=28)
                row.pack(fill="x", pady=2)
                
                # Ícone de status
                if claimed:
                    status_text = "🎁"  # Recompensa coletada
                    status_color = "#51cf66"
                elif is_completed:
                    status_text = "✅"  # Completado, aguardando coleta
                    status_color = "#ffd60a"
                else:
                    status_text = "⬜"  # Pendente
                    status_color = "#666"
                
                ctk.CTkLabel(
                    row, text=status_text,
                    font=("Roboto", 10),
                    text_color=status_color
                ).pack(side="left")
                
                # Nome do desafio (compacto)
                name_color = "#aaa" if not is_completed else ("#51cf66" if claimed else "#ffd60a")
                nome_label = ctk.CTkLabel(
                    row, text=challenge.get('name', '?'),
                    font=("Roboto", 9),
                    text_color=name_color,
                    wraplength=140
                )
                nome_label.pack(side="left", padx=(5, 0))
                
                # Tooltip com detalhes
                desc = challenge.get('description', '')
                try:
                    CTkToolTip(nome_label, f"{desc}\n\n🏆 XP: +{challenge.get('xp_reward')}\n💎 Mana: +{challenge.get('mana_reward')}")
                except Exception:
                    pass
                
                # Botão coletar (se completado e não coletado)
                if is_completed and not claimed:
                    def collect(code=challenge['code']):
                        xp, mana = ChallengesManager.claim_reward(code)
                        if xp > 0 or mana > 0:
                            _notificar("🎁 Recompensa!", f"+{xp} XP, +{mana} Mana")
                            get_audio_manager().play_sfx('achievement')
                            self.atualizar_desafios_ui()
                            self.atualizar_ui()
                    
                    ctk.CTkButton(
                        row, text="🎁",
                        width=25, height=20,
                        fg_color="#ffd60a",
                        hover_color="#fab005",
                        text_color="#000",
                        font=("Roboto", 10),
                        command=collect
                    ).pack(side="right")
                
                # Recompensa (pequena)
                reward_text = f"+{challenge.get('xp_reward', 0)}XP"
                ctk.CTkLabel(
                    row, text=reward_text,
                    font=("Roboto", 8),
                    text_color="#888"
                ).pack(side="right", padx=5)
        
        except Exception as e:
            logger.error(f"Erro ao atualizar desafios: {e}")

    def abrir_relatorios(self):
        """Abre a janela de relatórios de produtividade"""
        try:
            ReportsWindow(self)
            logger.info("Janela de relatórios aberta")
        except Exception as e:
            logger.error(f"Erro ao abrir relatórios: {e}")
            _notificar("❌ Erro", "Não foi possível abrir os relatórios")

    def atualizar_lista_historico(self):
        """Atualiza a lista de histórico na UI"""
        # Limpar
        for widget in self.tarefas_scroll_frame.winfo_children():
            widget.destroy()
            
        historico = carregar_historico(limite=30)
        
        if not historico:
            ctk.CTkLabel(
                self.tarefas_scroll_frame,
                text="Nenhuma tarefa concluída ainda.",
                text_color="#666"
            ).pack(pady=20)
            return
            
        for item in historico:
            self.criar_card_historico(self.tarefas_scroll_frame, item)

    def criar_card_historico(self, parent, item):
        """Cria card de histórico (id, titulo, xp, data, dif, bonus)"""
        # item: (id, titulo, xp_ganho, data_conclusao, nivel_dificuldade, bonus_temporal, tarefa_id)
        # Atenção: tarefa_id só existe se database.py foi atualizado corretamente.
        # Fallback seguro:
        if len(item) >= 7:
             _, titulo, xp, data, _, bonus, db_tarefa_id = item
        else:
             _, titulo, xp, data, _, bonus = item
             db_tarefa_id = None
        
        card = ctk.CTkFrame(
            parent,
            fg_color=THEME["bg_main"],
            corner_radius=20,
            border_width=1,
            border_color=THEME["border"]
        )
        card.pack(fill="x", pady=4)
        
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", padx=10, pady=8)
        
        # Linha 1: Título e XP
        l1 = ctk.CTkFrame(inner, fg_color="transparent")
        l1.pack(fill="x")
        
        ctk.CTkLabel(
            l1, text=titulo,
            font=("Roboto", 11, "bold"),
            text_color=THEME["text_sec"]
        ).pack(side="left")
        
        ctk.CTkLabel(
            l1, text=f"+{xp} XP",
            font=("Roboto", 11, "bold"),
            text_color=THEME["success"]
        ).pack(side="right")
        
        # Linha 2: Data e Bônus
        l2 = ctk.CTkFrame(inner, fg_color="transparent")
        l2.pack(fill="x", pady=(2, 0))
        
        ctk.CTkLabel(
            l2, text=f"📅 {data}",
            font=("Roboto", 9),
            text_color="#666"
        ).pack(side="left")
        
        if bonus and bonus > 0:
            ctk.CTkLabel(
                l2, text=f"⚡ Bônus: {bonus}",
                font=("Roboto", 9),
                text_color="#ffc107"
            ).pack(side="right")
            
        # Botão Restaurar (🔄)
        if db_tarefa_id:
            ctk.CTkButton(
                l2, text="🔄",
                width=30, height=20,
                font=("Segoe UI Emoji", 12),
                fg_color="#333",
                hover_color="#555",
                command=lambda: self.restaurar_tarefa(db_tarefa_id)
            ).pack(side="right", padx=(0, 5))
    
    def atualizar_lista_tarefas(self):
        """Atualiza exibição de tarefas"""
        # Limpar
        for widget in self.tarefas_scroll_frame.winfo_children():
            widget.destroy()
        
        if not self.tarefas:
            ctk.CTkLabel(
                self.tarefas_scroll_frame,
                text="Nenhuma tarefa criada!",
                text_color="#888"
            ).pack(pady=40)
            return
        
        # Adicionar cada tarefa
        for tarefa in self.tarefas:
            self.criar_card_tarefa(self.tarefas_scroll_frame, tarefa)
    
    def criar_card_tarefa(self, parent, tarefa):
        """Cria card de uma tarefa"""
        # Desempacotar com suporte a atributo (9 itens) ou sem (8 itens - compat backward)
        if len(tarefa) >= 9:
             task_id, titulo, desc, nivel, xp, data, prior, concluida, attr_tag = tarefa[:9]
        else:
             task_id, titulo, desc, nivel, xp, data, prior, concluida = tarefa[:8]
             attr_tag = "DEX" # Default
        
        # Cores por prioridade (Urgente = Neon Red)
        prior_cores = {1: "#4a90e2", 2: "#f5a623", 3: "#d0021b", 4: "#ff2a6d"}
        cor_prior = prior_cores.get(prior, "#4a90e2")
        
        prior_labels = {1: "Baixa", 2: "Média", 3: "Alta", 4: "URGENTE"}
        label_prior = prior_labels.get(prior, "")
        
        nivel_labels = {1: "⭐", 2: "⭐⭐", 3: "⭐⭐⭐", 4: "⭐⭐⭐⭐", 5: "⭐⭐⭐⭐⭐"}
        nivel_icons = nivel_labels.get(nivel, "⭐")
        
        # Frame - PREMIUM MISSION CARD
        card = PremiumCard(
            parent,
            border_color=cor_prior,
            border_width=2
        )
        card.pack(fill="x", pady=8)
        
        # Conteúdo
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=12, pady=10)
        
        # Linha 1: Título + Nível + XP + Botões Ação
        linha1 = ctk.CTkFrame(inner, fg_color="transparent")
        linha1.pack(fill="x", pady=(0, 5))
        
        # Botão Concluir (✅) - No lugar do checkbox
        ctk.CTkButton(
            linha1, text="✅", # Emoji check
            width=40, height=35,
            font=("Segoe UI Emoji", 14),
            fg_color=THEME["success"], # Verde
            hover_color=COLORS["success"],
            corner_radius=10,
            command=lambda: self.concluir_tarefa(task_id, titulo, xp, nivel)
        ).pack(side="left", padx=(0, 10))
        
        # Título
        ctk.CTkLabel(
            linha1, text=titulo,
            font=("Roboto", 13, "bold"), # Levemente maior
            text_color=THEME["text_main"]
        ).pack(side="left")
        
        # Nível (stars)
        ctk.CTkLabel(
            linha1, text=nivel_icons,
            font=("Roboto", 9),
            text_color=COLORS["gold"]
        ).pack(side="left", padx=10)
        
        # XP na direita
        ctk.CTkLabel(
            linha1, text=f"{xp}XP",
            font=("Roboto", 11, "bold"),
            text_color=THEME["success"]
        ).pack(side="right", padx=(20, 0))
        
        # Attribute Badge (Novo)
        colors = {
            "INT": "#4DABF7", "DEX": "#51CF66", "STR": "#FF6B6B",
            "CHA": "#FFD43B", "CRI": "#CC5DE8"
        }
        attr_color = colors.get(attr_tag, "#888")
        
        ctk.CTkLabel(
            linha1, text=attr_tag,
            font=("Roboto", 9, "bold"),
            text_color=attr_color,
            fg_color=THEME["bg_main"],
            corner_radius=4,
            padx=4 
        ).pack(side="right", padx=(5, 5))
        
        # Linha 2: Prioridade + Data + Nível
        linha2 = ctk.CTkFrame(inner, fg_color="transparent")
        linha2.pack(fill="x", pady=(5, 8))
        
        # Badge Prioridade
        ctk.CTkLabel(
            linha2, text=label_prior,
            font=("Roboto", 9, "bold"),
            text_color="white",
            fg_color=cor_prior,
            padx=8, pady=3,
            corner_radius=3
        ).pack(side="left", padx=(0, 10))
        
        # Data
        if data:
            ctk.CTkLabel(
                linha2, text=f"📅 {data}",
                font=("Roboto", 9),
                text_color="#888"
            ).pack(side="left", padx=(0, 10))
        
        # Dificuldade
        ctk.CTkLabel(
            linha2, text=f"Nível {nivel}",
            font=("Roboto", 9),
            text_color="#aaa"
        ).pack(side="left")
        
        # Linha 3: Descrição (se houver)
        if desc and desc.strip():
            linha_desc = ctk.CTkFrame(inner, fg_color="transparent")
            linha_desc.pack(fill="x", pady=(5, 8))
            
            ctk.CTkLabel(
                linha_desc, text=f"📝 {desc[:60]}...",
                font=("Roboto", 9),
                text_color="#999",
                wraplength=400
            ).pack(anchor="w")
        
        # Linha 4: Botões de Edição Compactos (Direita alinhados na linha 1 na vdd ficaria melhor, mas ok na 4)
        # Vamos manter na 4 mas usar emojis
        linha4 = ctk.CTkFrame(inner, fg_color="transparent")
        linha4.pack(fill="x", pady=(8, 0))

        # Espaçador
        ctk.CTkLabel(linha4, text="", width=1).pack(side="left", expand=True)
        
        ctk.CTkButton(
            linha4, text="✏️", 
            width=40, height=28,
            font=("Segoe UI Emoji", 12),
            fg_color="#333",
            hover_color="#444",
            command=lambda: self.dialog_editar_tarefa(task_id)
        ).pack(side="right", padx=(5, 0))
        
        ctk.CTkButton(
            linha4, text="🗑️", 
            width=40, height=28,
            font=("Segoe UI Emoji", 12),
            fg_color="#442222", # Vermelho bem escuro
            hover_color="#ff6b6b",
            command=lambda: self.deletar_tarefa_confirm(task_id)
        ).pack(side="right", padx=(5, 0))
    
    def dialog_nova_tarefa(self):
        """Dialog para criar nova tarefa"""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Nova Tarefa")
        dialog.geometry("550x700")
        dialog.configure(fg_color="#1a1f3a")
        dialog.grab_set()
        
        # Título
        ctk.CTkLabel(
            dialog, text="Criar Nova Tarefa",
            font=("Roboto", 16, "bold"),
            text_color="#b19cd9"
        ).pack(padx=20, pady=(20, 15))
        
        # Frame com scroll
        scroll_container = ctk.CTkScrollableFrame(dialog, fg_color="transparent")
        scroll_container.pack(fill="both", expand=True, padx=20, pady=10)
        
        inner = ctk.CTkFrame(scroll_container, fg_color="transparent")
        inner.pack(fill="both", expand=True)
        
        # Nome
        ctk.CTkLabel(inner, text="Nome da Tarefa:", text_color="#aaa", font=("Roboto", 11)).pack(anchor="w", pady=(0, 5))
        entry_nome = ctk.CTkEntry(inner, placeholder_text="Ex: Estudar Python", height=35, font=("Roboto", 11))
        entry_nome.pack(fill="x", pady=(0, 15))
        
        # Descrição
        ctk.CTkLabel(inner, text="Descrição (opcional):", text_color="#aaa", font=("Roboto", 11)).pack(anchor="w", pady=(0, 5))
        entry_desc = ctk.CTkTextbox(inner, height=80, font=("Roboto", 10))
        entry_desc.pack(fill="x", pady=(0, 15))
        
        # Nível (Dificuldade)
        ctk.CTkLabel(inner, text="Nível de Dificuldade:", text_color="#aaa", font=("Roboto", 11)).pack(anchor="w", pady=(0, 5))
        combo_nivel = ctk.CTkComboBox(
            inner, values=["1 ⭐", "2 ⭐⭐", "3 ⭐⭐⭐", "4 ⭐⭐⭐⭐", "5 ⭐⭐⭐⭐⭐"], 
            state="readonly", height=35, font=("Roboto", 10)
        )
        combo_nivel.set("1 ⭐")
        combo_nivel.pack(fill="x", pady=(0, 15))
        
        # NOVO: Tipo de Treino (Atributo RPG)
        ctk.CTkLabel(inner, text="Tipo de Treino:", text_color="#aaa", font=("Roboto", 11)).pack(anchor="w", pady=(0, 5))
        
        attribute_var = ctk.StringVar(value="DEX - Projeto/Trabalho")
        attribute_options = [
            "INT - Estudo/Leitura",
            "DEX - Projeto/Trabalho",  
            "CRI - Arte/Criativo",
            "STR - Saúde/Físico",
            "CHA - Social/Reunião"
        ]
        
        combo_attribute = ctk.CTkOptionMenu(
            inner, 
            variable=attribute_var,
            values=attribute_options,
            height=35, 
            font=("Roboto", 10)
        )
        combo_attribute.pack(fill="x", pady=(0, 15))
        
        # NOVO: Recorrência
        ctk.CTkLabel(inner, text="Recorrência (dias da semana):", text_color="#aaa", font=("Roboto", 11)).pack(anchor="w", pady=(0, 5))
        recurr_frame = ctk.CTkFrame(inner, fg_color="transparent")
        recurr_frame.pack(fill="x", pady=(0, 15))
        
        dias_semana = ["S", "T", "Q", "Q", "S", "S", "D"]
        chk_days = []
        for i, d in enumerate(dias_semana):
            var = ctk.StringVar(value="")
            chk = ctk.CTkCheckBox(recurr_frame, text=d, variable=var, onvalue=str(i), offvalue="", width=30, font=("Roboto", 10))
            chk.pack(side="left", padx=(0, 3) if i < 6 else 0)
            chk_days.append(var)
        
        # Prioridade
        # Prioridade
        ctk.CTkLabel(inner, text="Prioridade:", text_color="#aaa", font=("Roboto", 11)).pack(anchor="w", pady=(0, 5))
        prior_labels = ["Baixa", "Média", "Alta", "Urgente"]
        combo_prior = ctk.CTkComboBox(
            inner, values=prior_labels, state="readonly", height=35, font=("Roboto", 10)
        )
        combo_prior.set("Média")
        combo_prior.pack(fill="x", pady=(0, 15))

        # Data
        ctk.CTkLabel(inner, text="Data de Entrega (YYYY-MM-DD):", text_color="#aaa", font=("Roboto", 11)).pack(anchor="w", pady=(0, 5))
        
        # Botões de Atalho de Data
        date_shortcuts = ctk.CTkFrame(inner, fg_color="transparent")
        date_shortcuts.pack(fill="x", pady=(0, 5))
        
        def set_date(days_offset):
            from datetime import timedelta
            target_date = datetime.now() + timedelta(days=days_offset)
            entry_data.delete(0, "end")
            entry_data.insert(0, target_date.strftime("%Y-%m-%d"))

        ctk.CTkButton(date_shortcuts, text="Hoje", width=60, height=20, font=("Roboto", 9), fg_color="#333", command=lambda: set_date(0)).pack(side="left", padx=(0, 5))
        ctk.CTkButton(date_shortcuts, text="Amanhã", width=60, height=20, font=("Roboto", 9), fg_color="#333", command=lambda: set_date(1)).pack(side="left", padx=(0, 5))
        ctk.CTkButton(date_shortcuts, text="Em 3 dias", width=70, height=20, font=("Roboto", 9), fg_color="#333", command=lambda: set_date(3)).pack(side="left")

        entry_data = ctk.CTkEntry(inner, placeholder_text="2026-01-25", height=35, font=("Roboto", 11))
        entry_data.pack(fill="x", pady=(0, 5))
        # Hora/Minuto removidos (não usados e confusos)
        # hora_frame = ctk.CTkFrame(inner, fg_color="transparent")
        
        
        # Botões GRANDE E VISÍVEL
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=20)
        
        def salvar():
            nome_cru = entry_nome.get().strip()
            
            # Validação e higienização do título
            is_valid, error_msg, nome = validate_task_title(nome_cru)
            if not is_valid:
                _notificar("❌ Erro", error_msg)
                logger.warning(f"Validação de título falhou: {error_msg}")
                return
            
            try:
                desc_cru = entry_desc.get("1.0", "end-1c").strip()
                
                # Validação e higienização da descrição
                is_valid_desc, desc_error, desc = validate_task_description(desc_cru)
                if not is_valid_desc:
                    _notificar("❌ Erro", desc_error)
                    logger.warning(f"Validação de descrição falhou: {desc_error}")
                    return
                
                nivel_text = combo_nivel.get().split()[0]
                nivel = int(nivel_text)
                
                # Extrair código do atributo (primeiro 3 chars = código)
                attr_text = attribute_var.get()
                attribute_tag = attr_text.split(" - ")[0]  # Pega só o código (INT, DEX, etc.)
                
                # Obter recorrência
                dias_selecionados = [v.get() for v in chk_days if v.get()]
                is_recurring = len(dias_selecionados) > 0
                recurrence_pattern = ",".join(dias_selecionados) if is_recurring else None
                
                prior = prior_labels.index(combo_prior.get()) + 1
                data = entry_data.get().strip() or None
                # hora/min removidos
                # Garante que XP é inteiro
                xp = 10 * nivel if isinstance(nivel, int) else 10
                # Garante que data é string no formato YYYY-MM-DD
                if data:
                    try:
                        datetime.strptime(data, "%Y-%m-%d")
                    except Exception:
                        data = None
                if adicionar_tarefa(nome, desc, nivel, xp, data, prior, attribute_tag, is_recurring, recurrence_pattern):
                    logger.info(f"Tarefa criada: {nome} (nível {nivel})")
                    self.carregar_tarefas()
                    self.atualizar_lista_tarefas()
                    dialog.destroy()
                    try:
                        winsound.Beep(600, 150)
                    except Exception:
                        pass
            except Exception as e:
                logger.error(f"Erro ao criar tarefa: {e}", exc_info=True)
        
        ctk.CTkButton(
            btn_frame, text="✅ CRIAR TAREFA",
            fg_color="#51cf66",
            hover_color="#45a049",
            font=("Roboto", 13, "bold"),
            height=40,
            command=salvar
        ).pack(fill="x", pady=5)
        
        ctk.CTkButton(
            btn_frame, text="❌ Cancelar",
            fg_color="#ff6b6b",
            hover_color="#e55555",
            font=("Roboto", 13, "bold"),
            height=40,
            command=dialog.destroy
        ).pack(fill="x", pady=5)
    
    def dialog_editar_tarefa(self, task_id):
        """Dialog para editar tarefa"""
        tarefa = next((t for t in self.tarefas if t[0] == task_id), None)
        if not tarefa:
            return
        
        # Desempacotar seguro
        if len(tarefa) >= 9:
             task_id, titulo, desc, nivel, xp, data, prior, concluida, attr_tag = tarefa[:9]
        else:
             task_id, titulo, desc, nivel, xp, data, prior, concluida = tarefa[:8]
             attr_tag = "DEX"
        
        dialog = ctk.CTkToplevel(self)
        dialog.title("Editar Tarefa")
        dialog.geometry("550x700")
        dialog.configure(fg_color="#1a1f3a")
        dialog.grab_set()
        
        # Título
        ctk.CTkLabel(
            dialog, text="Editar Tarefa",
            font=("Roboto", 16, "bold"),
            text_color="#b19cd9"
        ).pack(padx=20, pady=(20, 15))
        
        scroll_container = ctk.CTkScrollableFrame(dialog, fg_color="transparent")
        scroll_container.pack(fill="both", expand=True, padx=20, pady=10)
        
        inner = ctk.CTkFrame(scroll_container, fg_color="transparent")
        inner.pack(fill="both", expand=True)
        
        ctk.CTkLabel(inner, text="Nome da Tarefa:", text_color="#aaa", font=("Roboto", 11)).pack(anchor="w", pady=(0, 5))
        entry_nome = ctk.CTkEntry(inner, height=35, font=("Roboto", 11))
        entry_nome.insert(0, titulo)
        entry_nome.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(inner, text="Descrição (opcional):", text_color="#aaa", font=("Roboto", 11)).pack(anchor="w", pady=(0, 5))
        entry_desc = ctk.CTkTextbox(inner, height=80, font=("Roboto", 10))
        if desc:
            entry_desc.insert("1.0", desc)
        entry_desc.pack(fill="x", pady=(0, 15))
        
        # Nível (Dificuldade)
        ctk.CTkLabel(inner, text="Nível de Dificuldade:", text_color="#aaa", font=("Roboto", 11)).pack(anchor="w", pady=(0, 5))
        combo_nivel = ctk.CTkComboBox(
            inner, values=["1 ⭐", "2 ⭐⭐", "3 ⭐⭐⭐", "4 ⭐⭐⭐⭐", "5 ⭐⭐⭐⭐⭐"], 
            state="readonly", height=35, font=("Roboto", 10)
        )
        combo_nivel.set(f"{nivel} " + "⭐" * nivel)
        combo_nivel.pack(fill="x", pady=(0, 15))
        
        # Prioridade
        ctk.CTkLabel(inner, text="Prioridade:", text_color="#aaa", font=("Roboto", 11)).pack(anchor="w", pady=(0, 5))
        prior_labels = ["Baixa", "Média", "Alta", "Urgente"]
        combo_prior = ctk.CTkComboBox(
            inner, values=prior_labels, state="readonly", height=35, font=("Roboto", 10)
        )
        combo_prior.set(prior_labels[prior - 1])
        combo_prior.pack(fill="x", pady=(0, 15))

        # Atributo (Novo)
        ctk.CTkLabel(inner, text="Tipo de Treino:", text_color="#aaa", font=("Roboto", 11)).pack(anchor="w", pady=(0, 5))
        
        attribute_var = ctk.StringVar(value=f"{attr_tag} - (Atual)")
        attribute_options = [
            "INT - Estudo/Leitura",
            "DEX - Projeto/Trabalho",  
            "CRI - Arte/Criativo",
            "STR - Saúde/Físico",
            "CHA - Social/Reunião"
        ]
        # Tentar setar o valor correto no dropdown
        for opt in attribute_options:
            if opt.startswith(attr_tag):
                attribute_var.set(opt)
                break
                
        combo_attribute = ctk.CTkOptionMenu(
            inner, 
            variable=attribute_var,
            values=attribute_options,
            height=35, 
            font=("Roboto", 10)
        )
        combo_attribute.pack(fill="x", pady=(0, 15))
        
        # Data
        ctk.CTkLabel(inner, text="Data de Entrega (YYYY-MM-DD):", text_color="#aaa", font=("Roboto", 11)).pack(anchor="w", pady=(0, 5))
        
        # Botões de Atalho de Data (Edição)
        date_shortcuts = ctk.CTkFrame(inner, fg_color="transparent")
        date_shortcuts.pack(fill="x", pady=(0, 5))
        
        def set_date_edit(days_offset):
            from datetime import timedelta
            target_date = datetime.now() + timedelta(days=days_offset)
            entry_data.delete(0, "end")
            entry_data.insert(0, target_date.strftime("%Y-%m-%d"))

        ctk.CTkButton(date_shortcuts, text="Hoje", width=60, height=20, font=("Roboto", 9), fg_color="#333", command=lambda: set_date_edit(0)).pack(side="left", padx=(0, 5))
        ctk.CTkButton(date_shortcuts, text="Amanhã", width=60, height=20, font=("Roboto", 9), fg_color="#333", command=lambda: set_date_edit(1)).pack(side="left", padx=(0, 5))
        
        entry_data = ctk.CTkEntry(inner, height=35, font=("Roboto", 11))
        if data:
            entry_data.insert(0, data)
        entry_data.pack(fill="x", pady=(0, 20))
        
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=20)
        
        def salvar():
            nome_cru = entry_nome.get().strip()
            
            is_valid, error_msg, nome = validate_task_title(nome_cru)
            if not is_valid:
                _notificar("❌ Erro", error_msg)
                logger.warning(f"Validação de título falhou (edits): {error_msg}")
                return
            
            try:
                desc_cru = entry_desc.get("1.0", "end-1c").strip()
                
                is_valid_desc, desc_error, desc = validate_task_description(desc_cru)
                if not is_valid_desc:
                    _notificar("❌ Erro", desc_error)
                    logger.warning(f"Validação de descrição falhou (edits): {desc_error}")
                    return
                
                nivel_str = combo_nivel.get().split()[0]
                novo_nivel = int(nivel_str)
                nova_prior = prior_labels.index(combo_prior.get()) + 1
                nova_data = entry_data.get().strip() or None
                
                # Atributo
                attr_text = attribute_var.get()
                nova_attr = attr_text.split(" - ")[0]

                if editar_tarefa(task_id, titulo=nome, descricao=desc, nivel=novo_nivel, prioridade=nova_prior, data_vencimento=nova_data, attribute_tag=nova_attr):
                    self.carregar_tarefas()
                    self.atualizar_lista_tarefas()
                    dialog.destroy()
            except Exception as e:
                logger.error(f"Erro ao editar (safeguard): {e}")
                pass
        
        ctk.CTkButton(
            btn_frame, text="✅ SALVAR TAREFA",
            fg_color="#51cf66",
            hover_color="#45a049",
            font=("Roboto", 13, "bold"),
            height=40,
            command=salvar
        ).pack(fill="x", pady=5)
        
        ctk.CTkButton(
            btn_frame, text="❌ Cancelar",
            fg_color="#ff6b6b",
            hover_color="#e55555",
            font=("Roboto", 13, "bold"),
            height=40,
            command=dialog.destroy
        ).pack(fill="x", pady=5)
    
    def concluir_tarefa(self, task_id, titulo, xp, nivel):
        """Marca tarefa como concluída, calcula bônus de XP por antecedência e ganha XP"""
        from datetime import datetime
        # Obter data prevista da tarefa
        data_prevista = None
        for t in self.tarefas:
            if t[0] == task_id:
                data_prevista = t[5]  # data_vencimento
                break
        data_real = datetime.now()
        bonus = 0
        if data_prevista:
            try:
                dt_prevista = datetime.strptime(data_prevista, "%Y-%m-%d")
                # Só dá bônus se concluir ANTES da data prevista
                if data_real < dt_prevista:
                    diff_horas = (dt_prevista - data_real).total_seconds() // 3600
                    bonus = int(diff_horas) * 10
            except Exception:
                pass
        xp_total = xp + bonus
        
        # Obter prioridade para conquista "Caçador de Metas"
        prioridade = 1
        for t in self.tarefas:
            if t[0] == task_id:
                prioridade = t[6]
                break

        concluir_tarefa(task_id)
        adicionar_xp(xp_total)
        adicionar_ao_historico(task_id, titulo, xp_total, nivel, bonus)
        
        # Atualizar atributo
        attr_tag = "DEX"  # Valor padrão
        for t in self.tarefas:
            if t[0] == task_id:
                # O atributo está na posição 8 (índice 8) da tupla
                if len(t) > 8:
                    attr_tag = t[8]
                break
        # Adiciona pontos aos stats e atualiza 
        pontos_ganhos = nivel  # 1 ponto por cada estrela da tarefa
        if adicionar_stat_points(attr_tag, pontos_ganhos):
            print(f"⚡ +{pontos_ganhos} pontos em {attr_tag}!")
            self.atualizar_radar_chart()
        
        # SEPARAÇÃO MANA/XP: Dar MANA (moeda) baseado no nível de dificuldade
        mana_por_nivel = {1: 5, 2: 15, 3: 40, 4: 85, 5: 150}
        mana_ganho = mana_por_nivel.get(nivel, 5)
        adicionar_mana(mana_ganho)
        print(f"💰 +{mana_ganho} Mana pela tarefa! (Nível {nivel})")
        
        # Som e animação de conclusão
        self.tocar_som_conclusao()
        get_audio_manager().play_sfx('task_complete')
        self.animar_xp_ganho(xp_total)
        if bonus > 0:
            self.mostrar_bonus_xp(bonus)
            
        # --- CHECAR CONQUISTAS DE TAREFAS ---
        try:
            stats = get_task_stats()
            
            # 1. FIRST_STEPS (Primeira tarefa)
            if stats['total'] >= 1:
                if unlock_achievement("FIRST_STEPS", "Primeiros Passos", "Completar sua primeira tarefa."):
                    print("🏆 CONQUISTA: Primeiros Passos!")
                    get_audio_manager().play_sfx('achievement')

            # 2. HANDS_ON (10 tarefas)
            if stats['total'] >= 10:
                if unlock_achievement("HANDS_ON", "Mão na Massa", "Completar 10 tarefas."):
                    print("🏆 CONQUISTA: Mão na Massa!")
                    get_audio_manager().play_sfx('achievement')
            
            # 3. MULTITASKER (5 tarefas hoje)
            if stats['today'] >= 5:
                if unlock_achievement("MULTITASKER", "Multitarefa", "Completar 5 tarefas em um dia."):
                    print("🏆 CONQUISTA: Multitarefa!")
                    get_audio_manager().play_sfx('achievement')
            
            # 4. GOAL_HUNTER (Tarefa Urgente - Prioridade 4)
            if prioridade == 4:
                if unlock_achievement("GOAL_HUNTER", "Caçador de Metas", "Concluir uma tarefa urgente."):
                    print("🏆 CONQUISTA: Caçador de Metas!")
                    get_audio_manager().play_sfx('achievement')
        except Exception as e:
            print(f"Erro ao checar conquistas de tarefa: {e}")
        # -----------------------------------------------

        # Atualizar listas por último
        self.carregar_tarefas()
        self.atualizar_lista_tarefas()

    def restaurar_tarefa(self, tarefa_id):
        """Restaura tarefa concluída do histórico"""
        if restaurar_tarefa(tarefa_id):
            print(f"Tarefa {tarefa_id} restaurada!")
            self.carregar_tarefas()
            # Atualizar ambas as listas pois uma tarefa saiu de histórico -> ativa
            self.atualizar_lista_tarefas() 
            self.atualizar_lista_historico()
            try:
                winsound.Beep(700, 100)
            except Exception:
                pass

    def mostrar_bonus_xp(self, bonus):
        try:
            popup = ctk.CTkToplevel(self)
            popup.geometry("250x80")
            popup.attributes('-alpha', 0.95)
            popup.resizable(False, False)
            popup.update()
            x = self.winfo_x() + self.winfo_width() // 2 - 125
            y = self.winfo_y() + self.winfo_height() // 2 - 40
            popup.geometry(f"+{x}+{y}")
            popup.configure(fg_color="#1a1f3a")
            lbl = ctk.CTkLabel(
                popup,
                text=f"Bônus: +{bonus} XP por antecedência!",
                font=("Roboto", 18, "bold"),
                text_color="#51cf66"
            )
            lbl.pack(expand=True)
            popup.after(2000, popup.destroy)
        except Exception:
            pass
    
    def tocar_som_conclusao(self):
        """Toca som ao completar tarefa"""
        try:
            # Som de sucesso
            winsound.Beep(800, 100)
            winsound.Beep(1000, 100)
            winsound.Beep(1200, 150)
        except Exception:
            pass
    
    def animar_xp_ganho(self, xp):
        """Anima ganho de XP na tela"""
        try:
            # Criar popup temporário
            popup = ctk.CTkToplevel(self)
            popup.geometry("200x100")
            popup.attributes('-alpha', 0.9)
            popup.resizable(False, False)
            
            # Posicionar no centro da tela
            popup.update()
            x = self.winfo_x() + self.winfo_width() // 2 - 100
            y = self.winfo_y() + self.winfo_height() // 2 - 50
            popup.geometry(f"+{x}+{y}")
            
            # Cor de fundo
            popup.configure(fg_color="#1a1f3a")
            
            # Label com XP/Mana
            lbl = ctk.CTkLabel(
                popup,
                text=f"+{xp} Mana!",
                font=("Roboto", 40, "bold"),
                text_color="#7b2cbf"
            )
            lbl.pack(expand=True)
            
            # Auto-fechar após 2 segundos com fade-out
            for i in range(20):
                popup.update()
                popup.attributes('-alpha', 0.9 - (i * 0.045))
                popup.after(100)
            
            popup.destroy()
        except Exception:
            pass
    
    def deletar_tarefa_confirm(self, task_id):
        """Deleta tarefa com confirmação"""
        deletar_tarefa(task_id)
        self.carregar_tarefas()
        self.atualizar_lista_tarefas()
    
    def carregar_tarefas(self):
        """Carrega tarefas do banco"""
        self.tarefas = carregar_tarefas()
        
    def verificar_prazos(self):
        """Verifica tarefas próximas do vencimento e exibe notificação."""
        try:
            hoje = datetime.now().date()
            if not hasattr(self, '_tarefas_notificadas'):
                self._tarefas_notificadas = set()
            
            for t in self.tarefas:
                # Tupla tarefas: 0=id, 1=titulo, 5=data_vencimento, 7=concluida
                if len(t) < 8: continue
                
                t_id = t[0]
                t_nome = t[1]
                t_venc = t[5]
                t_concluida = t[7]
                
                if t_concluida or not t_venc or t_id in self._tarefas_notificadas:
                    continue
                
                try:
                    data_v = datetime.strptime(t_venc, "%Y-%m-%d").date()
                    diff = (data_v - hoje).days
                    
                    if diff == 0:
                        _notificar("⚠️ Tarefa Vence Hoje!", f"A missão '{t_nome}' expira hoje.")
                        self._tarefas_notificadas.add(t_id)
                    elif diff == 1:
                        _notificar("⏰ Tarefa Vence Amanhã!", f"Prepare-se: '{t_nome}' expira amanhã.")
                        self._tarefas_notificadas.add(t_id)
                    elif diff < 0:
                        _notificar("🚨 Tarefa Atrasada!", f"A missão '{t_nome}' está atrasada!")
                        self._tarefas_notificadas.add(t_id)
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"Erro na verificação de prazos: {e}")
            
        # Reagendar para rodar a cada 30 minutos (1800000 ms)
        self.after(1800000, self.verificar_prazos)
    
    def obter_imagem_lontra(self, nivel):
        """Obtém a imagem da lontra baseada no nível (Sistema de Evolução)"""
        # Determinar qual imagem usar baseado no nível - TABELA DE EVOLUÇÃO
        if nivel <= 10:
            # Nível 1 a 10: "A Iniciante"
            arquivo = "Uppalvl1a10.png"
        elif nivel <= 25:
            # Nível 11 a 25: "A Aprendiz"
            arquivo = "Uppalvl11a25.png"
        elif nivel <= 50:
            # Nível 26 a 50: "A Maga"
            arquivo = "Uppalvl26a50.png"
        elif nivel <= 75:
            # Nível 51 a 75: "A Arquimaga"
            arquivo = "Uppalvl51a75.png"
        else:
            # Nível 76+: "A Suprema" (Asset favorito do usuário)
            arquivo = "Uppalvl76a100.png"

        # Verificar cache
        if arquivo in self.lontra_images:
            return self.lontra_images[arquivo]

        # Buscar com resource_path (compatível com PyInstaller)
        caminho_img = resource_path(os.path.join('assets', arquivo))
        
        img = None
        if os.path.exists(caminho_img):
            try:
                img = Image.open(caminho_img)
            except Exception as e:
                print(f"Erro ao abrir imagem da Uppa: {caminho_img} - {e}")
        else:
            # Tentar caminho alternativo (Dev mode fallback se rodando da raiz fora do src)
            # Talvez assets esteja na raiz se rodar main.py da raiz sem ser module
            try:
                # Fallback para src/assets
                caminho_alt = os.path.join('src', 'assets', arquivo)
                if os.path.exists(caminho_alt):
                    img = Image.open(caminho_alt)
            except Exception:
                pass

        if img is None:
            # Silencioso para não spammar log se faltar asset na dev
            return None
            
        # Redimensionar para 200x200 (Tamanho Premium restaurado)
        img = img.resize((200, 200), Image.Resampling.LANCZOS)
        photo = ctk.CTkImage(light_image=img, dark_image=img, size=(200, 200))
        self.lontra_images[arquivo] = photo
        return photo
    
    def atualizar_ui(self):
        """Atualiza toda a UI"""
        # Checar se janela ainda existe
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return

        try:
            # Atualizar progresso
            prog = carregar_progresso()
            if prog:
                pid, nivel, xp_atual, xp_nec = prog
                
                # Detectar dano (perda de mana)
                if hasattr(self, 'ultimo_xp') and xp_atual < self.ultimo_xp:
                    self.animar_dano()
                self.ultimo_xp = xp_atual
                
                self.label_nivel.configure(text=f"NÍVEL {nivel}")
                self.label_xp.configure(text=f"{xp_atual} / {xp_nec} Mana")
                
                # Atualizar contador de Mana
                mana_total = obter_mana_total()
                self.label_mana.configure(text=f"💎 {mana_total} Mana")
                if hasattr(self, 'label_mana_loja'):
                    self.label_mana_loja.configure(text=f"💎 {mana_total} Mana")
                
                # Atualizar Streak
                stats = get_user_stats()
                streak = stats[1] if stats else 0
                self.label_streak.configure(text=f"🔥 {streak}")
                
                percent = int((xp_atual / xp_nec) * 100) if xp_nec > 0 else 0
                self.progress_xp.set_animated(min(xp_atual / xp_nec, 1.0))
                self.label_percent.configure(text=f"{percent}%")
                
                # Atualizar imagem da lontra baseada no nível
                imagem = self.obter_imagem_lontra(nivel)
                if imagem:
                    self.label_imagem_lontra.configure(image=imagem)
                else:
                    self.label_imagem_lontra.configure(text="Mascote não encontrada", image=None)
                
                # ANIMAÇÃO: Detectar ganho de XP e animar brilho (DESATIVADO - Som muito frequente)
                # if xp_atual > self.ultimo_xp:
                #     self.animar_ganho_xp()
                self.ultimo_xp = xp_atual
            
            # Contar tarefas completadas
            tarefas_completas = sum(1 for t in self.tarefas if t[7])  # t[7] é concluida
            self.label_stats_tarefas.configure(text=str(tarefas_completas))
            
            # Atualizar Efeitos Ativos na UI
            self.atualizar_active_effects_ui()

            # Repetir em 1 segundo
            self.after(1000, self.atualizar_ui)
            
        except Exception as e:
            # Evita spammar erro ao fechar
            if str(e) not in ["invalid command name", "application has been destroyed"]:
                print(f"[UI ERROR] {e}")

    
    def animar_ganho_xp(self):
        """Animação de brilho quando ganha XP - FASE 2"""
        if self.spotlight_frame is None:
            return
        
        # Cores do brilho: Normal -> Brilhante -> Normal
        cor_normal = "#c77dff"  # Roxo neon
        cor_brilho = "#ffd60a"  # Dourado mágico
        
        def pulso_1():
            try:
                self.spotlight_frame.configure(border_color=cor_brilho, border_width=6)
            except:
                pass
        
        def pulso_2():
            try:
                self.spotlight_frame.configure(border_color=cor_normal, border_width=4)
            except:
                pass
        
        # Sequência: brilha -> volta ao normal
        self.after(50, pulso_1)
        self.after(200, pulso_2)
    
    def animar_dano(self):
        """Pisca a tela em vermelho ao perder Mana"""
        original_color = self.cget("fg_color")
        flash_color = "#590000" # Vermelho escuro
        
        def restore():
            self.configure(fg_color=original_color)
            
        self.configure(fg_color=flash_color)
        winsound.Beep(150, 300) # Som grave de erro
        winsound.Beep(150, 300) # Som grave de erro
        self.after(200, restore)

    def mudar_preset(self, idx):
        """Muda o preset do pomodoro (25/50/90) com feedback visual imediato"""
        if self.pomodoro_ativo:
            self.parar_timer()
            
        self.pomodoro_atual = idx
        foco, _, _ = self.pomodoro_presets[idx]
        
        # Atualizar display do timer IMEDIATAMENTE
        try:
            self.timer_canvas.itemconfig(self.label_timer, text=f"{foco:02d}:00")
            self.timer_canvas.itemconfig(self.progress_arc, extent=-360) # Resetar para CHEIO
        except:
            pass

        # Atualizar cores dos botões (Feedback Visual)
        if hasattr(self, 'preset_buttons'):
            for i, btn in enumerate(self.preset_buttons):
                if i == idx:
                    # Selecionado: Roxo Neon + Borda
                    btn.configure(fg_color="#b44fff", border_color="#e0aaff", border_width=2)
                else:
                    # Deselecionado: Roxo Escuro + Sem borda (cor da borda igual ao fg para evitar erro)
                    btn.configure(fg_color="#3c096c", border_color="#3c096c", border_width=0)

    def resetar_timer(self):
        """Reseta o timer para o início do preset atual"""
        self.parar_timer()
        foco, pausa_curta, pausa_longa = self.pomodoro_presets[self.pomodoro_atual]
        try:
            self.timer_canvas.itemconfig(self.label_timer, text=f"{foco:02d}:00")
            self.timer_canvas.itemconfig(self.progress_arc, extent=-360)
            self.label_status_pomodoro.configure(text="🎯 Foco", fg_color="#5a189a", text_color="#ffffff")
        except:
            pass
    
    

    
    def _atualizar_display_timer(self):
        """Loop que atualiza o display do timer a cada segundo COM ANIMAÇÃO CIRCULAR"""
        # Calcular tempo total para o progresso
        foco, pausa_curta, pausa_longa = self.pomodoro_presets[self.pomodoro_atual]
        if not self.pomodoro_em_descanso:
            tempo_total = foco * 60
        else:
            # Usar pausa correta baseado no ciclo
            tempo_descanso = pausa_curta if self.pomodoro_ciclo_contador == 0 else pausa_longa
            tempo_total = tempo_descanso * 60
        
        while self.pomodoro_ativo:
            if not self.pomodoro_pausado:
                self.pomodoro_tempo_restante -= 1
                
                # Formatar tempo
                minutos = self.pomodoro_tempo_restante // 60
                segundos = self.pomodoro_tempo_restante % 60
                tempo_str = f"{minutos:02d}:{segundos:02d}"
                
                # Calcular progresso (0 a 1)
                progresso_percent = self.pomodoro_tempo_restante / tempo_total if tempo_total > 0 else 0
                
                # Angulo proporcional ao TEMPO RESTANTE (vai diminuindo de -360 até 0)
                angulo = -360 * progresso_percent
                
                # Atualizar display do canvas
                try:
                    self.timer_canvas.itemconfig(self.label_timer, text=tempo_str)
                    # Atualizar arco de progresso (extent negativo = sentido horário)
                    self.timer_canvas.itemconfig(self.progress_arc, extent=angulo)
                except Exception:
                    pass
                
                # Se chegou a zero
                if self.pomodoro_tempo_restante <= 0:
                    if not self.pomodoro_em_descanso:
                        # Foco terminou, inicia descanso
                        self._iniciar_descanso()
                    else:
                        # Descanso terminou, finaliza tudo
                        self._pomodoro_terminou()
                    break
            
            time.sleep(1)  # Aguarda 1 segundo
    
    def _iniciar_descanso(self):
        """Foco terminou, agora vai descansar (ALTERNA entre pausa curta e longa)"""
        set_timer_status(False) # Pausa monitoramento no descanso
        self.pomodoro_em_descanso = True
        
        # Pegar tempos baseado no preset atual
        foco, pausa_curta, pausa_longa = self.pomodoro_presets[self.pomodoro_atual]
        
        # Alternar entre pausa curta (ciclo 0) e pausa longa (ciclo 1)
        if self.pomodoro_ciclo_contador == 0:
            tempo_descanso = pausa_curta
            tipo_pausa = "Curta"
        else:
            tempo_descanso = pausa_longa
            tipo_pausa = "Longa"
        
        self.pomodoro_tempo_restante = tempo_descanso * 60
        
        # Atualizar indicador de status
        try:
            if tipo_pausa == "Curta":
                self.label_status_pomodoro.configure(text="☕ Pausa Curta", fg_color="#ffd43b", text_color="#1a0436")
            else:
                self.label_status_pomodoro.configure(text="🛌 Pausa Longa", fg_color="#ff6b6b", text_color="#ffffff")
        except:
            pass
        
        # Sons de fim de foco
        winsound.Beep(1200, 200)
        winsound.Beep(1000, 200)
        
        # Registrar pomodoro completado para desafios diários
        log_pomodoro(foco, was_focus=True)
        
        # --- GAME DEV: Balanceamento de Economia ---
        # Pomodoros também devem dar Mana
        mana_ganho = max(5, foco // 2)
        adicionar_mana(mana_ganho)
        try:
            _notificar("Pomodoro Concluído", f"Você ganhou {mana_ganho} Mana!")
        except Exception: pass
        
        # Atualizar desafios (verificar progresso)
        try:
            self.atualizar_desafios_ui()
        except:
            pass
        
        print(f"✅ Foco completo! Pausa {tipo_pausa} de {tempo_descanso}min...")
        
        # Continuar timer do descanso
        self.timer_thread = threading.Thread(
            target=self._atualizar_display_timer,
            daemon=True
        )
        self.timer_thread.start()
    
    def _pomodoro_terminou(self):
        """Pomodoro completo (foco + descanso) - ALTERNA CICLO"""
        set_timer_status(False)
        self.pomodoro_ativo = False
        self.pomodoro_em_descanso = False
        
        # Alternar contador de ciclo (0 -> 1 -> 0 -> 1...)
        self.pomodoro_ciclo_contador = 1 - self.pomodoro_ciclo_contador  # Toggle entre 0 e 1
        
        # Som de conclusão
        get_audio_manager().play_sfx('pomodoro_end')  # 🔊 SOM DE FIM
        
        # Resetar display para o próximo preset
        foco, pausa_curta, pausa_longa = self.pomodoro_presets[self.pomodoro_atual]
        try:
            self.timer_canvas.itemconfig(self.label_timer, text=f"{foco:02d}:00")
            self.timer_canvas.itemconfig(self.progress_arc, extent=-360) # Reset para cheio
        except:
            pass
        
        tipo_proxima = "Curta" if self.pomodoro_ciclo_contador == 0 else "Longa"
        print(f"✅ Pomodoro completo! Próximo ciclo: Pausa {tipo_proxima}")
        
        # Resetar indicador de status para Foco
        try:
            self.label_status_pomodoro.configure(text="🎯 Foco", fg_color="#5a189a", text_color="#ffffff")
        except:
            pass
        
        # AUTO-RESTART: Reiniciar automaticamente o próximo ciclo
        print(f"🔄 Iniciando próximo ciclo automaticamente em 2 segundos...")
        self.after(2000, self.iniciar_timer)  # Aguarda 2 segundos e reinicia
    
    def atualizar_active_effects_ui(self):
        """Renderiza os ícones de efeitos ativos"""
        # Obter efeitos ativos e pendentes
        effects = get_active_effects()
        
        # Se Potion XP estiver pendente, também queremos mostrar
        from database import get_pending_effects
        has_pending_xp = get_pending_effects('potion_xp')
        
        # Icones e tooltips
        icons = {
            'potion_focus': '🛡️',
            'potion_xp': '⚗️'
        }
        
        # Onde renderizar? Temos self.effects_frame (Pomodoro) e self.effects_frame_loja (Loja)
        # Vamos criar uma lista de "targets" para atualizar ambos se existirem
        targets = []
        if hasattr(self, 'effects_frame') and self.effects_frame.winfo_exists():
            targets.append(self.effects_frame)
        if hasattr(self, 'effects_frame_loja') and self.effects_frame_loja.winfo_exists():
            targets.append(self.effects_frame_loja)
            
        for frame in targets:
            # Limpar
            for widget in frame.winfo_children():
                widget.destroy()
                
            # Se não tem nada, skip
            if not effects and not has_pending_xp:
                continue
                
            # Container centralizado
            container = ctk.CTkFrame(frame, fg_color="transparent")
            container.pack(pady=2)
            
            # Renderizar Pendente (XP)
            if has_pending_xp:
                f = ctk.CTkFrame(container, fg_color="#2a0a33", corner_radius=10, border_width=1, border_color="#e0aaff")
                f.pack(side="left", padx=4)
                ctk.CTkLabel(f, text="⚗️ XP (Próx)", font=("Roboto", 10), text_color="#d8b4fe").pack(padx=6, pady=2)
            
            # Renderizar Ativos
            for effect in effects:
                code = effect['code']
                rem = effect['remaining_seconds']
                min_rem = int(rem / 60)
                sec_rem = int(rem % 60)
                
                icon = icons.get(code, '✨')
                # Cor diferente por tipo
                color = "#0b3c5d" if code == 'potion_focus' else "#5c1870"
                border = "#3282b8" if code == 'potion_focus' else "#c77dff"
                
                f = ctk.CTkFrame(container, fg_color=color, corner_radius=10, border_width=1, border_color=border)
                f.pack(side="left", padx=4)
                
                ctk.CTkLabel(
                    f, 
                    text=f"{icon} {min_rem}:{sec_rem:02d}", 
                    font=("Roboto", 11, "bold"), 
                    text_color="#fff"
                ).pack(padx=8, pady=2)

    def iniciar_timer(self):
        """Inicia o timer"""
        if self.pomodoro_ativo:
            return  # Já está rodando
        
        set_timer_status(True) # Ativa monitoramento
        self.pomodoro_ativo = True
        self.pomodoro_pausado = False
        self.pomodoro_em_descanso = False
        foco, pausa_curta, pausa_longa = self.pomodoro_presets[self.pomodoro_atual]
        self.pomodoro_tempo_restante = foco * 60  # Converter para segundos
        
        # --- ATIVAR EFEITOS PENDENTES (Potion XP) ---
        if activate_pending_effect('potion_xp', duration=foco):
            print("⚗️ Poção de XP Ativada para este ciclo!")
            get_audio_manager().play_sfx('powerup')
            _notificar("⚗️ Poção de XP Ativa!", "XP em dobro neste Pomodoro!")
        # --------------------------------------------
        
        # Iniciar thread do timer
        self.timer_thread = threading.Thread(
            target=self._atualizar_display_timer,
            daemon=True
        )
        self.timer_thread.start()
        
        tipo_pausa = "Curta" if self.pomodoro_ciclo_contador == 0 else "Longa"
        tempo_pausa = pausa_curta if self.pomodoro_ciclo_contador == 0 else pausa_longa
        print(f"✅ Pomodoro iniciado: {foco}min Foco + {tempo_pausa}min Pausa {tipo_pausa}")
        get_audio_manager().play_sfx('pomodoro_start')  # 🔊 SOM DE INÍCIO
        _notificar(
            "✅ Pomodoro Iniciado",
            f"{foco}min Foco + {tempo_pausa}min Pausa {tipo_pausa}",
            duracao=3
        )
    
    def pausar_timer(self):
        """Pausa/Retoma o timer"""
        if not self.pomodoro_ativo:
            return
        
        if self.pomodoro_pausado:
            # Retomar
            self.pomodoro_pausado = False
            set_timer_status(True)
            print("▶ Pomodoro retomado")
            _notificar(
                "▶ Pomodoro Retomado",
                "Voltando ao foco!"
            )
            winsound.Beep(900, 150)
        else:
            # Pausar
            self.pomodoro_pausado = True
            set_timer_status(False)
            print("⏸ Pomodoro pausado")
            _notificar(
                "⏸ Pomodoro Pausado",
                "Monitoramento parado"
            )
            winsound.Beep(800, 150)
    
    def parar_timer(self):
        """Para o timer completamente"""
        if not self.pomodoro_ativo:
            return
        
        
        set_timer_status(False)
        self.pomodoro_ativo = False
        self.pomodoro_em_descanso = False
        
        # Resetar display
        foco, pausa_curta, pausa_longa = self.pomodoro_presets[self.pomodoro_atual]
        try:
            self.timer_canvas.itemconfig(self.label_timer, text=f"{foco:02d}:00")
            self.timer_canvas.itemconfig(self.progress_arc, extent=-360)
        except:
            pass
        
        print("⏹ Pomodoro parado")
        winsound.Beep(500, 200)

    def toggle_foco_absoluto(self, estado: bool = None):
        """Ativa/Desativa modo Foco Absoluto"""
        # Suporta chamada direta com parâmetro ou via switch (se existir)
        if estado is None:
            if hasattr(self, 'switch_foco_absoluto'):
                estado = self.switch_foco_absoluto.get()
            else:
                estado = False
        set_absolute_focus(bool(estado))
        if estado:
             winsound.Beep(400, 100)
             winsound.Beep(300, 100) 

if __name__ == "__main__":
    app = UppaApp()
    app.mainloop()
