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
        session.commit()


    @classmethod    
    def get(cls, key:str):
        r = cls.select_one(cls.key == key)
        value = eval(r.type_+f'({r.value})')
        return value


class Coin(Model):
    __tablename__ = 'coins'

    symbol = Column(String, unique=True, nullable=False)
    historic = Column(ARRAY(Float))
    trades = relationship('Trade', back_populates='coin')
    wallet = relationship('Wallet', back_populates='coin')


class Trade(Model):
    __tablename__ = 'trades'

    price = Column(Float, nullable=False)
    age = Column(Integer, nullable=False)
    coin_id =  Column(Integer, ForeignKey('coins.id'))
    coin = relationship('Coin', back_populates='trades')


class Wallet(Model):
    __tablename__ = 'wallet'

    quantity = Column(Float, nullable=False, default=0.0)
    coin_id = Column(Integer, ForeignKey('coins.id'))
    coin = relationship('Coin', back_populates='wallet')



Model.metadata.create_all(engine)
