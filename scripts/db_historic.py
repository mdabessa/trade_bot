import sys, os

sys.path.append(os.path.join(os.path.dirname(sys.path[0])))

import sqlite3 as sql
import urllib.request

import pandas as pd
import tqdm

from modules.config import COINS

connection = sql.connect("./data/crypto_historic.db")

it = tqdm.tqdm(COINS, desc="Downloading csv...")
for coin in it:
    response = urllib.request.urlopen(
        f"https://www.cryptodatadownload.com/cdd/Binance_{coin.upper()}USDT_minute.csv"
    )
    html = response.read()

    with open(f"data/Binance_{coin.upper()}USDT.csv", "wb") as f:
        f.write(html)

for coin in COINS:
    print(coin)
    path = f"./data/Binance_{coin}USDT.csv"
    print("Loading csv...")
    df = pd.read_csv(path, skiprows=1)
    print("Creating table...")
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

    print("Inserting values...")
    v = list(df.values)
    v.reverse()

    cursor.executemany(
        f"""INSERT INTO {coin}(unix, date, symbol, open, high, low, close, volume, volume_usdt, tradecount)
    VALUES(?,?,?,?,?,?,?,?,?,?);""",
        v,
    )

    connection.commit()

connection.close()
