import datetime as dt
import json
import sqlite3 as sql
from time import sleep

from binance import Client

from .logger import Logger
from .models import Balance, Coin, Header, Trade
from .utils import IdGenerator, TimeCount, nround


class Manager:
    def __init__(self, logger: Logger) -> None:
        self.logger = logger

        scout = Header.get_create(key="scout", value="0", type_="int")

    def buy(self, coin: Coin, quantity: float = -1) -> bool:
        ...

    def sell(self, coin: Coin, quantity: float = -1) -> bool:
        ...

    def att_price(self) -> None:
        ...

    def get_balance(self, symbol: str) -> float:
        ...


class ManagerBacktest(Manager):
    def __init__(
        self,
        logger: Logger,
        coins_symbols: list,
        usdt_quantity: float = 100.0,
        fee: float = 0.1,
        keep_historic: int = 1440,
    ) -> None:
        super().__init__(logger)
        self.keep_historic = keep_historic

        usdt = Coin.get_create("USDT", 1, keep_historic, "0.00000001")
        Balance.get_create(usdt, usdt_quantity, fee)

        for symbol in coins_symbols:
            coin = Coin.get_create(symbol, 0, keep_historic, "0.00000001")
            Balance.get_create(coin, 0, fee)

    def buy(self, coin: Coin, quantity: float = -1) -> bool:
        usdt = Coin.get("USDT")
        usdt_balance = Balance.get(usdt)
        if quantity <= 0:
            quantity = usdt_balance.quantity / coin.price

        quantity = float(coin.quantity_lot_size(quantity))
        Balance.buy(coin, quantity)
        balance = Balance.get(coin)
        self.logger(
            f"{quantity} {coin.symbol} bought at {coin.price}!\n- {quantity * coin.price} USDT\nFee: {quantity*(balance.fee/100)} {coin.symbol}"
        )
        return True

    def sell(self, coin: Coin, quantity: float = -1) -> bool:
        balance = Balance.get(coin)
        if quantity <= 0:
            quantity = balance.quantity

        quantity = float(coin.quantity_lot_size(quantity))
        Balance.sell(coin, quantity)
        self.logger(
            f"{quantity} {coin.symbol} sold at {coin.price}!\n+ {quantity * coin.price} USDT\nFee: {(quantity*coin.price)*(balance.fee/100)} USDT"
        )
        return True


