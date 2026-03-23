import re

path = 'src/database.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace print(f"[ERRO] ...")
content = re.sub(r'print\(\s*f?\"\[ERRO\](.*?)\"\s*\)', r'logger.error(f"\1", exc_info=True)', content)

# Replace print("[ERRO] ...")
content = re.sub(r'print\(\s*\"\[ERRO\](.*?)\"\s*\)', r'logger.error("\1", exc_info=True)', content)

# Replace print(f"✗ ...")
content = re.sub(r'print\(\s*f?\"✗(.*?)\"\s*\)', r'logger.error(f"\1", exc_info=True)', content)

# Replace print(f"[OK] ...")
content = re.sub(r'print\(\s*f?\"\[OK\](.*?)\"\s*\)', r'logger.info(f"\1")', content)

# Replace print(f"✓ ...")
content = re.sub(r'print\(\s*f?\"✓(.*?)\"\s*\)', r'logger.info(f"\1")', content)

# General print() inside except blocks
content = re.sub(r'except Exception as e:\n(\s*)print\((.*?)\)', r'except Exception as e:\n\1logger.error(\2, exc_info=True)', content)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print('Done!')
