from traceback import print_exc

from modules.config import COINS, STRATEGY
from modules.logger import Logger
from modules.manager import ManagerHistoricalBacktest
from modules.strategy import StrategyRelative as Strategy

configs = STRATEGY["relative"]

logger = Logger("./logs/log.txt")

manager = ManagerHistoricalBacktest(
    logger=logger,
    coins_symbols=COINS,
    database_historic="data/crypto_historic.db",
    start_date="2020-10-01 00:00:00",
    end_date="2022-01-17 00:00:00",
    summary_fname="backtest/summary.json",
    usdt_quantity=100,
    fee=0.075,
    keep_historic=1440,
    minutes_steps=1,
)

strategy = Strategy(manager, configs)

try:
    strategy.run(delay=0)
except:
    print_exc()
    manager.save_summary()

    from modules.models import cache

    for c in cache:
        for i in cache[c]:
            print(i)
        print()
