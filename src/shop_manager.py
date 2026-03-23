"""
ShopManager - Gerenciador da Loja de Consumíveis do Uppa!
"""
from typing import Dict, Optional
from database import (
    obter_mana_total, gastar_mana, 
    add_item, remove_item, has_item, get_inventory,
    adicionar_mana
)
from sound_manager import get_audio_manager


class ShopManager:
    """
    Gerenciador da loja de consumíveis.
    
    Responsável por:
    - Catálogo de itens
    - Lógica de compra
    - Validações
    """
    
    # Catálogo de itens da loja
    CATALOG: Dict[str, dict] = {
        'potion_focus': {
            'name': 'Poção de Foco',
            'description': 'Imunidade a perda de mana por 15 minutos',
            'price': 60,
            'icon': '🧪',
            'effect': 'Escudo contra distrações por 15min'
        },
        'potion_xp': {
            'name': 'Poção de XP',
            'description': 'Dobra todo XP ganho no próximo Pomodoro',
            'price': 120,
            'icon': '⚗️',
            'effect': '2x XP no próximo ciclo completo'
        },
        'hourglass': {
            'name': 'Ampulheta Temporal',
            'description': 'Adiciona 5 minutos ao descanso atual',
            'price': 150,  # ITEM MAIS CARO - Muito valioso!
            'icon': '⏳',
            'effect': '+5min no intervalo'
        }
    }
    
    @staticmethod
    def get_catalog() -> Dict[str, dict]:
        """Retorna o catálogo completo da loja."""
        return ShopManager.CATALOG.copy()
    
    @staticmethod
    def get_item_info(item_code: str) -> Optional[dict]:
        """Retorna informações de um item específico."""
        return ShopManager.CATALOG.get(item_code)
    
    @staticmethod
    def buy_item(item_code: str) -> bool:
        """
        Compra um item da loja.
        
        Args:
            item_code: Código do item a comprar
            
        Returns:
            True se comprou com sucesso, False caso contrário
        """
        # Verificar se item existe
        item = ShopManager.CATALOG.get(item_code)
        if not item:
            print(f"❌ Item '{item_code}' não existe na loja!")
            return False
        
        # Verificar se tem Mana suficiente
        mana_atual = obter_mana_total()
        preco = item['price']
        
        if mana_atual < preco:
            print(f"❌ Mana insuficiente! Tem: {mana_atual}, precisa: {preco}")
            return False
        
        # Gastar mana
        if not gastar_mana(preco):
            return False
        
        # Adicionar item ao inventário
        if add_item(item_code, 1):
            print(f"✅ {item['icon']} {item['name']} comprado com sucesso!")
            
            # Tocar som de compra
            audio = get_audio_manager()
            audio.play_sfx('task_complete')  # Usar som de sucesso
            
            return True
        else:
            # Reverter gasto de mana se falhou ao adicionar item
            adicionar_mana(preco)
            print(f"❌ Erro ao adicionar item ao inventário. Mana devolvida.")
            return False
    
    @staticmethod
    def can_afford(item_code: str) -> bool:
        """Verifica se o jogador pode comprar o item."""
        item = ShopManager.CATALOG.get(item_code)
        if not item:
            return False
        
        return obter_mana_total() >= item['price']
    
    @staticmethod
    def get_price(item_code: str) -> int:
        """Retorna o preço de um item."""
        item = ShopManager.CATALOG.get(item_code)
        return item['price'] if item else 0


# Teste
if __name__ == "__main__":
    from database import iniciar_banco, adicionar_mana
    
    print("🛒 Testando ShopManager...\n")
    
    # Inicializar banco
    iniciar_banco()
    
    # Adicionar mana para teste
    adicionar_mana(100)
    
    # Testar catálogo
    print("📋 Catálogo da Loja:")
    for code, item in ShopManager.get_catalog().items():
        print(f"  {item['icon']} {item['name']} - {item['price']} Mana")
        print(f"     {item['description']}")
    
    # Testar compra
    print("\n💸 Tentando comprar Ampulheta...")
    success = ShopManager.buy_item('hourglass')
    print(f"Resultado: {'✅ Sucesso' if success else '❌ Falha'}")
    
    # Verificar inventário
    print("\n📦 Inventário:")
    inv = get_inventory()
    for item_code, qty in inv.items():
        if qty > 0:
            item_info = ShopManager.get_item_info(item_code)
            if item_info:
                print(f"  {item_info['icon']} {item_info['name']}: {qty}x")
    
    print("\n✅ Testes concluídos!")
