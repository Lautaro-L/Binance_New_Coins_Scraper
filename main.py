import os
import time
import json
from typing import NewType
import requests
from datetime import date
from datetime import datetime
from threading import Thread

ARTICLES_URL = 'https://www.binance.com/bapi/composite/v1/public/cms/article/catalog/list/query?catalogId=48&pageNo=1&pageSize=15'
ARTICLE      = 'https://www.binance.com/bapi/composite/v1/public/cms/article/detail/query?articleCode='

key_words = ['Binance Will List', 'adds', 'updates', 'enabled', 'trade', 'support']


def get_Announcements():
        articles = requests.get(ARTICLES_URL).json()
        return articles['data']['articles']

def get_Pari_and_DateTime(ARTICLE_CODE):
    new_Coin = requests.get(ARTICLE+ARTICLE_CODE).json()
    print(new_Coin['data']['seoDesc'])

def main():
    new_Anouncements = get_Announcements()

    for announcement in new_Anouncements:
        if key_words[0] in announcement['title']:
            get_Pari_and_DateTime(announcement['code'])

#TODO:
# save notice code to be able to check for new coins announcements
# after the purchase is done save in on database
# posible integration with AWS lambda ping it time before the coin is listed so it can place a limit order a little bti more than opening price
# add config files
# extract keywords from seoDesc
# plan multiple purchases?


if __name__ == '__main__':
    print('Starting')
    main()