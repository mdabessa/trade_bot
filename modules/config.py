from environs import Env
from os import environ
import json


env = Env()
env.read_env('./config/.env')


DATABASE_URL = environ['DATABASE_URL']
