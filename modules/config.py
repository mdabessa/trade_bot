import json
from os import environ

from environs import Env

path = './config/'

env = Env()
env.read_env(f'{path}.env')


DATABASE_URL = environ['DATABASE_URL']
DATABASE_URL = None


COINS = []
with open(f'{path}coin_list.txt', 'r') as f:
    coins = f.read()

coins = coins.split('\n')
for c in coins:
    if not c.startswith('#'):
        COINS.append(c.upper())


with open(f'{path}strategy.json', 'r') as f:
    STRATEGY = json.load(f)


with open(f'{path}discord_webhook.json', 'r') as f:
    DISCORD_WEBHOOK = json.load(f)
