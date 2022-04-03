import datetime as dt
from time import sleep, time

import numpy as np

from .manager import Manager
from .models import Coin, Header, Trade
from .utils import nround


class Strategy:
    def __init__(self, manager: Manager, config: dict) -> None:
        self.manager = manager

        for k, v in config.items():
            setattr(self, k, v)

    def run(self, delay: int = 60) -> None:
        ...


class StrategyDefault(Strategy):
    def __init__(self, manager: Manager, configs: dict) -> None:
        super().__init__(manager, configs)

        try:
            self.descripton = (
                f"Default strategy\n"
                + f"->Buy only when price is {(self.below_average)*100}% below average.\n"
                + f"->Buy only when price is trending up more than {self.trend_up*100}% in the last {self.trend_time} minutes.\n"
                + f"->Sell only when profits more than {self.profit*100}% or when has passed {self.max_days} days."
            )
        except:
            self.descripton = None

    def log_progress(self, diff: float, total_diff: float) -> None:
        if diff > 0:
            diff = f"+{nround(diff, n=2)}"
        else:
            diff = f"-{nround(abs(diff), n=2)}"

        if total_diff > 0:
            total_diff = f"+{nround(total_diff, n=2)}"
        else:
            total_diff = f"-{nround(abs(total_diff), n=2)}"

        self.manager.logger(
            f"Difference: {diff}%\n" + f"Total difference: {total_diff}%"
        )

    def init(self, delay: int):
        activity = Header.get("activity")
        if activity:
            activity = dt.datetime.strptime(activity.evaluate(), "%Y-%m-%d %H:%M:%S")
            diff = self.manager.date - activity
            minutes = (diff.seconds / 60) + (diff.days * 1440)
            if abs(minutes) > 5:
                self.manager.logger("Last activity was more than 5 minutes ago.")
                self.manager.logger("Scouting initial prices...")
                for _ in range(0, self.manager.keep_historic):
                    self.manager.att_price()
                    sleep(delay)

                Header.create_update("epoch", "0", "int")

            else:
                self.manager.logger("Continuing from the last stop.")
                self.manager.logger("Scouting initial prices...")
                coin = Coin.get_tradebles()[0]
                l = len(coin.historic)
                for _ in range(0, self.manager.keep_historic - l):
                    self.manager.att_price()
                    sleep(delay)
             
                Header.create_update("epoch", "0", "int")

        else:
            usdt = self.manager.get_balance("USDT")
            self.manager.logger(self.descripton)
            self.manager.logger("Starting for the first time.")
            self.manager.logger(f"Balance: {usdt}$ USDT")
            self.manager.logger("Scouting initial prices...")
            Header.create_update("start_balance", str(usdt), "float")
            for _ in range(0, self.manager.keep_historic):
                self.manager.att_price()
                sleep(delay)

            Header.create_update("epoch", "0", "int")

    def run(self, delay: int = 60) -> None:
        self.init(delay)
        self.manager.logger("Starting trade...")
        epoch = Header.get("epoch")

        while True:
            started_time = time()

            if not self.manager.att_price():
                self.manager.logger('Finished.')
                break

            scout = Header.get_create("scout", "0", type_="bool")
            if not scout:
                self.try_sell()
                self.try_buy()
                self.stop_lose()

            epoch.set(epoch.evaluate() + 1)

            end_time = time()
            s = delay - (end_time - started_time)
            if s > 0:
                sleep(s)

    def best(self, index: int = 0) -> Coin | None:
        potentials = []
        for coin in Coin.get_tradebles():
            med = sum(coin.historic) / len(coin.historic)
            if coin.price < med * (1 - self.below_average):
                diff = coin.price / coin.historic[-self.trend_time]
                if diff > self.trend_up:
                    potentials.append([coin, diff])

        potentials.sort(key=lambda x: -x[1])

        if len(potentials) >= index + 1:
            return potentials[index][0]

        elif len(potentials) > 0:
            return potentials[-1][0]

        else:
            return None

    def try_buy(self) -> None:
        if len(Trade.select_all()) == 0:
            best = self.best()
            if best:
                bought = False
                self.manager.logger(f"Trying buy {best} ...")

                if self.max_money <= 0:
                    bought = self.manager.buy(best)
                else:
                    usdt = self.manager.get_balance("USDT")
                    if usdt <= self.max_money:
                        bought = self.manager.buy(best)
                    else:
                        quantity = self.max_money / best.price
                        bought = self.manager.buy(best, quantity)

                if not bought:
                    self.manager.logger("Can not buy.")

    def try_sell(self) -> None:
        if len(Trade.select_all()) > 0:
            trade = Trade.select_all()[0]
            coin = Coin.get(trade.coin_symbol)

            best = self.best()
            if best != None and best.symbol == coin.symbol:
                return

            if coin.price > (trade.price * (1 + self.profit)):
                self.manager.logger(f"Trying sell {coin} ...")
                if self.manager.sell(coin):
                    diff = ((coin.price / trade.price) * 100) - 100

                    start_balance = Header.get("start_balance").evaluate()
                    balance = self.manager.get_balance("USDT")
                    total_diff = ((balance / start_balance) * 100) - 100

                    self.log_progress(diff, total_diff)

                else:
                    self.manager.logger("Can not sell.")

    def stop_lose(self) -> None:
        if len(Trade.select_all()) > 0:
            trade = Trade.select_all()[0]
            coin = Coin.get(trade.coin_symbol)
            epoch = Header.get("epoch").evaluate()

            if epoch - trade.age > 1440 * self.max_days:
                if self.manager.sell(coin):
                    diff = ((coin.price / trade.price) * 100) - 100

                    start_balance = Header.get("start_balance").evaluate()
                    balance = self.manager.get_balance("USDT")
                    total_diff = ((balance / start_balance) * 100) - 100

                    self.log_progress(diff, total_diff)

                else:
                    self.manager.logger("Can not sell.")


