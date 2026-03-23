
import customtkinter as ctk
from PIL import Image
import logging
from config import THEME, IMAGES_DIR
from database import set_setting

logger = logging.getLogger("uppa.onboarding")

class OnboardingOverlay(ctk.CTkFrame):
    """
    Overlay de onboarding para novos usuários.
    Exibe um tutorial passo a passo sobre as funcionalidades do app.
    """
    def __init__(self, parent, on_complete=None):
        super().__init__(parent, fg_color="transparent")
        self.parent = parent
        self.on_complete = on_complete
        self.place(relx=0, rely=0, relwidth=1, relheight=1)
        
        self.steps = [
            {
                "title": "Olá, Viajante!",
                "text": "Eu sou o Uppa, seu novo mascote de produtividade!\n\nEstou aqui para te ajudar a manter o foco e tornar suas tarefas mais divertidas, transformando sua rotina em um RPG.",
                # "image": "uppa_happy.png" 
            },
            {
                "title": "Perfil de Herói",
                "text": "No canto esquerdo, você vê seu Nível e XP.\n\nCada tarefa concluída te dá XP para evoluir. Quanto maior seu nível, mais recursos você desbloqueia!",
                # "image": "uppa_neutral.png"
            },
            {
                "title": "Missões (Tarefas)",
                "text": "No centro, você gerencia suas Missões.\n\nAdicione tarefas, defina a dificuldade e ganhe recompensas ao completá-las. Cuidado com os prazos!",
                # "image": "uppa_study.png"
            },
            {
                "title": "Zona de Foco",
                "text": "Use o Pomodoro à direita para focar.\n\nO tempo focado gera Mana e acelera sua evolução. Evite distrações para manter o combo!",
                # "image": "uppa_focus.png"
            },
            {
                "title": "Loja e Mana",
                "text": "Complete tarefas e mantenha o foco para ganhar Mana.\n\nUse Mana na Loja para comprar novos visuais para mim, poções e outros itens mágicos!",
                # "image": "uppa_happy.png"
            },
            {
                "title": "Tudo Pronto!",
                "text": "Agora é com você!\n\nComece adicionando sua primeira tarefa ou iniciando um ciclo de foco. Boa sorte na sua jornada!",
                # "image": "uppa_excited.png"
            }
        ]
        
        self.current_step_index = 0
        
        # Fundo semi-transparente (simulado com cor solida escura para foco)
        self.bg_overlay = ctk.CTkFrame(self, fg_color="#050010", corner_radius=0)
        self.bg_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        # Tenta pegar evento de click para não passar para baixo
        self.bg_overlay.bind("<Button-1>", lambda e: "break")
        
        self.setup_ui()
        self.show_step(0)

    def setup_ui(self):
        # Container do Card
        self.card = ctk.CTkFrame(
            self, 
            fg_color=THEME["bg_card"], 
            corner_radius=20, 
            border_width=2, 
            border_color=THEME["primary"]
        )
        self.card.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.5, relheight=0.6)
        
        # Imagem (Placeholder/Mascote)
        self.image_label = ctk.CTkLabel(self.card, text="")
        self.image_label.pack(pady=(30, 10))
        
        # Título
        self.title_label = ctk.CTkLabel(
            self.card, 
            text="", 
            font=("Roboto", 24, "bold"),
            text_color=THEME["primary"]
        )
        self.title_label.pack(pady=(10, 10))
        
        # Texto
        self.text_label = ctk.CTkLabel(
            self.card, 
            text="", 
            font=("Roboto", 16),
            wraplength=380,
            text_color=THEME["text_main"],
            justify="center"
        )
        self.text_label.pack(pady=(0, 20), padx=30, fill="both")
        
        # Footer (Botoes)
        self.footer_frame = ctk.CTkFrame(self.card, fg_color="transparent")
        self.footer_frame.pack(pady=20, padx=30, fill="x", side="bottom")
        
        # Botão Pular
        self.btn_skip = ctk.CTkButton(
            self.footer_frame,
            text="Pular Tutorial",
            fg_color="transparent",
            border_width=1,
            border_color=THEME["secondary"],
            text_color=THEME["secondary"],
            hover_color=THEME["bg_container"],
            width=100,
            command=self.finish_tutorial
        )
        self.btn_skip.pack(side="left")
        
        # Indicadores de progresso
        self.dots_frame = ctk.CTkFrame(self.footer_frame, fg_color="transparent")
        self.dots_frame.pack(side="left", expand=True)
        
        # Botão Próximo
        self.btn_next = ctk.CTkButton(
            self.footer_frame,
            text="Próximo",
            fg_color=THEME["primary"],
            hover_color=THEME["primary_hover"],
            width=100,
            command=self.next_step
        )
        self.btn_next.pack(side="right")

    def show_step(self, index):
        if index < 0 or index >= len(self.steps):
            return
            
        step = self.steps[index]
        
        self.title_label.configure(text=step["title"])
        self.text_label.configure(text=step["text"])
        
        # Atualiza imagem se dispovel no parent (UppaApp)
        image = None
        if hasattr(self.parent, "obter_imagem_lontra"):
            try:
                # Tenta pegar imagem do nivel 1 ou atual
                image = self.parent.obter_imagem_lontra(1)
            except Exception:
                pass
                
        if image:
            self.image_label.configure(image=image, text="")
        else:
            self.image_label.configure(text="[Uppa]", font=("Roboto", 40))
        
        # Atualiza botoes
        if index == len(self.steps) - 1:
            self.btn_next.configure(text="Começar!")
        else:
            self.btn_next.configure(text="Próximo")
            
        # Atualiza dots
        for widget in self.dots_frame.winfo_children():
            widget.destroy()
            
        for i in range(len(self.steps)):
            color = THEME["primary"] if i == index else "#555"
            size = 24 if i == index else 20
            dot = ctk.CTkLabel(self.dots_frame, text="•", font=("Arial", size), text_color=color)
            dot.pack(side="left", padx=2)

    def next_step(self):
        if self.current_step_index < len(self.steps) - 1:
            self.current_step_index += 1
            self.show_step(self.current_step_index)
        else:
            self.finish_tutorial()

    def finish_tutorial(self):
        try:
            success = set_setting("tutorial_completed", "1")
            if not success:
                logger.error("Falha ao salvar estado do tutorial")
        except Exception as e:
            logger.error(f"Erro ao finalizar tutorial: {e}")
            
        self.destroy()
        if self.on_complete:
            self.on_complete()
