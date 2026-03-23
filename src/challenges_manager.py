"""
Uppa! - Sistema de Desafios Diários
Gerencia os desafios diários, progresso e recompensas.
"""

import random
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple
from config import get_logger, DAILY_CHALLENGES_POOL, DAILY_CHALLENGES_COUNT

# Logger
logger = get_logger("uppa.challenges")


class ChallengesManager:
    """
    Gerenciador de desafios diários.
    
    Responsável por:
    - Gerar desafios aleatórios do dia
    - Verificar progresso
    - Distribuir recompensas
    """
    
    @staticmethod
    def get_today_challenges() -> List[dict]:
        """
        Retorna os desafios do dia atual.
        Se não existirem, gera novos.
        
        Returns:
            Lista de dicts com os desafios do dia
        """
        from database import _get_db_connection
        
        today = date.today().isoformat()
        
        conn = _get_db_connection()
        cursor = conn.cursor()
        
        # Verificar se já há desafios para hoje
        cursor.execute("""
            SELECT challenge_code, is_completed, claimed 
            FROM daily_challenges 
            WHERE date = ?
        """, (today,))
        
        rows = cursor.fetchall()
        
        if rows:
            # Já tem desafios, retornar com dados completos
            challenges = []
            for row in rows:
                code, is_completed, claimed = row
                challenge_info = ChallengesManager._get_challenge_info(code)
                if challenge_info:
                    challenge_info['is_completed'] = bool(is_completed)
                    challenge_info['claimed'] = bool(claimed)
                    challenges.append(challenge_info)
            conn.close()
            return challenges
        
        # Gerar novos desafios
        conn.close()
        return ChallengesManager._generate_today_challenges()
    
    @staticmethod
    def _generate_today_challenges() -> List[dict]:
        """Gera desafios aleatórios para o dia."""
        from database import _get_db_connection
        
        today = date.today().isoformat()
        
        # Selecionar desafios aleatórios
        selected = random.sample(DAILY_CHALLENGES_POOL, min(DAILY_CHALLENGES_COUNT, len(DAILY_CHALLENGES_POOL)))
        
        conn = _get_db_connection()
        cursor = conn.cursor()
        
        # Inserir novos desafios
        for challenge in selected:
            cursor.execute("""
                INSERT INTO daily_challenges (date, challenge_code, is_completed, claimed)
                VALUES (?, ?, 0, 0)
            """, (today, challenge['code']))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Desafios do dia gerados: {[c['code'] for c in selected]}")
        
        # Retornar com campos extras
        for c in selected:
            c['is_completed'] = False
            c['claimed'] = False
        
        return selected
    
    @staticmethod
    def _get_challenge_info(code: str) -> Optional[dict]:
        """Retorna informações de um desafio pelo código."""
        for c in DAILY_CHALLENGES_POOL:
            if c['code'] == code:
                return c.copy()
        return None
    
    @staticmethod
    def check_progress_all() -> List[Tuple[str, bool]]:
        """
        Verifica o progresso de todos os desafios do dia.
        
        Returns:
            Lista de (challenge_code, was_just_completed)
        """
        from database import _get_db_connection
        
        today = date.today().isoformat()
        now = datetime.now()
        results = []
        
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Buscar desafios não completados
            cursor.execute("""
                SELECT challenge_code FROM daily_challenges
                WHERE date = ? AND is_completed = 0
            """, (today,))
            
            pending = cursor.fetchall()
            
            for (code,) in pending:
                completed = ChallengesManager._check_condition(code, now, conn)
                if completed:
                    cursor.execute("""
                        UPDATE daily_challenges 
                        SET is_completed = 1 
                        WHERE date = ? AND challenge_code = ?
                    """, (today, code))
                    results.append((code, True))
                    logger.info(f"Desafio completado: {code}")
            
            conn.commit()
        
        return results
    
    @staticmethod
    def _check_condition(code: str, now: datetime, conn) -> bool:
        """
        Verifica se a condição de um desafio foi cumprida.
        
        Args:
            code: Código do desafio
            now: Datetime atual
            conn: Conexão com o banco
            
        Returns:
            True se o desafio foi completado
        """
        cursor = conn.cursor()
        today = date.today().isoformat()
        
        if code == "foco_matinal":
            # Pomodoro antes das 10h
            if now.hour >= 10:
                return False  # Passou o horário
            cursor.execute("""
                SELECT COUNT(*) FROM pomodoro_log 
                WHERE date = ? AND completed_at IS NOT NULL 
                AND CAST(strftime('%H', completed_at) AS INTEGER) < 10
            """, (today,))
            count = cursor.fetchone()[0]
            return count >= 1
        
        elif code == "produtivo":
            # 3 tarefas completadas hoje
            cursor.execute("""
                SELECT COUNT(*) FROM historico_tarefas 
                WHERE DATE(data_conclusao) = ?
            """, (today,))
            count = cursor.fetchone()[0]
            return count >= 3
        
        elif code == "maratonista":
            # 2h de foco hoje
            cursor.execute("""
                SELECT SUM(duration_minutes) FROM pomodoro_log 
                WHERE date = ? AND was_focus = 1
            """, (today,))
            row = cursor.fetchone()
            mins = row[0] if row and row[0] else 0
            return mins >= 120
        
        elif code == "impecavel":
            # Nenhuma distração hoje: verificar se houve pomodoros mas nenhuma punição de XP.
            # Proxy: tem pelo menos 1 pomodoro hoje E nenhuma troca de contexto punida.
            # Checamos se fez focus, e se a soma de XP perdido do dia é zero.
            # (Simplificação viável: 1+ pomodoro completado hoje sem nenhuma interrupção registrada)
            cursor.execute("""
                SELECT COUNT(*) FROM pomodoro_log 
                WHERE date = ? AND was_focus = 1
            """, (today,))
            row = cursor.fetchone()
            pomodoros_hoje = row[0] if row else 0
            if pomodoros_hoje == 0:
                return False  # Precisa ter focado pelo menos uma vez
            # Verificar se streak de hoje não foi quebrado (sem puniçoes)
            cursor.execute("SELECT current_streak FROM user_stats WHERE id = 1")
            row = cursor.fetchone()
            streak = row[0] if row else 0
            return streak > 0  # Manteve o streak = não quebrou no dia
        
        elif code == "comecou_bem":
            # 1 tarefa antes das 9h
            if now.hour >= 9:
                return False
            cursor.execute("""
                SELECT COUNT(*) FROM historico_tarefas 
                WHERE DATE(data_conclusao) = ?
                AND CAST(strftime('%H', data_conclusao) AS INTEGER) < 9
            """, (today,))
            count = cursor.fetchone()[0]
            return count >= 1
        
        elif code == "streak_fire":
            # 3 combos no dia (precisa tracking específico)
            # Simplificação: 90+ min de foco implica múltiplos combos
            cursor.execute("""
                SELECT SUM(duration_minutes) FROM pomodoro_log 
                WHERE date = ? AND was_focus = 1
            """, (today,))
            row = cursor.fetchone()
            mins = row[0] if row and row[0] else 0
            return mins >= 90
        
        elif code == "noturno":
            # Pomodoro após 22h
            if now.hour < 22:
                return False  # Ainda não é noite
            cursor.execute("""
                SELECT COUNT(*) FROM pomodoro_log 
                WHERE date = ? AND completed_at IS NOT NULL 
                AND CAST(strftime('%H', completed_at) AS INTEGER) >= 22
            """, (today,))
            count = cursor.fetchone()[0]
            return count >= 1
        
        elif code == "focus_total":
            # 4 pomodoros no dia
            cursor.execute("""
                SELECT COUNT(*) FROM pomodoro_log 
                WHERE date = ? AND completed_at IS NOT NULL
            """, (today,))
            count = cursor.fetchone()[0]
            return count >= 4
        
        return False
    
    @staticmethod
    def claim_reward(code: str) -> Tuple[int, int]:
        """
        Reivindica a recompensa de um desafio completado.
        
        Args:
            code: Código do desafio
            
        Returns:
            (xp_ganho, mana_ganha) ou (0, 0) se já reivindicado
        """
        from database import _get_db_connection, adicionar_xp, adicionar_mana
        
        today = date.today().isoformat()
        
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Verificar se completou e não reivindicou
            cursor.execute("""
                SELECT is_completed, claimed FROM daily_challenges
                WHERE date = ? AND challenge_code = ?
            """, (today, code))
            
            row = cursor.fetchone()
            
            if not row:
                return (0, 0)
            
            is_completed, claimed = row
            
            if not is_completed or claimed:
                return (0, 0)
            
            # Buscar recompensas
            challenge_info = ChallengesManager._get_challenge_info(code)
            if not challenge_info:
                return (0, 0)
            
            xp_reward = challenge_info.get('xp_reward', 0)
            mana_reward = challenge_info.get('mana_reward', 0)
            
            # Marcar como reivindicado
            cursor.execute("""
                UPDATE daily_challenges 
                SET claimed = 1 
                WHERE date = ? AND challenge_code = ?
            """, (today, code))
            
            conn.commit()
            
        # Dar recompensas
        if xp_reward > 0:
            adicionar_xp(xp_reward)
        if mana_reward > 0:
            adicionar_mana(mana_reward)
        
        logger.info(f"Recompensa reivindicada: {code} (+{xp_reward} XP, +{mana_reward} Mana)")
        
        return (xp_reward, mana_reward)
    
    @staticmethod
    def get_daily_summary() -> Dict:
        """
        Retorna um resumo dos desafios do dia.
        
        Returns:
            Dict com total, completed, claimed
        """
        challenges = ChallengesManager.get_today_challenges()
        
        return {
            'total': len(challenges),
            'completed': sum(1 for c in challenges if c.get('is_completed')),
            'claimed': sum(1 for c in challenges if c.get('claimed')),
            'challenges': challenges
        }


# Teste
if __name__ == "__main__":
    from database import iniciar_banco
    
    print("🎯 Testando ChallengesManager...\n")
    
    iniciar_banco()
    
    # Gerar/buscar desafios do dia
    print("📋 Desafios do Dia:")
    challenges = ChallengesManager.get_today_challenges()
    for c in challenges:
        status = "✅" if c.get('is_completed') else "⬜"
        claimed = "🎁" if c.get('claimed') else ""
        print(f"  {status} {c['name']} - {c['description']} {claimed}")
    
    # Resumo
    print("\n📊 Resumo:")
    summary = ChallengesManager.get_daily_summary()
    print(f"  Total: {summary['total']}")
    print(f"  Completados: {summary['completed']}")
    print(f"  Reivindicados: {summary['claimed']}")
    
    print("\n✅ Teste concluído!")
