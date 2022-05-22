import json

import matplotlib.pyplot as plt
import numpy as np
import sqlite3 as sql
import datetime as dt


def db(url):
    conn = sql.connect(url)
    return conn


def get_currencies(connection: sql.Connection, start_date: dt.datetime, end_date: dt.datetime, coins: list):
    cursor = connection.cursor()
    currencies = {}
    for coin in coins:
        r = cursor.execute(f"""
                SELECT * FROM {coin}
                WHERE date BETWEEN '{start_date}' AND '{end_date}'
            """)
        currencies[coin] = r.fetchall()
    cursor.close()
    return currencies


def summary(fname):
    with open(fname, "r") as f:
        return json.load(f)


def diff_daily(data, plot=False):
    usdt = data["daily_close"]
    btc = data["daily_close_btc"]

    print(
        f"start: {usdt[0]} USDT, finish: {usdt[-1]} USDT, max: {max(usdt)} USDT, min: {min(usdt)} USDT"
    )
    print(
        f"start: {btc[0]} BTC, finish: {btc[-1]} BTC, max: {max(btc)} BTC, min: {min(btc)} BTC"
    )
    
    if plot:
        _usdt = list(map(lambda x: ((x / usdt[0]) * 100) - 100, usdt))
        _btc = list(map(lambda x: ((x / btc[0]) * 100) - 100, btc))

        _usdt.insert(0, 0)
        _btc.insert(0, 0)

        plt.plot(_btc, label="BTC")
        plt.plot(_usdt, label="USDT")
        plt.title("Progress")
        plt.xlabel("Days")
        plt.ylabel("%")
        plt.legend()
        plt.show()


def order_freq(data, plot=False):
    buy = list(filter(lambda x: x["type"] == "buy", data["orders_historic"]))

    diffs = []
    for i in range(1, len(buy)):
        diff = buy[i]["epoch"] - buy[i - 1]["epoch"]
        diffs.append(diff)

    c = max(diffs)
    c = (c / 60) / 24
    date = data["orders_historic"][np.argmax(diffs)]["date"]
    print(f"Longer streak without activity was {c} days on {date}")

    m = sum(diffs) / len(diffs)
    m = (m / 60) / 24
    print(f"Avarege streak between buys: {m} days")

    if plot:
        plt.plot(diffs)
        plt.show()


def get_order(data, query, key):
    try:
        order = list(filter(lambda x: x[key] == query, data["orders_historic"]))[0]
        return order
    except:
        return None


def best_and_worst(data):
    buy = list(filter(lambda x: x["type"] == "buy", data["orders_historic"]))
    sell = list(filter(lambda x: x["type"] == "sell", data["orders_historic"]))

    diffs = []
    for i in range(len(buy)):
        diff = sell[i]["price"] / buy[i]["price"]
        diffs.append(diff)

    best = np.argmax(diffs)
    worst = np.argmin(diffs)

    print(
        f'Best: {buy[best]["symbol"]} buy: {buy[best]["price"]} and sell: {sell[best]["price"]} diff: +{(diffs[best]*100)-100}%'
    )
    print(
        f'Worst: {buy[worst]["symbol"]} buy: {buy[worst]["price"]} and sell: {sell[worst]["price"]} diff: -{((1/diffs[worst])*100)-100}%'
    )


def freq_sell(data):
    buy = list(filter(lambda x: x["type"] == "buy", data["orders_historic"]))
    sell = list(filter(lambda x: x["type"] == "sell", data["orders_historic"]))

    c = [sell[x]["epoch"] - buy[x]["epoch"] for x in range(len(buy))]
    f = ((sum(c) / len(c)) / 60) / 24
    print(f"Sell freq: {f} days")


def positives_and_negatives(data):
    buy = list(filter(lambda x: x["type"] == "buy", data["orders_historic"]))
    sell = list(filter(lambda x: x["type"] == "sell", data["orders_historic"]))

    c = [1 if sell[x]["price"] - buy[x]["price"] > 0 else 0 for x in range(len(buy))]
    p = sum(c)
    print(
        f"Positives orders: {p}, Negatives orders: {len(c)-p}, Total orders: {len(c)}, Diff: {(p/len(c))*100}%"
    )


def buy_same_followed(data):
    buy = list(filter(lambda x: x["type"] == "buy", data["orders_historic"]))
    c = buy[0]
    m = 0
    for i in range(1, len(buy)):
        if buy[i]["symbol"] == c["symbol"]:
            m += 1
        c = buy[i]

    print(f"Was bought {m} coin same followed.")


def coin_quality(data):
    print("=== Trades by Coins ===")
    orders = data["orders_historic"]
    buy = list(filter(lambda x: x["type"] == "buy", orders))

    coins = {}
    for b in buy:
        s = list(filter(lambda x: x["type"] == "sell" and x["id"] == b["id"], orders))[
            0
        ]
        diff = s["price"] / b["price"]

        try:
            coins[b["symbol"]].append(diff)
        except:
            coins[b["symbol"]] = [diff]

    res = []
    for key in coins.keys():
        pos = len(list(filter(lambda x: x >= 1, coins[key])))
        total = len(coins[key])
        symbol = key
        res.append([pos, total, symbol])

    res.sort(key=lambda x: x[0] / x[1], reverse=True)

    for r in res:
        pos = r[0]
        total = r[1]
        key = r[2]

        print(
            f'{key}{" "*(5-len(key))} || Positives: {pos}, Total: {total} = {(pos/total)*100}%'
        )


def streak_pattern(data):
    streaks = []
    streak = None
    b_orders = list(filter(lambda x: x["type"] == "buy", data["orders_historic"]))
    s_orders = list(filter(lambda x: x["type"] == "sell", data["orders_historic"]))
    
    for b_order in b_orders:
        s_order = list(filter(lambda x: x['id'] == b_order['id'], s_orders))[0]
        diff = s_order['price'] - b_order['price']
        if diff != 0:
            diff = diff/abs(diff)


        if streak == None:
            streak = {
                'start_date': b_order['date'],
                'end_date': s_order['date'],
                'diff': diff,
                'trades_count': 1
            }

            continue
            
        if diff == streak['diff']:
            streak['end_date'] = s_order['date']
            streak['trades_count'] += 1
        
        else:
            streaks.append(streak)
            streak = {
                'start_date': b_order['date'],
                'end_date': s_order['date'],
                'diff': diff,
                'trades_count': 1
            }
        
    if streak != None:
        streaks.append(streak)

    print(len(streaks))
    conn = db('./data/crypto_historic.db')
    total_med = {'pos':[], 'neg':[]} 
    for p in streaks:
        print(p)
        start = dt.datetime.strptime(p['start_date'], "%Y-%m-%d %H:%M:%S")
        dist = dt.timedelta(days=10)
        pre = start - dist
        currencies = get_currencies(conn, pre, start, data['coins'])
        
        btc = currencies['BTC']
        price = [x[3] for x in btc]
        med = ((price[-1]/price[0])-1)*100
        if p['diff'] == 1:
            total_med['pos'].append(med)
        else:
            total_med['neg'].append(med)

    total_med['pos'] = sum(total_med['pos'])/len(total_med['pos'])
    total_med['neg'] = sum(total_med['neg'])/len(total_med['neg'])
    print(total_med)


data = summary("./backtest/summary.json")

plot = False
diff_daily(data, plot)
order_freq(data, plot)
best_and_worst(data)
freq_sell(data)
positives_and_negatives(data)
buy_same_followed(data)
coin_quality(data)
streak_pattern(data)
