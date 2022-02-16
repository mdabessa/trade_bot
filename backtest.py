from traceback import print_exc

from modules.logger import Logger 
from modules.manager import ManagerHistoricalBacktest
from modules.strategy import StrategyDefault


configs = {
    'below_average': 0.07,
    'trend_up': 0.01,
    'trend_time': 1440,
    'profit': 0.02,
    'max_days': 3,
    'max_money': 100,
    'btc_max_diff': 0.94,
    'btc_trend_days': 4,
}

logger = Logger('./logs/log.txt')

manager = ManagerHistoricalBacktest(
    logger=logger,
    coins_symbols=['BTC', 'ETH', 'NEO'],
    database_historic='data/crypto_historic.db',
    start_date='2020-10-01 00:00:00',
    end_date='2022-01-17 00:00:00', 
    summary_fname='backtest/summary.json',
    usdt_quantity=100, 
    fee=0.075,
    keep_historic=1440*4
)

strategy = StrategyDefault(manager, configs)

try:
    strategy.run(delay=0)
except:
    print_exc()
    manager.save_summary()
