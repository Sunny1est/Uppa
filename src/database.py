import sqlite3
import os
import logging
from typing import List, Tuple
from datetime import datetime
from config import DB_PATH

# Logger para este módulo
logger = logging.getLogger("uppa.database")

# Caminho do banco de dados centralizado em config.py
DB_FILE = str(DB_PATH)


def _get_db_connection():
    """Retorna uma conexão com o banco de dados."""
    return sqlite3.connect(DB_FILE, timeout=10.0)

def iniciar_banco() -> None:
    """Inicializa o banco de dados e cria as tabelas necessárias."""
    try:
        with _get_db_connection() as conn:
            cursor = conn.cursor()

            # Criar tabela de progresso
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS progresso (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nivel INTEGER DEFAULT 1,
                    xp_atual INTEGER DEFAULT 0,
                    xp_necessario INTEGER DEFAULT 100,
                    mana_total INTEGER DEFAULT 0,
                    trocas_contexto_total INTEGER DEFAULT 0,
                    titulo TEXT DEFAULT 'Lontra Aprendiz',
                    stat_int INTEGER DEFAULT 0,
                    stat_dex INTEGER DEFAULT 0,
                    stat_str INTEGER DEFAULT 0,
                    stat_cha INTEGER DEFAULT 0,
                    stat_cri INTEGER DEFAULT 0
                )
                """
            )

            # Criar tabela de whitelist
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS whitelist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome_app TEXT UNIQUE
                )
                """
            )

            # Criar tabela de apps neutros
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS apps_neutros (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome_app TEXT UNIQUE
                )
                """
            )

            # --- NOVAS TABELAS PARA GRIMÓRIO (MODULE 3) ---
            # Tabela de estatísticas persistentes
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS user_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    total_focus_minutes INTEGER DEFAULT 0,
                    longest_session INTEGER DEFAULT 0,
                    last_login_date TEXT,
                    current_streak INTEGER DEFAULT 0
                )
                """
            )

            # Tabela de conquistas desbloqueadas
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS achievements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT UNIQUE,
                    name TEXT,
                    description TEXT,
                    unlocked_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            # Inicializar stats se vazio
            cursor.execute("SELECT COUNT(*) FROM user_stats")
            if cursor.fetchone()[0] == 0:
                cursor.execute(
                    "INSERT INTO user_stats (total_focus_minutes, longest_session, current_streak) VALUES (0, 0, 0)"
                )
            
            # Tabela de inventário de itens
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS inventory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_code TEXT UNIQUE NOT NULL,
                    quantity INTEGER DEFAULT 0
                )
                """
            )
            
            # Inicializar itens do inventário
            itens_padrao = [
                ('potion_focus',),
                ('potion_xp',),
                ('hourglass',)
            ]
            cursor.executemany(
                "INSERT OR IGNORE INTO inventory (item_code, quantity) VALUES (?, 0)",
                itens_padrao
            )

            # Tabela de efeitos ativos (Potions)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS active_effects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_code TEXT NOT NULL,
                    start_time TEXT DEFAULT CURRENT_TIMESTAMP,
                    duration_minutes INTEGER,
                    status TEXT DEFAULT 'active'
                )
                """
            )
            
            # Tabela de desafios diários
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS daily_challenges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    challenge_code TEXT NOT NULL,
                    is_completed INTEGER DEFAULT 0,
                    claimed INTEGER DEFAULT 0,
                    UNIQUE(date, challenge_code)
                )
                """
            )
            
            # Tabela de log de pomodoros (para desafios)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS pomodoro_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    duration_minutes INTEGER,
                    was_focus INTEGER DEFAULT 1
                )
                """
            )
            # -----------------------------------------------
            
            # Tabela de configurações do app (Key-Value)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS app_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
                """
            )
            
            # Inicializar tutorial se não existir
            cursor.execute("SELECT 1 FROM app_settings WHERE key = 'tutorial_completed'")
            if not cursor.fetchone():
                 cursor.execute("INSERT OR IGNORE INTO app_settings (key, value) VALUES ('tutorial_completed', '0')")

            # Criar tabela de tarefas
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS tarefas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    titulo TEXT NOT NULL,
                    descricao TEXT,
                    nivel INTEGER DEFAULT 1,
                    xp_base INTEGER DEFAULT 10,
                    data_vencimento TEXT,
                    prioridade INTEGER DEFAULT 1,
                    concluida INTEGER DEFAULT 0,
                    criada_em TEXT DEFAULT CURRENT_TIMESTAMP,
                    attribute_tag TEXT DEFAULT 'DEX',
                    is_recurring INTEGER DEFAULT 0,
                    recurrence_pattern TEXT,
                    last_renewed_date TEXT
                )
                """
            )

            # --- Migração Retroativa: Tarefas Recorrentes ---
            try:
                cursor.execute("ALTER TABLE tarefas ADD COLUMN is_recurring INTEGER DEFAULT 0")
                cursor.execute("ALTER TABLE tarefas ADD COLUMN recurrence_pattern TEXT")
                cursor.execute("ALTER TABLE tarefas ADD COLUMN last_renewed_date TEXT")
            except Exception:
                pass  # Colunas já existem

            # Criar tabela de commits para snapshots de estado
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS commits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                    progresso_data TEXT,  -- JSON com dados de progresso
                    tarefas_data TEXT     -- JSON com lista de tarefas
                )
                """
            )

            # Criar tabela de histórico de tarefas concluídas
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS historico_tarefas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tarefa_id INTEGER,
                    titulo TEXT NOT NULL,
                    xp_ganho INTEGER,
                    data_conclusao TEXT DEFAULT CURRENT_TIMESTAMP,
                    nivel_dificuldade INTEGER,
                    bonus_temporal INTEGER DEFAULT 0
                )
                """
            )

            # Inserir apps neutros padrão (não penalizam, mas podem dar recompensa)
            apps_neutros: List[Tuple[str]] = [
                # Apps do próprio sistema Uppa
                ("Uppa",),
                ("uppa",),
                ("Python",),
                ("Nova Tarefa",),
                ("Criar Tarefa",),
                ("nova tarefa",),
                ("criar tarefa",),

                # Ferramentas do Sistema Windows (neutras - não produtivas nem improdutivas)
                ("Snipping Tool",),  # Ferramenta de captura de tela
                ("Snip & Sketch",),  # Ferramenta de captura de tela
                ("Print Screen",),  # Captura de tela
                ("Screenshot",),  # Captura de tela
                ("Screen capture",),  # Captura de tela
                ("Lightshot",),  # Captura de tela
                ("Greenshot",),  # Captura de tela
                ("ShareX",),  # Captura de tela e compartilhamento
                ("Flameshot",),  # Captura de tela
                ("Gyazo",),  # Captura de tela

                # Gerenciamento de Arquivos
                ("File Explorer",),
                ("Windows Explorer",),
                ("Explorer",),
                ("This PC",),
                ("My Computer",),
                ("Documents",),
                ("Downloads",),
                ("Desktop",),

                # Configurações e Sistema
                ("Settings",),
                ("Control Panel",),
                ("System Properties",),
                ("Device Manager",),
                ("Task Manager",),
                ("Resource Monitor",),
                ("Event Viewer",),
                ("Services",),
                ("Registry Editor",),
                ("Command Prompt",),
                ("PowerShell",),
                ("Windows Terminal",),
                ("Run",),
                ("Search",),
                ("Cortana",),
                ("Start Menu",),

                # Atualizações e Manutenção
                ("Windows Update",),
                ("Windows Security",),
                ("Windows Defender",),
                ("Microsoft Store",),
                ("App Installer",),

                # Outros Neutros
                ("Calculator",),
                ("Calendar",),
                ("Clock",),
                ("Weather",),
                ("Photos",),
                ("Paint",),
                ("Notepad",),
                ("WordPad",),
                ("Sticky Notes",),
                ("Steps Recorder",),
                ("Problem Steps Recorder",),
                ("Quick Assist",),
                ("Remote Desktop",),
                ("Magnifier",),
                ("Narrator",),
                ("On-Screen Keyboard",),
            ]
            cursor.executemany(
                "INSERT OR IGNORE INTO apps_neutros (nome_app) VALUES (?)", apps_neutros
            )

            # Inserir progresso inicial se não existir
            cursor.execute("SELECT COUNT(*) FROM progresso")
            if cursor.fetchone()[0] == 0:
                cursor.execute(
                    """
                    INSERT INTO progresso (nivel, xp_atual, xp_necessario, trocas_contexto_total, titulo)
                    VALUES (1, 0, 200, 0, 'Lontra Aprendiz')
                    """
                )

            # Inserir aplicativos padrão (lista pequena)
            apps_padrao: List[Tuple[str]] = [
                ("Visual Studio Code",),
                ("Google Chrome",),
                ("Spotify",),
                ("Slack",),
                ("Notion",),
                ("PyCharm",),
                ("Python",),
                ("Stack Overflow",),
            ]

            # Lista mais completa de apps de produtividade / dev
            apps_produtividade: List[Tuple[str]] = [
                # Desenvolvimento e IDEs
                ("Visual Studio Code",),
                ("PyCharm",),
                ("IntelliJ IDEA",),
                ("Eclipse",),
                ("Android Studio",),
                ("WebStorm",),
                ("DataGrip",),
                ("DBeaver",),
                ("SQL Developer",),
                ("Visual Studio",),
                ("Sublime Text",),
                ("Atom",),
                ("Vim",),
                ("Emacs",),
                ("Xcode",),
                ("NetBeans",),
                ("Code::Blocks",),
                ("Dev-C++",),
                ("Qt Creator",),
                ("RStudio",),
                ("Jupyter Notebook",),
                ("Spyder",),
                ("Anaconda Navigator",),

                # Navegadores e Web
                ("Google Chrome",),
                ("Mozilla Firefox",),
                ("Microsoft Edge",),
                ("Opera",),
                ("Safari",),
                ("Brave",),
                ("Vivaldi",),

                # Comunicação e Colaboração
                ("Slack",),
                ("Microsoft Teams",),
                ("Discord",),
                ("Zoom",),
                ("Microsoft Outlook",),
                ("Gmail",),
                ("Thunderbird",),
                ("Skype",),
                ("Webex",),
                ("Cisco Webex",),

                # Produtividade e Escritório
                ("Microsoft Word",),
                ("Microsoft Excel",),
                ("Microsoft PowerPoint",),
                ("Google Docs",),
                ("Google Sheets",),
                ("Google Slides",),
                ("LibreOffice",),
                ("OpenOffice",),
                ("WPS Office",),
                ("Notion",),
                ("Obsidian",),
                ("OneNote",),
                ("Evernote",),
                ("Trello",),
                ("Asana",),
                ("Jira",),
                ("Confluence",),
                ("Miro",),
                ("Figma",),
                ("Adobe XD",),
                ("Sketch",),
                ("Canva",),

                # Banco de Dados e Análise
                ("Power BI Desktop",),
                ("Tableau",),
                ("pgAdmin",),
                ("MySQL Workbench",),
                ("HeidiSQL",),
                ("SQL Server Management Studio",),
                ("Oracle SQL Developer",),
                ("MongoDB Compass",),
                ("Redis Desktop Manager",),
                ("Postman",),
                ("Insomnia",),
                ("Swagger",),

                # Versionamento e DevOps
                ("Git",),
                ("GitHub Desktop",),
                ("GitLab",),
                ("Bitbucket",),
                ("SourceTree",),
                ("TortoiseGit",),
                ("Docker Desktop",),
                ("VirtualBox",),
                ("VMware Workstation",),
                ("Kubernetes",),
                ("Jenkins",),
                ("GitHub Actions",),

                # Outros Produtivos
                ("Spotify",),  # Música para foco
                ("Focus@Will",),
                ("Forest",),
                ("RescueTime",),
                ("Toggl",),
                ("Clockify",),
                ("Grammarly",),
                ("Hemingway",),
                ("Scrivener",),
                ("Zotero",),
                ("Mendeley",),
            ]

            # Inserir nas tabelas de whitelist (usando INSERT OR IGNORE para evitar conflitos)
            cursor.executemany(
                "INSERT OR IGNORE INTO whitelist (nome_app) VALUES (?)",
                apps_produtividade,
            )

            conn.commit()
            logger.info(f" Banco de dados iniciado e tabelas criadas com sucesso.")

    except sqlite3.Error as e:
        logger.error(f" Erro ao inicializar banco de dados: {e}", exc_info=True)
        raise


