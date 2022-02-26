from decimal import Decimal

from matplotlib.pyplot import hist
from sqlalchemy import (Column, Float, ForeignKey, Integer, String,
                        create_engine)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

from .config import DATABASE_URL

if DATABASE_URL:
    engine = create_engine(DATABASE_URL, echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()

else:
    session = None


cache = {}
Base = declarative_base()


class ModelCache:
    def __init__(self, **data) -> None:
        for key, val in data.items():
            setattr(self, key, val)

        cache[self.__class__.__name__].append(self)

    def delete(self):
        cache[self.__class__.__name__].remove(self)

    def update(self):
        ...

    @classmethod
    def select(cls, key: str, value: str) -> list:
        objs = list(
            filter(lambda x: getattr(x, key) == value, cache[cls.__name__])
        )
        return objs

    @classmethod
    def select_one(cls, key: str, value):
        try:
            obj = list(
                filter(lambda x: getattr(x, key) == value, cache[cls.__name__])
            )[0]
            return obj

        except IndexError:
            return None

    @classmethod
    def select_all(cls) -> list:
        return cache[cls.__name__]


class ModelORM(Base):
    __abstract__ = True

    def __init__(self, **data) -> None:
        super().__init__(**data)

        session.add(self)
        self.update()

    def delete(self):
        session.delete(self)
        self.update()

    def update(self):
        session.commit()

    @classmethod
    def select(cls, key: str, value: str) -> list:
        return session.query(cls).filter(getattr(cls, key) == value).all()

    @classmethod
    def select_one(cls, key: str, value):
        return session.query(cls).filter(getattr(cls, key) == value).first()

    @classmethod
    def select_all(cls) -> list:
        return session.query(cls).all()


if session:
    Model = ModelORM
else:
    Model = ModelCache


class Header(Model):
    if session:
        __tablename__ = 'headers'
        key = Column(String, primary_key=True)
        value = Column(String, nullable=False)
        type_ = Column(String, nullable=False)
    else:
        cache['Header'] = []

    def __init__(self, key: str, value: str, type_: str = 'str') -> None:
        super().__init__(key=str(key), value=str(value), type_=str(type_))

    def set(self, value):
        self.value = str(value)
        self.update()

    def evaluate(self):
        value = eval(self.type_ + f'("{self.value}")')
        return value

    def __bool__(self) -> bool:
        return bool(self.evaluate())

    def __repr__(self) -> str:
        return (
            f'Header(key={self.key}, value={self.value}, type_={self.type_})'
        )

    @classmethod
    def get(cls, key: str):
        return cls.select_one('key', key)

    @classmethod
    def get_create(cls, key: str, value: str, type_: str):
        header = cls.get(key)
        if header == None:
            header = Header(key=str(key), value=str(value), type_=str(type_))

        return header

    @classmethod
    def create_update(cls, key: str, value: str, type_: str):
        header = cls.get(key)
        if header == None:
            header = Header(key=str(key), value=str(value), type_=str(type_))
        else:
            header.set(value)

        return header


class Coin(Model):
    if session:
        __tablename__ = 'coins'
        symbol = Column(String, primary_key=True)
        price = Column(Float, default=0.0, nullable=False)
        historic = Column(ARRAY(Float), default=[])
        keep_historic = Column(Integer, default=50, nullable=False)
        lot_size = Column(String, default='0.001', nullable=False)
        trades = relationship('Trade', back_populates='coin')
        balance = relationship('Balance', back_populates='coin', uselist=False)
    else:
        cache['Coin'] = []

    def __init__(
        self,
        symbol: str,
        price: float,
        historic: list = None,
        keep_historic: int = 50,
        lot_size: str = '0.001',
    ) -> None:
        super().__init__(
            symbol=str(symbol),
            price=float(price),
            historic=historic,
            keep_historic=int(keep_historic),
            lot_size=str(lot_size),
        )

    def set_price(self, price: float) -> None:
        self.price = price
        self.update()
        self.add_historic(price)

    def add_historic(self, price: float) -> None:
        if self.historic == None:
            self.historic = []

        historic = self.historic.copy()
        historic.append(price)
        while len(historic) > self.keep_historic:
            historic.pop(0)

        self.historic = historic
        self.update()

    def quantity_lot_size(self, quantity: float) -> str:
        if float(self.lot_size) == 1:
            _qtd = int(quantity)
        else:
            q = Decimal(quantity - float(self.lot_size))
            try:
                _qtd = q.quantize(Decimal(str(float(self.lot_size))))
            except:
                print(self.lot_size)
                print(quantity)
                print(q)

        return str(_qtd)

    def __repr__(self) -> str:
        return f'<{self.symbol}: {self.price} USDT>'

    def __bool__(self) -> bool:
        return True

    @classmethod
    def get(cls, symbol: str):
        return cls.select_one('symbol', symbol)

    @classmethod
    def get_create(
        cls, symbol: str, price: float, keep_historic: int, lot_size: str
    ):
        coin = cls.get(symbol)
        if not coin:
            coin = Coin(
                symbol=symbol,
                price=price,
                keep_historic=keep_historic,
                lot_size=lot_size,
            )

        return coin


class Trade(Model):
    if session:
        __tablename__ = 'trades'
        coin_symbol = Column(
            String, ForeignKey('coins.symbol'), primary_key=True
        )
        price = Column(Float, nullable=False)
        age = Column(Integer, nullable=False)
        id = Column(Integer, nullable=False)
        coin = relationship('Coin', back_populates='trades')
    else:
        cache['Trade'] = []

    def __init__(self, coin: Coin, price: float, age: int, id: int) -> None:
        super().__init__(
            coin=coin,
            coin_symbol=str(coin.symbol),
            price=float(price),
            age=int(age),
            id=int(id),
        )

    def __repr__(self) -> str:
        return f'Trade(coin_symbol={self.coin_symbol}, price={self.price}, age={self.age})'

    @classmethod
    def get(cls, coin: Coin):
        return cls.select_one('coin_symbol', coin.symbol)


class Balance(Model):
    if session:
        __tablename__ = 'balance'
        coin_symbol = Column(
            String, ForeignKey('coins.symbol'), primary_key=True
        )
        quantity = Column(Float, nullable=False, default=0.0)
        fee = Column(Float, nullable=False, default=0.0)
        coin = relationship('Coin', back_populates='balance')
    else:
        cache['Balance'] = []

    def __init__(
        self, coin: Coin, quantity: float = 0.0, fee: float = 0.0
    ) -> None:
        super().__init__(
            coin=coin,
            coin_symbol=coin.symbol,
            quantity=float(quantity),
            fee=float(fee),
        )

    def set(self, quantity: float) -> None:
        self.quantity = quantity
        self.update()

    def __repr__(self) -> str:
        return f'Balance(coin_symbol={self.coin_symbol}, quantity={self.quantity}, fee={self.fee})'

    @classmethod
    def buy(cls, coin: Coin, quantity: float = None) -> None:
        usdt = Balance.get(Coin.get('USDT'))
        if usdt.quantity <= 12:
            raise Exception('Insufficient money!')

        if quantity == None:
            quantity = usdt.quantity / coin.price

        balance_coin = Balance.get(coin)

        balance_coin.set(
            balance_coin.quantity + (quantity * (1 - balance_coin.fee / 100))
        )
        usdt.set(usdt.quantity - (quantity * coin.price))

    @classmethod
    def sell(cls, coin: Coin, quantity: float = None) -> None:
        usdt = Balance.get(Coin.get('USDT'))
        balance_coin = Balance.get(coin)

        if quantity == None:
            quantity = balance_coin.quantity

        usdt.set(
            usdt.quantity + (quantity * coin.price) * (1 - usdt.fee / 100)
        )
        balance_coin.set(balance_coin.quantity - quantity)

    @classmethod
    def get(cls, coin: Coin):
        return cls.select_one('coin_symbol', coin.symbol)

    @classmethod
    def get_create(cls, coin: Coin, quantity: float = 0.0, fee: float = 0.1):
        balance = cls.get(coin)
        if not balance:
            balance = Balance(coin=coin, quantity=quantity, fee=fee)

        return balance

    @classmethod
    def to_dict(cls) -> dict:
        balances = cls.select_all()
        res = {}
        for balance in balances:
            res[balance.coin_symbol] = balance.quantity

        return res


if session:
    Model.metadata.create_all(engine)
