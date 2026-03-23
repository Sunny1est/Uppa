"""
Stats Visualizer - Gráfico de Radar para Atributos RPG
Integra matplotlib com CustomTkinter
"""
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure


def create_radar_chart(parent_frame, stats_dict, size=(150, 150), bg_color='#261635'):
    """
    Cria um gráfico de radar pentagonal para visualizar stats RPG.
    
    Args:
        parent_frame: Frame CTk onde inserir o gráfico
        stats_dict: Dict com stats {'INT': valor, 'DEX': valor, ...}
        size: Tupla (width, height) em pixels
        bg_color: Cor de fundo do gráfico (hex)
        
    Returns:
        Canvas do matplotlib integrado ao Tkinter
    """
    # Labels dos atributos (ordem fixa)
    labels = ['INT', 'DEX', 'STR', 'CHA', 'CRI']
    stats = [stats_dict.get(label, 0) for label in labels]
    
    # Normalizar valores para o gráfico (max 100 para escala)
    max_value = max(stats) if max(stats) > 0 else 1
    normalized_stats = stats.copy()
    
    # Criar ângulos para pentágono (5 pontos)
    num_vars = len(labels)
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    
    # Fechar o polígono (repetir primeiro valor)
    normalized_stats += [normalized_stats[0]]
    angles += [angles[0]]
    
    # Criar figura com fundo do tema (sem transparência para evitar bordas brancas)
    # Cor de fundo do app: #1a0b2e (cor do card) ou #0d0221 (cor do app)
    # Usando a cor do card onde o gráfico está inserido - Default atualizado para #2a1050 (Card Scrollable)
    theme_bg = bg_color
    
    fig = Figure(figsize=(size[0]/100, size[1]/100), dpi=100)
    fig.patch.set_facecolor(theme_bg) # Fundo da figura
    
    # Criar subplot polar
    ax = fig.add_subplot(111, polar=True)
    ax.set_facecolor(theme_bg)  # Fundo do plot
    
    # Desenhar polígono
    ax.plot(angles, normalized_stats, 'o-', linewidth=2, color='#bf00ff', markersize=4) # Neon Purple
    ax.fill(angles, normalized_stats, alpha=0.3, color='#bf00ff') # Semi-transparent Purple
    
    # Configurar labels
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, color='#f8f0ff', size=9, weight='bold') # Pearly White
    
    # Ajustar limites para dar respiro aos labels
    ax.set_ylim(0, max_value * 1.15)

    # Remover números radiais e simplificar grid
    ax.set_yticks([])
    ax.set_yticklabels([])
    ax.grid(color='#4d2c63', alpha=0.3, linewidth=0.8) # Mais suave e roxo para o novo tema
    ax.spines['polar'].set_visible(False)
    
    # FORÇAR POSIÇÃO DOS EIXOS
    ax.set_position([0.2, 0.2, 0.6, 0.6])
    
    # Integrar ao Tkinter
    canvas = FigureCanvasTkAgg(fig, master=parent_frame)
    canvas.draw()
    
    # Remover bordas extras do widget
    canvas.get_tk_widget().configure(bg=theme_bg, highlightthickness=0)
    
    return canvas


def get_attribute_color(attribute):
    """Retorna cor temática para cada atributo em harmonia com o novo tema"""
    colors = {
        'INT': '#00f2ff',  # Mana Blue
        'DEX': '#df80ff',  # Bright Purple
        'STR': '#ff3366',  # Crimson
        'CHA': '#00ff9d',  # Emerald
        'CRI': '#ffd700'   # Gold
    }
    return colors.get(attribute, '#f8f0ff')


# Teste standalone
if __name__ == "__main__":
    import customtkinter as ctk
    from database import get_all_stats, adicionar_stat_points
    
    # Adicionar alguns pontos para teste
    adicionar_stat_points('INT', 25)
    adicionar_stat_points('DEX', 15)
    adicionar_stat_points('STR', 10)
    adicionar_stat_points('CHA', 20)
    adicionar_stat_points('CRI', 18)
    
    # Criar janela de teste
    root = ctk.CTk()
    root.title("Teste - Radar Chart")
    root.geometry("300x300")
    root.configure(fg_color="#1a0b2e")
    
    # Frame container
    frame = ctk.CTkFrame(root, fg_color="transparent")
    frame.pack(fill="both", expand=True, padx=20, pady=20)
    
    # Criar gráfico
    stats = get_all_stats()
    print(f"Stats: {stats}")
    
    canvas = create_radar_chart(frame, stats, size=(200, 200))
    canvas.get_tk_widget().pack()
    
    root.mainloop()