def salvar_commit() -> None:
    """Salva um snapshot do estado atual (progresso + tarefas) como um commit."""
    import json
    try:
        with _get_db_connection() as conn:
            cursor = conn.cursor()

            # Buscar progresso atual
            cursor.execute("SELECT nivel, xp_atual, xp_necessario, titulo FROM progresso WHERE id = 1")
            progresso = cursor.fetchone()
            if progresso:
                progresso_data = {
                    "nivel": progresso[0],
                    "xp_atual": progresso[1],
                    "xp_necessario": progresso[2],
                    "titulo": progresso[3]
                }
            else:
                progresso_data = {"nivel": 1, "xp_atual": 0, "xp_necessario": 100, "titulo": "Lontra Aprendiz"}

            # Buscar tarefas atuais
            cursor.execute("SELECT id, titulo, descricao, nivel, xp_base, data_vencimento, prioridade, concluida, criada_em FROM tarefas ORDER BY id")
            tarefas = cursor.fetchall()
            tarefas_data = [
                {
                    "id": t[0],
                    "titulo": t[1],
                    "descricao": t[2],
                    "nivel": t[3],
                    "xp_base": t[4],
                    "data_vencimento": t[5],
                    "prioridade": t[6],
                    "concluida": t[7],
                    "criada_em": t[8]
                } for t in tarefas
            ]

            # Salvar commit
            cursor.execute(
                "INSERT INTO commits (progresso_data, tarefas_data) VALUES (?, ?)",
                (json.dumps(progresso_data), json.dumps(tarefas_data))
            )
            conn.commit()
            logger.info(f" Commit salvo com sucesso.")

    except Exception as e:
        logger.error(f" Erro ao salvar commit: {e}", exc_info=True)


