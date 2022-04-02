import os
import sys

sys.path.append(os.path.join(os.path.dirname(sys.path[0])))

from modules.manager import ManagerBinance
from modules.logger import Logger
from modules.config import API_KEY, API_SECRET, COINS

logger = Logger("./logs/log.txt")

manager = ManagerBinance(
    logger=logger,
    coins_symbols=COINS,
    api_key=API_KEY,
    api_secret=API_SECRET,
    keep_historic=1440,
)


quantity = manager.get_balance("USDT")
print(quantity)
