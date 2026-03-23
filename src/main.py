"""
Uppa! - Seu Mascote de Produtividade
Arquivo de entrada principal
"""

import sys
import traceback

def main():
    """Função principal - entry point do app"""
    
    # 1. Tentar fechar splash imediatamente para garantir que não trave
    try:
        import pyi_splash # type: ignore
        pyi_splash.close()
    except ImportError:
        pass

    try:
        # 2. Inicializar logging PRIMEIRO (antes de qualquer import)
        from config import setup_logging, get_logger
        logger = setup_logging()
        logger.info("=" * 50)
        logger.info("Uppa! Iniciando...")
        
        # 3. Importações tardias para evitar travamento no import
        # Se database ou gui derem erro no import (comuns em builds),
        # agora conseguimos pegar o erro.
        from database import iniciar_banco
        from gui import UppaApp
        
        logger.info("Módulos carregados com sucesso")
        
        # 4. Iniciar banco de dados
        iniciar_banco()
        logger.info("Banco de dados inicializado")
        
        # 5. Criar e rodar app
        logger.info("Iniciando interface gráfica...")
        app = UppaApp()
        app.mainloop()
        
        logger.info("Uppa! encerrado normalmente")

    except Exception as e:
        # Log do erro para debug
        error_msg = f"Ocorreu um erro ao iniciar o Uppa:\n\n{str(e)}\n\n{traceback.format_exc()}"
        
        # Tentar logar o erro
        try:
            from config import get_logger
            logger = get_logger()
            logger.error(f"Erro fatal: {e}", exc_info=True)
        except Exception:
            pass
        
        print(error_msg)
        
        # Tentar mostrar popup nativo do Windows (já que o GUI pode ter falhado)
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, error_msg, "Erro Fatal - Uppa", 0x10) # 0x10 = Icon Error
        except Exception:
            pass
        
        sys.exit(1)

if __name__ == "__main__":
    main()