def carregar_ultimo_commit() -> bool:
    """Carrega o último commit salvo, restaurando progresso e tarefas."""
    import json
    try:
        with _get_db_connection() as conn:
            cursor = conn.cursor()

            # Buscar último commit
            cursor.execute("SELECT progresso_data, tarefas_data FROM commits ORDER BY id DESC LIMIT 1")
            commit = cursor.fetchone()
            if not commit:
                print("Nenhum commit encontrado. Usando estado padrão.")
                return False

            progresso_data, tarefas_data = commit

            # Restaurar progresso
            progresso = json.loads(progresso_data)
            cursor.execute(
                "UPDATE progresso SET nivel = ?, xp_atual = ?, xp_necessario = ?, titulo = ? WHERE id = 1",
                (progresso["nivel"], progresso["xp_atual"], progresso["xp_necessario"], progresso["titulo"])
            )

            # Limpar tarefas atuais e restaurar do commit
            cursor.execute("DELETE FROM tarefas")
            tarefas = json.loads(tarefas_data)
            for tarefa in tarefas:
                cursor.execute(
                    "INSERT INTO tarefas (id, titulo, descricao, nivel, xp_base, data_vencimento, prioridade, concluida, criada_em) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (tarefa["id"], tarefa["titulo"], tarefa["descricao"], tarefa["nivel"], tarefa["xp_base"],
                     tarefa["data_vencimento"], tarefa["prioridade"], tarefa["concluida"], tarefa["criada_em"])
                )

            conn.commit()
            logger.info(f" Ultimo commit carregado com sucesso.")
            return True

    except Exception as e:
        logger.error(f" Erro ao carregar commit: {e}", exc_info=True)
        return False


def adicionar_ao_historico(tarefa_id: int, titulo: str, xp_ganho: int, nivel_dificuldade: int, bonus_temporal: int = 0) -> None:
    """Adiciona tarefa concluída ao histórico."""
    from datetime import datetime
    try:
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            data_conclusao = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                "INSERT INTO historico_tarefas (tarefa_id, titulo, xp_ganho, nivel_dificuldade, bonus_temporal, data_conclusao) VALUES (?, ?, ?, ?, ?, ?)",
                (tarefa_id, titulo, xp_ganho, nivel_dificuldade, bonus_temporal, data_conclusao)
            )
            conn.commit()
    except Exception as e:
        logger.error(f" Erro ao adicionar ao historico: {e}", exc_info=True)


