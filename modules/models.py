from decimal import Decimal
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import  create_engine, Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.dialects.postgresql import ARRAY

from .config import DATABASE_URL


engine = create_engine(DATABASE_URL, echo=False)
Session = sessionmaker(bind=engine)
session = Session()


Base = declarative_base()


class Model(Base):
    __abstract__  = True

    id = Column(Integer, primary_key=True)


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
    def select(cls, expression):
        if session:
            return session.query(cls).filter(expression).all()
        else:
            return []


    @classmethod
    def select_one(cls, expression):
        if session:
            return session.query(cls).filter(expression).first()
        else:
            return None


    @classmethod
    def select_all(cls):
        if session:
            return session.query(cls).all()
        else:
            return []


class Header(Model):
    __tablename__ = 'headers'
    
    key = Column(String, unique=True)
    value = Column(String, nullable=False)
    type_ = Column(String, nullable=False)
    

    def set(self, value):
        self.value = str(value)
        self.update()


    def evaluate(self):
        value = eval(self.type_+f'("{self.value}")')
        return value
    
    
    def __bool__(self) -> bool:
        return bool(self.evaluate())


    @classmethod
    def get(cls, key: str):
        return cls.select_one(cls.key == key)


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
    __tablename__ = 'coins'

    symbol = Column(String, unique=True, nullable=False)
    price = Column(Float, default=0.0, nullable=False)
    historic = Column(ARRAY(Float), default=[])
    keep_historic = Column(Integer, default=50, nullable=False)
    lot_size = Column(String, default='0.001', nullable=False)
    trades = relationship('Trade', back_populates='coin')
    balance = relationship('Balance', back_populates='coin', uselist=False)


    def set_price(self, price: float) -> None:
        self.price = price
        self.update()
        self.add_historic(price)


    def add_historic(self, price: float) -> None:
        historic = self.historic.copy()
        historic.append(price)
        while len(historic) > self.keep_historic:
            historic.pop(0)

        self.historic = historic.copy() 
        self.update()

    
    def quantity_lot_size(self, quantity: float) -> str:
        if float(self.lot_size) == 1:
            _qtd = int(quantity)
        else:
            q = Decimal(quantity-float(self.lot_size))
            _qtd = q.quantize(Decimal(str(float(self.lot_size))))
        
        return str(_qtd)


    def __repr__(self) -> str:
        return f'<{self.symbol}: {self.price} USDT>'


    def __bool__(self) -> bool:
        return True


    @classmethod
    def get(cls, symbol: str):
        return cls.select_one(cls.symbol == symbol)
    

    @classmethod
    def get_create(cls, symbol: str, price: float, keep_historic: int, lot_size: str): 
        coin = cls.get(symbol)
        if not coin:
            coin = Coin(symbol=symbol, price=price, keep_historic=keep_historic, lot_size=lot_size)
        
        return coin



class Trade(Model):
    __tablename__ = 'trades'

    price = Column(Float, nullable=False)
    age = Column(Integer, nullable=False)
    coin_id =  Column(Integer, ForeignKey('coins.id'))
    coin = relationship('Coin', back_populates='trades')


    @classmethod
    def get(cls, coin: Coin):
        return cls.select_one(cls.coin == coin)



class Balance(Model):
    __tablename__ = 'balance'

    quantity = Column(Float, nullable=False, default=0.0)
    fee = Column(Float, nullable=False, default=0.0)
    coin_id = Column(Integer, ForeignKey('coins.id'), unique=True, nullable=False)
    coin = relationship('Coin', back_populates='balance')


    def set(self, quantity: float) -> None:
        self.quantity = quantity
        self.update()

    
    @classmethod
    def buy(cls, coin: Coin, quantity: float = None) -> None:
        usdt = Coin.get('USDT').balance
        if usdt.quantity <= 12:
            raise Exception('Insufficient money!')
        
        if quantity == None:
            quantity = usdt.quantity/coin.price
        
        balance_coin = coin.balance

        balance_coin.set(balance_coin.quantity + (quantity * (1 - balance_coin.fee/100)))
        usdt.set(usdt.quantity - (quantity * coin.price))
    

    @classmethod
    def sell(cls, coin: Coin, quantity: float = None) -> None:
        usdt = Coin.get('USDT').balance

        balance_coin = coin.balance
        if quantity == None:
            quantity = balance_coin.quantity

        usdt.set(usdt.quantity + (quantity * coin.price) * (1 - usdt.fee/100))
        balance_coin.set(balance_coin.quantity - quantity)


    @classmethod
    def get(cls, coin: Coin):
        return cls.select_one(cls.coin == coin)


    @classmethod
    def get_create(cls, coin: Coin, quantity: float = 0.0, fee: float = 0.1):
        balance = cls.get(coin)
        if not balance:
            balance = Balance(coin=coin, quantity=quantity, fee=fee)

        return balance


    @classmethod
    def to_dict(cls) -> dict:
        coins = cls.select_all()
        res = {}
        for coin in coins:
            res[coin.coin.symbol] = coin.quantity

        return res 


Model.metadata.create_all(engine)
