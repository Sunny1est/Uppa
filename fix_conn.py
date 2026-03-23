import re

path = 'src/database.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Update _get_db_connection to add timeout
content = content.replace(
    'return sqlite3.connect(DB_FILE)',
    'return sqlite3.connect(DB_FILE, timeout=10.0)'
)

# Standardize with sqlite3.connect(DB_FILE) as conn: -> with _get_db_connection() as conn:
content = content.replace(
    'with sqlite3.connect(DB_FILE) as conn:',
    'with _get_db_connection() as conn:'
)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print('Done connection fix!')