def carregar_historico(limite: int = 50) -> List[Tuple]:
    """Carrega histórico de tarefas concluídas (mais recentes primeiro)."""
    try:
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, titulo, xp_ganho, data_conclusao, nivel_dificuldade, bonus_temporal, tarefa_id FROM historico_tarefas ORDER BY data_conclusao DESC LIMIT ?",
                (limite,)
            )
            return cursor.fetchall()
    except Exception as e:
        logger.error(f" Erro ao carregar historico: {e}", exc_info=True)
        return []


def editar_tarefa(tarefa_id: int, titulo: str = None, nivel: int = None, prioridade: int = None, data_vencimento: str = None, descricao: str = None, attribute_tag: str = None) -> bool:
    """Edita uma tarefa existente. XP é definido automaticamente pelo nível."""
    try:
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            # Buscar tarefa atual
            cursor.execute("SELECT titulo, nivel, xp_base, prioridade, data_vencimento, descricao, attribute_tag FROM tarefas WHERE id = ?", (tarefa_id,))
            resultado = cursor.fetchone()
            if not resultado:
                return False
            novo_titulo = titulo if titulo is not None else resultado[0]
            novo_nivel = nivel if nivel is not None else resultado[1]
            nova_prioridade = prioridade if prioridade is not None else resultado[3]
            nova_data = data_vencimento if data_vencimento is not None else resultado[4]
            nova_descricao = descricao if descricao is not None else resultado[5]
            novo_atributo = attribute_tag if attribute_tag is not None else (resultado[6] if len(resultado) > 6 else 'DEX')
            
            xp_base_auto = 10 * novo_nivel
            cursor.execute(
                "UPDATE tarefas SET titulo = ?, nivel = ?, xp_base = ?, prioridade = ?, data_vencimento = ?, descricao = ?, attribute_tag = ? WHERE id = ?",
                (novo_titulo, novo_nivel, xp_base_auto, nova_prioridade, nova_data, nova_descricao, novo_atributo, tarefa_id)
            )
            conn.commit()
            return True
    except Exception as e:
        logger.error(f" Erro ao editar tarefa: {e}", exc_info=True)
        return False


def carregar_tarefas() -> List[Tuple]:
    """Carrega todas as tarefas ativas (não concluídas)"""
    try:
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, titulo, descricao, nivel, xp_base, data_vencimento, prioridade, concluida, attribute_tag FROM tarefas WHERE concluida = 0 ORDER BY prioridade DESC, criada_em DESC"
            )
            return cursor.fetchall()
    except Exception as e:
        logger.error(f" Erro ao carregar tarefas: {e}", exc_info=True)
        return []


def process_daily_recurrences(current_date: datetime = None) -> None:
    """Renews recurring tasks if today matches their recurrence pattern."""
    if current_date is None:
        current_date = datetime.now()
    
    today_str = current_date.strftime("%Y-%m-%d")
    weekday_str = str(current_date.weekday())  # 0=Monday, ... 6=Sunday
    
    try:
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, recurrence_pattern, last_renewed_date, concluida FROM tarefas WHERE is_recurring = 1")
            
            for task_id, pattern, last_renewed, concluida in cursor.fetchall():
                if pattern and weekday_str in pattern.split(','):
                    # It's a day for this task
                    if last_renewed != today_str:
                        # Needs to be active today (if it was completed previously, it resets. If it wasn't, we just update the renewed date)
                        cursor.execute("UPDATE tarefas SET concluida = 0, last_renewed_date = ? WHERE id = ?", (today_str, task_id))
            conn.commit()
    except Exception as e:
        logger.error(f"Erro ao processar recorrencias: {e}")

def adicionar_tarefa(titulo: str, descricao: str = "", nivel: int = 1, xp_base: int = 10, 
                     data_vencimento: str = None, prioridade: int = 1, attribute_tag: str = "DEX",
                     is_recurring: bool = False, recurrence_pattern: str = None) -> bool:
    """Adiciona uma nova tarefa"""
    try:
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            today_str = datetime.now().strftime("%Y-%m-%d") if is_recurring else None
            cursor.execute(
                "INSERT INTO tarefas (titulo, descricao, nivel, xp_base, data_vencimento, prioridade, attribute_tag, is_recurring, recurrence_pattern, last_renewed_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (titulo, descricao, nivel, xp_base, data_vencimento, prioridade, attribute_tag, 1 if is_recurring else 0, recurrence_pattern, today_str)
            )
            conn.commit()
            return True
    except Exception as e:
        logger.error(f" Erro ao adicionar tarefa: {e}", exc_info=True)
        return False


def deletar_tarefa(tarefa_id: int) -> bool:
    """Remove uma tarefa pelo ID"""
    try:
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            # Apaga tb o histórico associado para não deixar sujeira
            cursor.execute("DELETE FROM historico_tarefas WHERE tarefa_id = ?", (tarefa_id,))
            cursor.execute("DELETE FROM tarefas WHERE id = ?", (tarefa_id,))
            conn.commit()
            return True
    except Exception as e:
        logger.error(f" Erro ao deletar tarefa: {e}", exc_info=True)
        return False


