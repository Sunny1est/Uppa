
import sqlite3
import os

# Use a test database file
TEST_DB = "test_uppa_data.db"

if os.path.exists(TEST_DB):
    os.remove(TEST_DB)

def setup_db():
    conn = sqlite3.connect(TEST_DB)
    cursor = conn.cursor()
    # Create inventory table but DO NOT insert items
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_code TEXT UNIQUE NOT NULL,
            quantity INTEGER DEFAULT 0
        )
        """
    )
    conn.commit()
    conn.close()

def add_item_buggy(item_code: str, quantity: int = 1) -> bool:
    """Simulates the current buggy implementation"""
    try:
        with sqlite3.connect(TEST_DB) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE inventory SET quantity = quantity + ? WHERE item_code = ?",
                (quantity, item_code)
            )
            # CHECK: In the current code, we don't check rowcount here.
            # We just commit and return True.
            conn.commit()
            
            # For reproduction verification, we check if it was actually added
            if cursor.rowcount == 0:
                print(f"[BUG REPRO] Update affected 0 rows for {item_code}")
            else:
                print(f"[SUCCESS] Update affected {cursor.rowcount} rows")
                
            return True
    except Exception as e:
        print(f"[ERRO] add_item: {e}")
        return False

def check_inventory():
    with sqlite3.connect(TEST_DB) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM inventory")
        rows = cursor.fetchall()
        print("Inventory dump:", rows)
        return len(rows)

if __name__ == "__main__":
    setup_db()
    
    print("Trying to add 'hourglass' which is NOT in the table...")
    result = add_item_buggy('hourglass', 1)
    print(f"Function returned: {result}")
    
    count = check_inventory()
    if count == 0 and result is True:
        print("\n!!! BUG REPRODUCED !!!")
        print("Function returned True (success) but item was NOT added to inventory.")
    else:
        print("\nCannot reproduce bug.")