class ManagerHistoricalBacktest(ManagerBacktest):
    def __init__(
        self,
        logger: Logger,
        coins_symbols: list,
        database_historic: str,
        start_date: str,
        end_date: str,
        summary_fname: str,
        usdt_quantity: float = 100,
        fee: float = 0.1,
        keep_historic: int = 1440,
        minutes_steps: int = 1,
    ) -> None:

        super().__init__(logger, coins_symbols, usdt_quantity, fee, keep_historic)

        self.summary = {
            "daily_close": [],
            "daily_close_btc": [],
            "orders_historic": [],
        }
        self.summary_fname = summary_fname
        self.database_historic = sql.connect(database_historic)
        self.simulation_time = TimeCount()
        self.date = ""
        self.minutes_steps = minutes_steps

        id_marc = Header.get_create("id_marc", "0", "int")
        self.gen_id = IdGenerator(id_marc.evaluate())

        activity = Header.get("activity")
        if activity == None:
            self.date = dt.datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
        else:
            self.date = dt.datetime.strptime(activity.evaluate(), "%Y-%m-%d %H:%M:%S")

        self.end_date = dt.datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S")

        self.price_history = {}
        for coin in coins_symbols:
            cursor = self.database_historic.cursor()
            cursor.execute(
                f"""
                SELECT date, open FROM {coin}
                WHERE date BETWEEN '{self.date}' AND '{self.end_date}'
            """
            )

            r = cursor.fetchall()

            self.price_history[coin] = dict(r)

    def buy(self, coin: Coin, quantity: float = -1) -> bool:
        r = super().buy(coin, quantity)
        if r:
            epoch = Header.get("epoch").evaluate()
            id_marc = Header.get("id_marc")
            trade = Trade(coin=coin, price=coin.price, age=epoch, id=id_marc.evaluate())
            id_marc.set(self.gen_id())

            order = {
                "id": trade.id,
                "date": str(self.date),
                "epoch": epoch,
                "type": "buy",
                "symbol": coin.symbol,
                "price": coin.price,
            }

            self.summary["orders_historic"].append(order)

        return r

    def sell(self, coin: Coin, quantity: float = -1) -> bool:
        r = super().sell(coin, quantity)
        if r:
            epoch = Header.get("epoch").evaluate()

            trade = Trade.get(coin)

            order = {
                "id": trade.id,
                "date": str(self.date),
                "epoch": epoch,
                "type": "sell",
                "symbol": coin.symbol,
                "price": coin.price,
            }

            self.summary["orders_historic"].append(order)
            trade.delete()
        return r

    def att_price(self) -> None:
        self.date += dt.timedelta(minutes=self.minutes_steps)
        if self.date >= self.end_date:
            for trade in Trade.select_all():
                coin = Coin.get(trade.coin_symbol)
                self.sell(coin)

            self.summary["final_wallet"] = Balance.to_dict()
            self.save_summary()

            self.logger("Finished.")
            self.logger(
                f"Total simulation time: {nround(self.simulation_time.total())} secs"
            )
            return False

        if self.date.strftime("%H:%M") == "00:00":
            self.logger(f"Date: {self.date}")
            self.logger(f"Simulation: 1 day = {nround(self.simulation_time())} seconds")
            self.summary["daily_close"].append(self.estimate_balance())
            self.summary["daily_close_btc"].append(self.estimate_balance_btc())

        for coin in Coin.select_all():
            price = self.get_price(coin)
            coin.set_price(float(price))

        activity = Header.get_create("activity", str(self.date), "str")
        activity.set(self.date)
        return True

    def get_price(self, coin: Coin) -> float:
        try:
            price = self.price_history[coin.symbol][str(self.date)]
            return price
        except:
            return coin.price

    def estimate_balance(self) -> float:
        value = 0
        for coin in Coin.select_all():
            value += coin.price * Balance.get(coin).quantity

        return value

    def estimate_balance_btc(self) -> None:
        value = self.estimate_balance()
        btc = Coin.get("BTC")

        return value / btc.price

    def save_summary(self) -> None:
        with open(self.summary_fname, "w") as f:
            json.dump(self.summary, f, indent=4)

    def get_balance(self, symbol: str) -> float:
        return float(Balance.get(Coin.get(symbol)).quantity)