def concluir_tarefa(tarefa_id: int) -> bool:
    """Marca uma tarefa como concluída e distribui pontos de RPG"""
    try:
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Obter detalhes da tarefa para pontos de RPG
            cursor.execute("SELECT attribute_tag, nivel FROM tarefas WHERE id = ?", (tarefa_id,))
            resultado = cursor.fetchone()
            if resultado:
                attr_tag, nivel = resultado
                if attr_tag:
                    adicionar_stat_points(attr_tag, nivel)
                    
            cursor.execute("UPDATE tarefas SET concluida = 1 WHERE id = ?", (tarefa_id,))
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Erro ao concluir tarefa: {e}")
        return False


def restaurar_tarefa(tarefa_id: int) -> bool:
    """Restaura uma tarefa concluída para ativa"""
    try:
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE tarefas SET concluida = 0 WHERE id = ?", (tarefa_id,))
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Erro ao restaurar tarefa: {e}")
        return False


def carregar_progresso() -> Tuple:
    """Carrega dados de progresso do usuário"""
    try:
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, nivel, xp_atual, xp_necessario FROM progresso WHERE id = 1")
            row = cursor.fetchone()
            if row:
                return row
            return (1, 1, 0, 100)
    except Exception as e:
        logger.error(f" Erro ao carregar progresso: {e}", exc_info=True)
        return (1, 1, 0, 100)


def adicionar_xp(xp: int) -> None:
    """Adiciona XP ao usuário"""
    try:
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            # Pega XP atual
            cursor.execute("SELECT xp_atual, xp_necessario, nivel FROM progresso WHERE id = 1")
            row = cursor.fetchone()
            if row:
                xp_atual, xp_nec, nivel = row
                novo_xp = xp_atual + xp
                novo_nivel = nivel
                
                # Verifica se passou de nível
                while novo_xp >= xp_nec:
                    novo_xp -= xp_nec
                    novo_nivel += 1
                    xp_nec = int(xp_nec * 1.2)  # XP necessário aumenta 20% por nível
                
                cursor.execute(
                    "UPDATE progresso SET xp_atual = ?, xp_necessario = ?, nivel = ? WHERE id = 1",
                    (novo_xp, xp_nec, novo_nivel)
                )
                conn.commit()
    except Exception as e:
        logger.error(f" Erro ao adicionar XP: {e}", exc_info=True)


def update_focus_stats(minutes_added: int) -> None:
    """Atualiza estatísticas de foco, streak e acumulado do dia."""
    from datetime import datetime
    try:
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            
            # --- Migração Rápida (Garante que a coluna existe) ---
            try:
                cursor.execute("ALTER TABLE user_stats ADD COLUMN today_focus_minutes INTEGER DEFAULT 0")
            except Exception:
                pass  # Coluna já existe
            # -----------------------------------------------------

            today = datetime.now().strftime("%Y-%m-%d")
            
            cursor.execute("SELECT total_focus_minutes, last_login_date, current_streak, today_focus_minutes FROM user_stats WHERE id=1")
            row = cursor.fetchone()
            
            if row:
                total, last_login, streak, today_mins = row
                # Garante que today_mins não é None
                today_mins = today_mins or 0 
                
                new_total = total + minutes_added
                new_today_mins = today_mins + minutes_added
                new_streak = streak

                if last_login != today:
                    # Novo dia!
                    new_today_mins = minutes_added # Reseta o dia
                    
                    # Lógica de Streak
                    if last_login:
                        try:
                            last = datetime.strptime(last_login, "%Y-%m-%d")
                            diff = (datetime.now() - last).days
                            if diff == 1:
                                new_streak += 1
                            elif diff > 1:
                                new_streak = 1 # Quebrou streak
                        except Exception:
                            new_streak = 1
                    else:
                        new_streak = 1 # Primeiro login

                cursor.execute(
                    "UPDATE user_stats SET total_focus_minutes=?, last_login_date=?, current_streak=?, today_focus_minutes=? WHERE id=1",
                    (new_total, today, new_streak, new_today_mins)
                )
                conn.commit()
    except Exception as e:
        logger.error(f" stats: {e}", exc_info=True)

def get_user_stats() -> Tuple:
    """Retorna (total_minutes, streak, today_minutes)"""
    try:
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            # Tenta pegar coluna nova, se falhar (banco antigo), retorna padrao
            try:
                cursor.execute("SELECT total_focus_minutes, current_streak, today_focus_minutes FROM user_stats WHERE id=1")
                return cursor.fetchone() or (0, 0, 0)
            except Exception:
                # Fallback para banco migrado
                cursor.execute("SELECT total_focus_minutes, current_streak FROM user_stats WHERE id=1")
                row = cursor.fetchone()
                return (row[0], row[1], 0) if row else (0, 0, 0)
    except Exception:
        return (0, 0, 0)

def get_task_stats() -> dict:
    """Retorna estatísticas de tarefas para conquistas."""
    stats = {"total": 0, "today": 0, "urgent": 0}
    try:
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            today = datetime.now().strftime("%Y-%m-%d")
            
            # Total completed
            cursor.execute("SELECT COUNT(*) FROM historico_tarefas")
            stats["total"] = cursor.fetchone()[0]
            
            # Completed today
            cursor.execute("SELECT COUNT(*) FROM historico_tarefas WHERE date(data_conclusao) = ?", (today,))
            stats["today"] = cursor.fetchone()[0]

            # Completed urgent (Nível 4? Não, prioridade. Na tabela tarefas, prioridade=4 é Urgente)
            # Na historico_tarefas não salvamos prioridade explicitamente, mas salvamos nivel_dificuldade.
            # Vamos checar se conseguimos join ou se salvamos. 
            # Ops, historico tem: (tarefa_id, titulo, xp_ganho, nivel_dificuldade, bonus_temporal, data_conclusao)
            # A prioridade não foi para o historico.
            # Workaround: "Caçador de Metas" checará no momento da conclusão.
            
    except Exception as e:
        logger.error(f" get_task_stats: {e}", exc_info=True)
    return stats

