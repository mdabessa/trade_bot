import json
from os import environ

from environs import Env

path = "./config/"

env = Env()
env.read_env(f"{path}.env")


API_KEY = environ["API_KEY"]
API_SECRET = environ["API_SECRET"]
DATABASE_URL = environ["DATABASE_URL"]

DISCORD_WEBHOOK_URL = environ["DISCORD_WEBHOOK_URL"]
DISCORD_USER_ID_MENTION = environ["DISCORD_USER_ID_MENTION"]
DISCORD_WEBHOOK_USERNAME = environ["DISCORD_WEBHOOK_USERNAME"]
DISCORD_WEBHOOK_AVATAR = environ["DISCORD_WEBHOOK_AVATAR"]


with open(f"{path}coin_list.json", "r") as f:
    coins = json.load(f)

COINS = coins["coin_list"]


with open(f"{path}strategy.json", "r") as f:
    STRATEGY = json.load(f)


DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://")