class StrategyRelative(StrategyDefault):
    def __init__(self, manager: Manager, configs: dict) -> None:
        super().__init__(manager, configs)

        try:
            self.descripton = (
                f"Relative strategy\n"
                + f"->Buy best relative coin from coins list.\n"
                + f"->Sell only when profits more than {self.profit*100}% or when has passed {self.max_days} days."
            )
        except:
            self.descripton = None

    def best(self, index: int = 0):
        potentials = []
        best = None
        for coin in Coin.get_tradebles():
            med = sum(coin.historic[-self.trend_time :]) / self.trend_time
            diff = coin.price / med
            potentials.append([coin, diff])

        potentials.sort(key=lambda x: x[1])
        if len(potentials) > 0:
            best = potentials[-(index + 1)][0]

        return best


class StrategyTrend(StrategyDefault):
    def __init__(self, manager: Manager, configs: dict) -> None:
        super().__init__(manager, configs)

        self.descripton = f"Trend Strategy\n" + ""

    def best(self, index: int = 0) -> None:
        potentials = []
        for coin in Coin.get_tradebles():
            diff = coin.price / coin.historic[-self.trend_time]
            if diff > self.trend_up:
                potentials.append([coin, diff])

        potentials.sort(key=lambda x: -x[1])

        if len(potentials) >= index + 1:
            return potentials[index][0]

        elif len(potentials) > 0:
            return potentials[-1][0]

        else:
            return None

    def try_sell(self) -> None:
        if len(Trade.select_all()) > 0:
            btc = Coin.get("BTC")
            med = sum(btc.historic[-self.btc_trend_days * 1440 :]) / len(
                btc.historic[-self.btc_trend_days * 1440 :]
            )
            diff = btc.price / med
            if diff < self.btc_max_diff:
                return None

            trade = Trade.select_all()[0]
            coin = Coin.get(trade.coin_symbol)

            diff = coin.price / coin.historic[-self.trend_time]
            if diff < 1 - self.trend_down:
                self.manager.logger(f"Trying sell {coin} ...")
                if self.manager.sell(coin):
                    diff = ((coin.price / trade.price) * 100) - 100

                    start_balance = Header.get("start_balance").evaluate()
                    balance = self.manager.get_balance("USDT")
                    total_diff = ((balance / start_balance) * 100) - 100

                    self.log_progress(diff, total_diff)

                else:
                    self.manager.logger("Can not sell.")

    def stop_lose(self) -> None:
        ...


class StrategyML(StrategyDefault):
    def __init__(self, manager: Manager, configs: dict) -> None:
        from .ml import create_model, normilizer

        super().__init__(manager, configs)
        self.model = create_model((self.inputs,))

        checkpoint_path = "ml/cp.ckpt"
        self.model.load_weights(checkpoint_path)
        self.descripton = f"Machine Learning Strategy"

    def try_buy(self) -> None:
        if len(Trade.select_all()) == 0:
            potentials = []
            for coin in Coin.get_tradebles():
                inputs = np.array(coin.historic[-self.inputs :])
                inputs /= max(inputs)
                inputs = inputs.reshape(-1, self.inputs)
                pred = self.model.predict(inputs)[0]
                if np.argmax(pred) == 2:
                    potentials.append([coin, pred[2]])

            potentials.sort(key=lambda x: -x[1])

            if len(potentials) > 0:
                best = potentials[-1][0]

                bought = False
                self.manager.logger(f"Trying buy {best} ...")

                if self.max_money <= 0:
                    bought = self.manager.buy(best)
                else:
                    usdt = self.manager.get_balance("USDT")
                    if usdt <= self.max_money:
                        bought = self.manager.buy(best)
                    else:
                        quantity = self.max_money / best.price
                        bought = self.manager.buy(best, quantity)

                if not bought:
                    self.manager.logger("Can not buy.")

    def try_sell(self) -> None:
        if len(Trade.select_all()) > 0:
            trade = Trade.select_all()[0]
            coin = Coin.get(trade.coin_symbol)

            inputs = np.array(coin.historic[-self.inputs :])
            inputs /= max(inputs)
            inputs = inputs.reshape(-1, self.inputs)

            pred = self.model.predict(inputs)[0]
            if np.argmax(pred) == 1:
                self.manager.logger(f"Trying sell {coin} ...")
                if self.manager.sell(coin):
                    diff = ((coin.price / trade.price) * 100) - 100

                    start_balance = Header.get("start_balance").evaluate()
                    balance = self.manager.get_balance("USDT")
                    total_diff = ((balance / start_balance) * 100) - 100

                    self.log_progress(diff, total_diff)

                else:
                    self.manager.logger("Can not sell.")

    def stop_lose(self) -> None:
        ...