def is_achievement_unlocked(code: str) -> bool:
    try:
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM achievements WHERE code=?", (code,))
            return cursor.fetchone() is not None
    except Exception:
        return False

def unlock_achievement(code: str, name: str, desc: str) -> bool:
    """Desbloqueia conquista se ainda não tiver"""
    if is_achievement_unlocked(code):
        return False
    try:
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO achievements (code, name, description) VALUES (?, ?, ?)",
                (code, name, desc)
            )
            conn.commit()
            return True
    except Exception as e:
        logger.error(f" achievement unlock: {e}", exc_info=True)
        return False

def get_unlocked_achievements() -> List[str]:
    """Retorna lista de códigos desbloqueados"""
    try:
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT code FROM achievements")
            return [r[0] for r in cursor.fetchall()]
    except Exception:
        return []


def carregar_whitelist() -> List[str]:
    """Carrega a lista de aplicativos permitidos (whitelist)."""
    try:
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT nome_app FROM whitelist")
            return [row[0] for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Erro ao carregar whitelist: {e}")
        return []


def carregar_apps_neutros() -> List[str]:
    """Carrega a lista de aplicativos neutros."""
    try:
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT nome_app FROM apps_neutros")
            return [row[0] for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Erro ao carregar apps neutros: {e}")
        return []


def salvar_progresso(xp: int, nivel: int, xp_nec: int) -> None:
    """Salva o progresso do usuário (XP, Nível)"""
    try:
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE progresso SET xp_atual = ?, nivel = ?, xp_necessario = ? WHERE id = 1",
                (xp, nivel, xp_nec)
            )
            conn.commit()
    except Exception as e:
        logger.error(f" Erro ao salvar progresso: {e}", exc_info=True)




def notificar_perda_xp(perda: int, atual: int) -> None:
    """Notifica perda de XP (compatibilidade)."""
    # Monitor já faz o feedback visual/sonoro. Esta função existe para manter compatibilidade.
    pass


# ==================== SISTEMA DE MANA (MOEDA) ====================

def adicionar_mana(quantidade: int) -> None:
    """Adiciona Mana (moeda) ao total do jogador.
    
    Args:
        quantidade: Quantidade de Mana a adicionar
    """
    try:
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE progresso SET mana_total = mana_total + ? WHERE id = 1",
                (quantidade,)
            )
            conn.commit()
            print(f"💰 +{quantidade} Mana! Total disponível para gastar.")
    except Exception as e:
        logger.error(f" adicionar_mana: {e}", exc_info=True)


def obter_mana_total() -> int:
    """Retorna o total de Mana disponível do jogador.
    
    Returns:
        Total de Mana (moeda) disponível
    """
    try:
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT mana_total FROM progresso WHERE id = 1")
            result = cursor.fetchone()
            return result[0] if result else 0
    except Exception as e:
        logger.error(f" obter_mana_total: {e}", exc_info=True)
        return 0


def gastar_mana(quantidade: int) -> bool:
    """Gasta Mana (moeda) do jogador.
    
    Args:
        quantidade: Quantidade de Mana a gastar
        
    Returns:
        True se tinha Mana suficiente e gastou, False caso contrário
    """
    try:
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT mana_total FROM progresso WHERE id = 1")
            result = cursor.fetchone()
            mana_atual = result[0] if result else 0
            
            if mana_atual >= quantidade:
                cursor.execute(
                    "UPDATE progresso SET mana_total = mana_total - ? WHERE id = 1",
                    (quantidade,)
                )
                conn.commit()
                print(f"💸 -{quantidade} Mana gasta. Restante: {mana_atual - quantidade}")
                return True
            else:
                print(f"❌ Mana insuficiente! Tem: {mana_atual}, precisa: {quantidade}")
                return False
    except Exception as e:
        logger.error(f" gastar_mana: {e}", exc_info=True)
        return False

# ==================================================================

# ==================== SISTEMA DE INVENTÁRIO ====================

def get_inventory() -> dict:
    """Retorna o inventário completo do jogador.
    
    Returns:
        Dict com {item_code: quantity}
    """
    try:
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT item_code, quantity FROM inventory")
            return {row[0]: row[1] for row in cursor.fetchall()}
    except Exception as e:
        logger.error(f" get_inventory: {e}", exc_info=True)
        return {}


def get_item_quantity(item_code: str) -> int:
    """Retorna a quantidade de um item específico.
    
    Args:
        item_code: Código do item
        
    Returns:
        Quantidade do item
    """
    try:
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT quantity FROM inventory WHERE item_code = ?", (item_code,))
            result = cursor.fetchone()
            return result[0] if result else 0
    except Exception as e:
        logger.error(f" get_item_quantity: {e}", exc_info=True)
        return 0


