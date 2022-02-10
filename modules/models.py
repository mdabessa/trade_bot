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
        
        if session:
            session.add(self)
            session.commit()


    def delete(self):
        self.super().delete()
        session.commit()


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


    @classmethod    
    def get(cls, key:str):
        r = cls.select_one(cls.key == key)
        value = eval(r.type_+f'({r.value})')
        return value


class Coin(Model):
    __tablename__ = 'coins'

    symbol = Column(String, unique=True, nullable=False)
    historic = Column(ARRAY(Float), default=[])
    trades = relationship('Trade', back_populates='coin')
    wallet = relationship('Wallet', back_populates='coin')

    def __init__(self, symbol: str, price: float, keep_historic: int, lot_size: str) -> None:
        super().__init__(symbol=symbol)

        self.keep_historic = keep_historic 
        self.lot_size = lot_size

        self.set_price(price)


    def set_price(self, price: float) -> None:
        self.price = price
        self.addHistoric(price)
        self.update()


    def add_historic(self, price: float) -> None:
        self.historic.append(price)
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


class Trade(Model):
    __tablename__ = 'trades'

    price = Column(Float, nullable=False)
    age = Column(Integer, nullable=False)
    coin_id =  Column(Integer, ForeignKey('coins.id'))
    coin = relationship('Coin', back_populates='trades')


class Wallet(Model):
    __tablename__ = 'wallet'

    quantity = Column(Float, nullable=False, default=0.0)
    coin_id = Column(Integer, ForeignKey('coins.id'), unique=True, nullable=False)
    coin = relationship('Coin', back_populates='wallet')

    def __init__(self, coin: Coin, quantity: float = 0.0, fee: float = 0.1) -> None:
        super().__init__(coin, quantity)
        
        self.fee = fee


    def set(self, quantity: float) -> None:
        self.quantity = quantity
        self.update()

    
    @classmethod
    def buy(cls, coin: Coin, quantity: float = None) -> None:
        usdt = cls.select_one(cls.coin.symbol == 'USDT')
        if usdt.quantity <= 12:
            raise Exception('Insufficient money!')
        
        if quantity == None:
            quantity = usdt.quantity/coin.price
        
        wallet_coin = coin.wallet

        wallet_coin.set(wallet_coin.quantity + (quantity * (1 - wallet_coin.fee/100)))
        usdt.set(usdt.quantity - (quantity * coin.price))
    

    @classmethod
    def sell(cls, coin: Coin, quantity: float = None) -> None:
        usdt = cls.select_one(cls.coin.symbol == 'USDT')

        wallet_coin = coin.wallet
        if quantity == None:
            quantity = wallet_coin.quantity

        usdt.set(usdt.quantity + (quantity * coin.price) * (1 - usdt.fee/100))
        wallet_coin.set(wallet_coin.quantity - quantity)


    @classmethod
    def to_dict(cls) -> dict:
        coins = cls.select_all()
        res = {}
        for coin in coins:
            res[coin.coin.symbol] = coin.quantity

        return res 


Model.metadata.create_all(engine)
