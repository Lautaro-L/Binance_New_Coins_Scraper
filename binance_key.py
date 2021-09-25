import yaml
import os
from binance.client import Client
from binance.exceptions import BinanceAPIException


def load_binance_creds(file):
    if os.path.exists(file):
        with open(file) as file:
            auth = yaml.load(file, Loader=yaml.FullLoader)
        return Client(api_key = auth['binance_key'], api_secret = auth['binance_secret'])
    else: print("Cant find: ", file)