def add_item(item_code: str, quantity: int = 1) -> bool:
    """Adiciona item ao inventário.
    
    Args:
        item_code: Código do item
        quantity: Quantidade a adicionar
        
    Returns:
        True se sucesso
    """
    try:
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO inventory (item_code, quantity) VALUES (?, 0)", (item_code,))
            cursor.execute(
                "UPDATE inventory SET quantity = quantity + ? WHERE item_code = ?",
                (quantity, item_code)
            )
            conn.commit()
            print(f"📦 +{quantity}x {item_code} adicionado ao inventário")
            return True
    except Exception as e:
        logger.error(f" add_item: {e}", exc_info=True)
        return False


def remove_item(item_code: str, quantity: int = 1) -> bool:
    """Remove item do inventário.
    
    Args:
        item_code: Código do item
        quantity: Quantidade a remover
        
    Returns:
        True se tinha quantidade suficiente e removeu
    """
    try:
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT quantity FROM inventory WHERE item_code = ?", (item_code,))
            result = cursor.fetchone()
            current_qty = result[0] if result else 0
            
            if current_qty >= quantity:
                cursor.execute(
                    "UPDATE inventory SET quantity = quantity - ? WHERE item_code = ?",
                    (quantity, item_code)
                )
                conn.commit()
                print(f"📦 -{quantity}x {item_code} removido do inventário")
                return True
            else:
                print(f"❌ Quantidade insuficiente de {item_code}! Tem: {current_qty}, precisa: {quantity}")
                return False
    except Exception as e:
        logger.error(f" remove_item: {e}", exc_info=True)
        return False


def has_item(item_code: str) -> bool:
    """Verifica se tem pelo menos 1 unidade do item.
    
    Args:
        item_code: Código do item
        
    Returns:
        True se tem pelo menos 1
    """
    return get_item_quantity(item_code) > 0

# ==================== SISTEMA DE EFEITOS ATIVOS ====================

def add_active_effect(item_code: str, duration_minutes: int = None, status: str = 'active') -> bool:
    """Adiciona um efeito ativo (poção)."""
    try:
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO active_effects (item_code, duration_minutes, status) VALUES (?, ?, ?)",
                (item_code, duration_minutes, status)
            )
            conn.commit()
            return True
    except Exception as e:
        logger.error(f" add_active_effect: {e}", exc_info=True)
        return False

def get_active_effects() -> List[dict]:
    """Retorna lista de efeitos ativos válidos."""
    from datetime import datetime, timedelta
    effects = []
    try:
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            # Buscar todos ativos
            cursor.execute("SELECT id, item_code, start_time, duration_minutes, status FROM active_effects WHERE status = 'active'")
            rows = cursor.fetchall()
            
            now = datetime.now()
            
            for row in rows:
                eid, code, start_str, duration, status = row
                
                # Se tem duração, checar se expirou
                if duration is not None:
                    start_time = datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S")
                    end_time = start_time + timedelta(minutes=duration)
                    
                    if now > end_time:
                        # Expirou, marcar como finished
                        cursor.execute("UPDATE active_effects SET status = 'finished' WHERE id = ?", (eid,))
                        continue
                        
                    # Calcular tempo restante em segundos
                    remaining = (end_time - now).total_seconds()
                    effects.append({
                        'code': code,
                        'remaining_seconds': int(remaining),
                        'duration_total': duration
                    })
                else:
                    # Sem duração (efeito permanente ou gatilho imediato que ainda tá marked as active??)
                    # No nosso caso, potion_xp pending vira active com duração no start timer.
                    # Se tiver active sem duração, é ???
                    # Vamos assumir que Potion XP Pending tem status='pending', aqui filtramos status='active'.
                    pass
            
            conn.commit() # Commit para expirados
            
    except Exception as e:
        logger.error(f" get_active_effects: {e}", exc_info=True)
    
    return effects

def get_pending_effects(item_code: str) -> bool:
    """Verifica se tem efeito pendente (ex: Potion XP esperando timer)."""
    try:
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM active_effects WHERE item_code = ? AND status = 'pending'", (item_code,))
            return cursor.fetchone() is not None
    except Exception:
        return False

def activate_pending_effect(item_code: str, duration: int) -> bool:
    """Ativa um efeito pendente (ex: Potion XP ao iniciar timer)."""
    try:
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            # Pega o primeiro pendente
            cursor.execute("SELECT id FROM active_effects WHERE item_code = ? AND status = 'pending' LIMIT 1", (item_code,))
            row = cursor.fetchone()
            if row:
                eid = row[0]
                cursor.execute(
                    "UPDATE active_effects SET status = 'active', start_time = CURRENT_TIMESTAMP, duration_minutes = ? WHERE id = ?",
                    (duration, eid)
                )
                conn.commit()
                return True
    except Exception as e:
        logger.error(f" activate_pending: {e}", exc_info=True)
    return False

def is_effect_active(item_code: str) -> bool:
    """Verifica booleanamente se um efeito está ativo."""
    effects = get_active_effects()
    return any(e['code'] == item_code for e in effects)

# ==================================================================

# ==================== SISTEMA DE STATS (RPG) ====================

def adicionar_stat_points(attribute: str, points: int) -> bool:
    """Adiciona pontos a um atributo específico.
    
    Args:
        attribute: Código do atributo ('INT', 'DEX', 'STR', 'CHA', 'CRI')
        points: Quantidade de pontos a adicionar
        
    Returns:
        True se sucesso
    """
    try:
        # Mapear código para coluna
        column_map = {
            'INT': 'stat_int',
            'DEX': 'stat_dex',
            'STR': 'stat_str',
            'CHA': 'stat_cha',
            'CRI': 'stat_cri'
        }
        
        column = column_map.get(attribute.upper())
        if not column:
            logger.error(f" Atributo inválido: {attribute}", exc_info=True)
            return False
        
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE progresso SET {column} = {column} + ? WHERE id = 1",
                (points,)
            )
            conn.commit()
            print(f"⚡ +{points} pontos de {attribute}!")
            return True
    except Exception as e:
        logger.error(f" adicionar_stat_points: {e}", exc_info=True)
        return False