class ManagerBinance(Manager):
    def __init__(
        self,
        logger: Logger,
        coins_symbols: list,
        api_key: str,
        api_secret: str,
        keep_historic: int = 1440,
    ) -> None:

        super().__init__(logger)

        self.client = Client(api_key=api_key, api_secret=api_secret)
        self.keep_historic = keep_historic
        self.date = dt.datetime.today()
        id_marc = Header.get_create("id_marc", "0", "int")
        self.gen_id = IdGenerator(id_marc.evaluate())

        for symbol in coins_symbols:
            pair = symbol.upper() + "USDT"
            price = float(self.client.get_margin_price_index(symbol=pair)["price"])

            filters = self.client.get_symbol_info(pair)["filters"]
            lot_size = list(filter(lambda x: x["filterType"] == "LOT_SIZE", filters))[
                0
            ]["stepSize"]

            Coin.get_create(symbol.upper(), price, keep_historic, lot_size)

    def buy(self, coin: Coin, quantity: float = -1) -> bool:
        pair = coin.symbol + "USDT"
        usdt_balance = self.get_balance("USDT")

        if quantity <= 0:
            quantity = usdt_balance / coin.price

        quantity = coin.quantity_lot_size(quantity)

        response = self.client.order_market_buy(symbol=pair, quantity=str(quantity))

        commission = 0
        for f in response["fills"]:
            commission += float(f["commission"])

        self.logger(
            f'{response["executedQty"]} {coin.symbol} bought at {coin.price}!\n'
            + f"- {float(quantity) * coin.price} USDT\n"
            + f'Fee: {commission} {response["fills"][0]["commissionAsset"]}'
        )

        epoch = Header.get("epoch").evaluate()
        id_marc = Header.get("id_marc")

        Trade(coin=coin, price=coin.price, age=epoch, id=id_marc.evaluate())
        id_marc.set(self.gen_id())

        return True

    def sell(self, coin: Coin, quantity: float = -1) -> bool:
        pair = coin.symbol + "USDT"

        if quantity <= 0:
            quantity = self.get_balance(coin.symbol)

        quantity = coin.quantity_lot_size(quantity)

        response = self.client.order_market_sell(symbol=pair, quantity=str(quantity))

        commission = 0
        for f in response["fills"]:
            commission += float(f["commission"])

        self.logger(
            f'{response["executedQty"]} {coin.symbol} sold at {coin.price}!\n'
            + f"+ {float(quantity) * coin.price} USDT\n"
            + f'Fee: {commission} {response["fills"][0]["commissionAsset"]}'
        )

        trade = Trade.get(coin)
        trade.delete()

        return True

    def att_price(self) -> None:
        self.date = dt.datetime.today()
        date = self.date.strftime("%Y-%m-%d %H:%M:%S")

        if self.date.strftime("%H:%M") == "00:00":
            self.logger.log(f"Date: {date}")

        for coin in Coin.get_tradebles():
            pair = coin.symbol + "USDT"
            price = float(self.client.get_margin_price_index(symbol=pair)["price"])
            coin.set_price(price)

        Header.create_update("activity", str(date))
        return True

    def get_balance(self, symbol: str) -> float:
        infos = self.client.get_account()
        sleep(0.5)
        c = filter(lambda x: x["asset"] == symbol, infos["balances"])
        return float(list(c)[0]["free"])


class ManagerPaperTradeBinance(ManagerBinance):
    def __init__(
        self,
        logger: Logger,
        coins_symbols: list,
        api_key: str,
        api_secret: str,
        usdt_quantity: float = 100,
        fee: float = 0.1,
        keep_historic: int = 1440,
    ) -> None:
        super().__init__(logger, coins_symbols, api_key, api_secret, keep_historic)

        usdt = Coin.get_create("USDT", 1, keep_historic, "0.00000001")
        Balance.get_create(usdt, usdt_quantity, fee)

        for symbol in coins_symbols:
            coin = Coin.get_create(symbol, 0, keep_historic, "0.00000001")
            Balance.get_create(coin, 0, fee)

    def buy(self, coin: Coin, quantity: float = -1) -> bool:
        r = super().buy(coin, quantity)
        if r:
            epoch = Header.get("epoch").evaluate()
            id_marc = Header.get("id_marc")
            trade = Trade(coin=coin, price=coin.price, age=epoch, id=id_marc.evaluate())
            id_marc.set(self.gen_id())

            order = {
                "id": trade.id,
                "date": str(self.date),
                "epoch": epoch,
                "type": "buy",
                "symbol": coin.symbol,
                "price": coin.price,
            }

            self.summary["orders_historic"].append(order)

        return r

    def sell(self, coin: Coin, quantity: float = -1) -> bool:
        r = super().sell(coin, quantity)
        if r:
            epoch = Header.get("epoch").evaluate()

            trade = Trade.get(coin)

            order = {
                "id": trade.id,
                "date": str(self.date),
                "epoch": epoch,
                "type": "sell",
                "symbol": coin.symbol,
                "price": coin.price,
            }

            self.summary["orders_historic"].append(order)
            trade.delete()
        return r
