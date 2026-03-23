"""
Uppa! - Sistema de Relatórios
Janela separada com gráficos de produtividade e estatísticas.
"""

import customtkinter as ctk
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np

from config import get_logger, COLORS, THEME
from database import _get_db_connection

# Logger
logger = get_logger("uppa.reports")


class ReportsWindow(ctk.CTkToplevel):
    """
    Janela de Relatórios de Produtividade.
    
    Exibe:
    - Gráfico de foco por dia (últimos 7 dias)
    - Tarefas completadas por semana
    - Estatísticas gerais
    """
    
    def __init__(self, parent):
        super().__init__(parent)
        
        self.title("📊 Relatórios de Produtividade - Uppa!")
        self.geometry("800x600")
        self.configure(fg_color=THEME["bg_main"])
        
        # Configurar para ficar na frente
        self.transient(parent)
        self.grab_set()
        
        # Dados
        self.current_period = "semana"  # "semana" ou "mes"
        
        # Setup UI
        self._setup_ui()
        self._load_data()
    
    def _setup_ui(self):
        """Cria a interface do relatório"""
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 10))
        
        ctk.CTkLabel(
            header, text="📊 Relatórios de Produtividade",
            font=("Roboto", 24, "bold"),
            text_color=THEME["text_main"]
        ).pack(side="left")
        
        # Botão fechar
        ctk.CTkButton(
            header, text="✕", width=40, height=40,
            fg_color="#ff6b6b",
            hover_color="#fa5252",
            command=self.destroy
        ).pack(side="right")
        
        # Tabs de período
        tabs_frame = ctk.CTkFrame(self, fg_color="transparent")
        tabs_frame.pack(fill="x", padx=20, pady=10)
        
        self.period_var = ctk.StringVar(value="Semana")
        self.period_selector = ctk.CTkSegmentedButton(
            tabs_frame,
            values=["Semana", "Mês", "Histórico"],
            variable=self.period_var,
            command=self._on_period_change,
            selected_color="#9d4edd",
            selected_hover_color="#c77dff",
            unselected_color="#240046",
            unselected_hover_color="#3c096c"
        )
        self.period_selector.pack(fill="x")
        
        # Container principal (scrollável)
        self.content_frame = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent"
        )
        self.content_frame.pack(fill="both", expand=True, padx=20, pady=10)
    
    def _on_period_change(self, value):
        """Callback para mudança de período"""
        self.current_period = value.lower()
        self._load_data()
    
    def _load_data(self):
        """Carrega e exibe os dados do período selecionado"""
        # Limpar conteúdo anterior
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        if self.current_period == "semana":
            self._render_week_report()
        elif self.current_period == "mês":
            self._render_month_report()
        else:
            self._render_history_report()
    
    def _render_week_report(self):
        """Renderiza relatório semanal"""
        # Card de estatísticas rápidas
        stats_card = ctk.CTkFrame(
            self.content_frame,
            fg_color=THEME["bg_card"],
            corner_radius=20
        )
        stats_card.pack(fill="x", pady=10)
        
        # Buscar dados
        focus_data = self._get_focus_by_day(7)
        tasks_data = self._get_tasks_by_day(7)
        total_focus = sum(focus_data.values())
        total_tasks = sum(tasks_data.values())
        
        # Grid de estatísticas
        stats_inner = ctk.CTkFrame(stats_card, fg_color="transparent")
        stats_inner.pack(fill="x", padx=20, pady=15)
        
        stats = [
            ("⏱️", f"{total_focus}min", "Tempo de Foco"),
            ("✅", str(total_tasks), "Tarefas Completas"),
            ("📈", f"{total_focus // 7}min/dia", "Média Diária"),
        ]
        
        for i, (icon, value, label) in enumerate(stats):
            col = ctk.CTkFrame(stats_inner, fg_color="transparent")
            col.pack(side="left", expand=True, fill="x")
            
            ctk.CTkLabel(
                col, text=icon,
                font=("Segoe UI Emoji", 28)
            ).pack()
            
            ctk.CTkLabel(
                col, text=value,
                font=("Roboto", 22, "bold"),
                text_color=COLORS["gold"]
            ).pack()
            
            ctk.CTkLabel(
                col, text=label,
                font=("Roboto", 11),
                text_color="#aaa"
            ).pack()
        
        # Gráfico de barras - Foco por dia
        chart_card = ctk.CTkFrame(
            self.content_frame,
            fg_color=THEME["bg_card"],
            corner_radius=20
        )
        chart_card.pack(fill="x", pady=10)
        
        ctk.CTkLabel(
            chart_card, text="📊 Tempo de Foco por Dia",
            font=("Roboto", 14, "bold"),
            text_color=THEME["text_sec"]
        ).pack(anchor="w", padx=20, pady=(15, 5))
        
        self._create_bar_chart(chart_card, focus_data, "Minutos", COLORS["accent"])
        
        # Gráfico de tarefas
        tasks_card = ctk.CTkFrame(
            self.content_frame,
            fg_color=THEME["bg_card"],
            corner_radius=20
        )
        tasks_card.pack(fill="x", pady=10)
        
        ctk.CTkLabel(
            tasks_card, text="✅ Tarefas Completadas por Dia",
            font=("Roboto", 14, "bold"),
            text_color=THEME["text_sec"]
        ).pack(anchor="w", padx=20, pady=(15, 5))
        
        self._create_bar_chart(tasks_card, tasks_data, "Tarefas", THEME["success"])
    
    def _render_month_report(self):
        """Renderiza relatório mensal"""
        # Buscar dados de 30 dias
        focus_data = self._get_focus_by_day(30)
        tasks_data = self._get_tasks_by_day(30)
        
        total_focus = sum(focus_data.values())
        total_tasks = sum(tasks_data.values())
        
        # Card resumo
        stats_card = ctk.CTkFrame(
            self.content_frame,
            fg_color="#2a1050",
            corner_radius=20
        )
        stats_card.pack(fill="x", pady=10)
        
        stats_inner = ctk.CTkFrame(stats_card, fg_color="transparent")
        stats_inner.pack(fill="x", padx=20, pady=15)
        
        stats = [
            ("⏱️", f"{total_focus // 60}h {total_focus % 60}m", "Tempo Total"),
            ("✅", str(total_tasks), "Tarefas Completas"),
            ("🔥", f"{len([v for v in focus_data.values() if v > 0])}", "Dias Ativos"),
        ]
        
        for i, (icon, value, label) in enumerate(stats):
            col = ctk.CTkFrame(stats_inner, fg_color="transparent")
            col.pack(side="left", expand=True, fill="x")
            
            ctk.CTkLabel(col, text=icon, font=("Segoe UI Emoji", 28)).pack()
            ctk.CTkLabel(col, text=value, font=("Roboto", 22, "bold"), text_color="#ffd60a").pack()
            ctk.CTkLabel(col, text=label, font=("Roboto", 11), text_color="#aaa").pack()
        
        # Gráfico mensal (por semana)
        weekly_data = self._aggregate_by_week(focus_data)
        
        chart_card = ctk.CTkFrame(
            self.content_frame,
            fg_color="#2a1050",
            corner_radius=20
        )
        chart_card.pack(fill="x", pady=10)
        
        ctk.CTkLabel(
            chart_card, text="📊 Foco por Semana",
            font=("Roboto", 14, "bold"),
            text_color="#e0aaff"
        ).pack(anchor="w", padx=20, pady=(15, 5))
        
        self._create_bar_chart(chart_card, weekly_data, "Minutos", "#9d4edd")
    
    def _render_history_report(self):
        """Renderiza estatísticas históricas"""
        conn = _get_db_connection()
        cursor = conn.cursor()
        
        # Total de tarefas
        cursor.execute("SELECT COUNT(*) FROM historico_tarefas")
        total_tasks = cursor.fetchone()[0]
        
        # Total de focus
        cursor.execute("SELECT total_focus_minutes FROM user_stats WHERE id = 1")
        row = cursor.fetchone()
        total_focus = row[0] if row else 0
        
        # Streak atual
        cursor.execute("SELECT current_streak FROM user_stats WHERE id = 1")
        row = cursor.fetchone()
        streak = row[0] if row else 0
        
        # Nível atual
        cursor.execute("SELECT nivel, xp_atual FROM progresso WHERE id = 1")
        row = cursor.fetchone()
        nivel, xp = row if row else (1, 0)
        
        conn.close()
        
        # Card de estatísticas históricas
        stats_card = ctk.CTkFrame(
            self.content_frame,
            fg_color=THEME["bg_card"],
            corner_radius=20
        )
        stats_card.pack(fill="x", pady=10)
        
        ctk.CTkLabel(
            stats_card, text="🏆 Estatísticas Históricas",
            font=("Roboto", 16, "bold"),
            text_color=COLORS["gold"]
        ).pack(pady=(15, 10))
        
        stats = [
            ("⏱️ Tempo Total de Foco", f"{total_focus // 60}h {total_focus % 60}min"),
            ("✅ Tarefas Completadas", str(total_tasks)),
            ("🔥 Streak Atual", f"{streak} dias"),
            ("⭐ Nível", f"{nivel} ({xp} XP)"),
        ]
        
        for label, value in stats:
            row = ctk.CTkFrame(stats_card, fg_color="transparent")
            row.pack(fill="x", padx=20, pady=5)
            
            ctk.CTkLabel(
                row, text=label,
                font=("Roboto", 12),
                text_color="#aaa"
            ).pack(side="left")
            
            ctk.CTkLabel(
                row, text=value,
                font=("Roboto", 14, "bold"),
                text_color="#e0aaff"
            ).pack(side="right")
        
        # Padding final
        ctk.CTkFrame(stats_card, fg_color="transparent", height=15).pack()
    
    def _create_bar_chart(self, parent, data: Dict[str, int], ylabel: str, color: str):
        """Cria um gráfico de barras usando matplotlib"""
        # Definir cores based no tema atual (Matplotlib não suporta tuplas CTk)
        mode = ctk.get_appearance_mode()
        is_dark = mode == "Dark"
        
        bg_color = '#2a1050' if is_dark else '#ffffff'
        text_color = '#aaaaaa' if is_dark else '#333333'
        spine_color = '#444444' if is_dark else '#dddddd'
        
        fig = Figure(figsize=(7, 2.5), facecolor=bg_color)
        ax = fig.add_subplot(111)
        
        # Configurar aparência
        ax.set_facecolor(bg_color)
        ax.tick_params(colors=text_color, labelsize=8)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_color(spine_color)
        ax.spines['left'].set_color(spine_color)
        
        # Dados
        labels = list(data.keys())
        values = list(data.values())
        
        # Criar barras
        bars = ax.bar(labels, values, color=color, edgecolor='none', width=0.6)
        
        # Labels nas barras
        for bar, val in zip(bars, values):
            if val > 0:
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                       str(val), ha='center', va='bottom', color=text_color, fontsize=8)
        
        ax.set_ylabel(ylabel, color=text_color, fontsize=9)
        
        fig.tight_layout()
        
        # Embed no tkinter
        canvas = FigureCanvasTkAgg(fig, parent)
        canvas.draw()
        canvas.get_tk_widget().pack(padx=10, pady=(0, 15))
    
    def _get_focus_by_day(self, days: int) -> Dict[str, int]:
        """Retorna minutos de foco por dia"""
        conn = _get_db_connection()
        cursor = conn.cursor()
        
        result = {}
        today = datetime.now().date()
        
        for i in range(days - 1, -1, -1):
            day = today - timedelta(days=i)
            day_str = day.isoformat()
            day_label = day.strftime("%d/%m") if days > 7 else day.strftime("%a")
            
            cursor.execute("""
                SELECT SUM(duration_minutes) FROM pomodoro_log 
                WHERE date = ? AND was_focus = 1
            """, (day_str,))
            
            row = cursor.fetchone()
            result[day_label] = row[0] if row and row[0] else 0
        
        conn.close()
        return result
    
    def _get_tasks_by_day(self, days: int) -> Dict[str, int]:
        """Retorna tarefas completadas por dia"""
        conn = _get_db_connection()
        cursor = conn.cursor()
        
        result = {}
        today = datetime.now().date()
        
        for i in range(days - 1, -1, -1):
            day = today - timedelta(days=i)
            day_str = day.isoformat()
            day_label = day.strftime("%d/%m") if days > 7 else day.strftime("%a")
            
            cursor.execute("""
                SELECT COUNT(*) FROM historico_tarefas 
                WHERE DATE(data_conclusao) = ?
            """, (day_str,))
            
            row = cursor.fetchone()
            result[day_label] = row[0] if row else 0
        
        conn.close()
        return result
    
    def _aggregate_by_week(self, daily_data: Dict[str, int]) -> Dict[str, int]:
        """Agrega dados diários em semanas"""
        items = list(daily_data.items())
        weeks = {}
        
        for i in range(0, len(items), 7):
            week_items = items[i:i+7]
            week_label = f"Sem {(i // 7) + 1}"
            weeks[week_label] = sum(v for _, v in week_items)
        
        return weeks


# Teste
if __name__ == "__main__":
    import customtkinter as ctk
    from database import iniciar_banco
    
    iniciar_banco()
    
    root = ctk.CTk()
    root.geometry("200x100")
    
    def open_reports():
        ReportsWindow(root)
    
    ctk.CTkButton(root, text="Abrir Relatórios", command=open_reports).pack(pady=30)
    
    root.mainloop()