def get_all_stats() -> dict:
    """Retorna todos os atributos do jogador.
    
    Returns:
        Dict com {'INT': valor, 'DEX': valor, ...}
    """
    try:
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT stat_int, stat_dex, stat_str, stat_cha, stat_cri FROM progresso WHERE id = 1"
            )
            result = cursor.fetchone()
            if result:
                return {
                    'INT': result[0] or 0,
                    'DEX': result[1] or 0,
                    'STR': result[2] or 0,
                    'CHA': result[3] or 0,
                    'CRI': result[4] or 0
                }
            return {'INT': 0, 'DEX': 0, 'STR': 0, 'CHA': 0, 'CRI': 0}
    except Exception as e:
        logger.error(f" get_all_stats: {e}", exc_info=True)
        return {'INT': 0, 'DEX': 0, 'STR': 0, 'CHA': 0, 'CRI': 0}


def get_dominant_attribute() -> tuple:
    """Retorna o atributo dominante e seu valor.
    
    Returns:
        Tupla (attribute_code, value). Ex: ('INT', 25)
    """
    stats = get_all_stats()
    if sum(stats.values()) == 0:
        return ('NONE', 0)
    
    dominant = max(stats, key=stats.get)
    return (dominant, stats[dominant])


def get_character_class() -> tuple:
    """Retorna classe/título baseado nos atributos.
    
    Returns:
        Tupla (título, descrição)
    """
    stats = get_all_stats()
    total = sum(stats.values())
    
    if total == 0:
        return ("Iniciante", "Sua jornada está apenas começando!")
    
    # Verificar se é balanceado
    avg = total / 5
    if all(abs(v - avg) < avg * 0.3 for v in stats.values() if avg > 0):
        return ("Avatar Elemental", "Você domina todas as artes com equilíbrio perfeito.")
    
    # Classes baseadas no atributo dominante
    dominant, value = get_dominant_attribute()
    
    classes = {
        'INT': ("Arquimago Erudito", "Seu poder vem do conhecimento profundo."),
        'DEX': ("Feiticeiro Veloz", "Sua eficiência em projetos é lendária."),
        'STR': ("Mago de Batalha", "Corpo são, mente sã. Você aguenta qualquer tranco."),
        'CHA': ("Bardo Encantador", "Sua magia une as pessoas e resolve conflitos."),
        'CRI': ("Alquimista Criativo", "Você transforma o nada em ideias brilhantes.")
    }
    
    return classes.get(dominant, ("Mago Aprendiz", "Continue sua jornada!"))

# ==================================================================


# ==================== SISTEMA DE POMODORO LOG ====================

def log_pomodoro(duration_minutes: int, was_focus: bool = True) -> bool:
    """
    Registra um pomodoro completado.
    
    Args:
        duration_minutes: Duração em minutos
        was_focus: True se foi sessão de foco, False se foi descanso
        
    Returns:
        True se registrado com sucesso
    """
    try:
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            
            now = datetime.now()
            today = now.strftime("%Y-%m-%d")
            completed_at = now.strftime("%Y-%m-%d %H:%M:%S")
            
            cursor.execute("""
                INSERT INTO pomodoro_log (date, completed_at, duration_minutes, was_focus)
                VALUES (?, ?, ?, ?)
            """, (today, completed_at, duration_minutes, 1 if was_focus else 0))
            
            conn.commit()
            
        print(f"⏱️ Pomodoro registrado: {duration_minutes}min ({'foco' if was_focus else 'descanso'})")
        return True
    except Exception as e:
        logger.error(f" log_pomodoro: {e}", exc_info=True)
        return False


def get_pomodoros_today() -> int:
    """
    Retorna quantidade de pomodoros completados hoje.
    
    Returns:
        Número de pomodoros de foco completados hoje
    """
    try:
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            
            today = datetime.now().strftime("%Y-%m-%d")
            
            cursor.execute("""
                SELECT COUNT(*) FROM pomodoro_log 
                WHERE date = ? AND was_focus = 1 AND completed_at IS NOT NULL
            """, (today,))
            
            return cursor.fetchone()[0]
    except Exception as e:
        logger.error(f" get_pomodoros_today: {e}", exc_info=True)
        return 0

# ======================== SETTINGS SYSTEM =========================

def get_setting(key: str, default: str = None) -> str:
    """
    Retorna o valor de uma configuração.
    
    Args:
        key: Chave da configuração
        default: Valor padrão caso não encontre
    
    Returns:
        Valor da configuração ou default
    """
    try:
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
            result = cursor.fetchone()
            return result[0] if result else default
    except Exception as e:
        logger.error(f" get_setting: {e}", exc_info=True)
        return default

def set_setting(key: str, value: str) -> bool:
    """
    Define o valor de uma configuração.
    Cria ou atualiza a chave existente.
    
    Args:
        key: Chave da configuração
        value: Valor a salvar
    
    Returns:
        True se sucesso, False caso contrário
    """
    try:
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO app_settings (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """, (key, value))
            conn.commit()
            return True
    except Exception as e:
        logger.error(f" set_setting: {e}", exc_info=True)
        return False

# ==================================================================


if __name__ == "__main__":
    iniciar_banco()
