import os
import sys

sys.path.append(os.path.join(os.path.dirname(sys.path[0])))

import sqlite3 as sql

import pandas as pd

from modules.config import COINS

connection = sql.connect("./data/crypto_historic.db")


for coin in COINS[8:9]:
    print(coin)
    path = f"./data/Binance_{coin}USDT.csv"
    print("Carregando csv...")
    df = pd.read_csv(path)
    print("criando table...")
    query = f"""CREATE TABLE IF NOT EXISTS {coin}(
        unix varchar(255),
        date datetime2,
        symbol varchar(255),
        open float,
        high float,
        low float,
        close float,
        volume float,
        volume_usdt float,
        tradecount integer,
        primary key(unix)
    )"""

    cursor = connection.cursor()
    cursor.execute(query)

    print("Inserindo valores...")
    v = list(df.values)
    v.reverse()

    cursor.executemany(
        f"""INSERT INTO {coin}(unix, date, symbol, open, high, low, close, volume, volume_usdt, tradecount)
    VALUES(?,?,?,?,?,?,?,?,?,?);""",
        v,
    )

    connection.commit()

connection.close()
