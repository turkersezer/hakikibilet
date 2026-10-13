import shutil
import os
from datetime import datetime

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_dir = os.path.join(os.getcwd(), "backups", f"backup_{timestamp}")
os.makedirs(backup_dir, exist_ok=True)

items = ["app", "data", "run.py", "requirements.txt"]
for item in items:
    if os.path.exists(item):
        dest_path = os.path.join(backup_dir, item)
        if os.path.isdir(item):
            shutil.copytree(item, dest_path, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dest_path)

print(f"SUCCESS: System backup created at {backup_dir}")
