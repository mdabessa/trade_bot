import os
import sys

sys.path.append(os.path.join(os.path.dirname(sys.path[0])))

from modules.models import Header


scout = Header.get("scout")
print(f"Scout: {scout.evaluate()}")
scout.set("0")
print(f"Scout: {scout.evaluate()}")
