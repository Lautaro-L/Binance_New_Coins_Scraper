import os
import re
import time
import json
import requests
import threading


from json_manage import *
from binance_key import *
from datetime import datetime
import dateutil.parser as dparser

ARTICLES_URL = 'https://www.binance.com/bapi/composite/v1/public/cms/article/catalog/list/query?catalogId=48&pageNo=1&pageSize=15'
ARTICLE      = 'https://www.binance.com/bapi/composite/v1/public/cms/article/detail/query?articleCode='

key_words = ['Futures', 'Isolated', 'Margin', 'Launchpool', 'Launchpad', 'Cross', 'Perpetual']
filter_List = ['body', 'type', 'catalogId', 'catalogName', 'publishDate']

file = 'announcements.json'
schedules_file = 'scheduled_order.json'
executed_trades_file = 'executed_trades.json'

ammount = 500

client = load_binance_creds(r'auth.yml')


def create_order(pair, usdt_to_spend, action):
    return client.create_order(
        symbol = pair,
        side = action,
        type = 'MARKET',
        quoteOrderQty = usdt_to_spend,
        recvWindow = "10000"
    )



def get_Announcements():
    unfiltered_Articles = requests.get(ARTICLES_URL).json()['data']['articles']
    articles = []

    for article in unfiltered_Articles:
        flag = True
        for word in key_words:
            if word in article['title']:
                flag = False
        if flag:
            articles.append(article)
                

    for article in articles:
        for undesired_Data in filter_List:
            if undesired_Data in article:
                del article[undesired_Data]
    
    return articles


def get_Pair_and_DateTime(ARTICLE_CODE):
    
    new_Coin = requests.get(ARTICLE+ARTICLE_CODE).json()['data']['seoDesc']
    datetime = dparser.parse(new_Coin, fuzzy=True, ignoretz=True)
    
    raw_pairs = re.findall(r'\S{2,6}?/USDT', new_Coin)
    pairs = []
    
    for pair in raw_pairs:
        pairs.append(pair.replace('/', ''))
    return [datetime, pairs]
    

def executed_order(order):
    update_json(executed_trades_file, order)#needs more logic 


def schedule_Order(time_And_Pair, announcement):
    scheduled_order = {'time':time_And_Pair[0].strftime("%Y-%m-%d %H:%M:%S"), 'pairs':time_And_Pair[1]}

    update_json(schedules_file, scheduled_order)
    update_json(file, announcement)



def place_Order_On_Time(time_till_live, pair):
    
    time_to_wait = ((time_till_live - datetime.utcnow()).total_seconds() - 10)
    time_till_live = str(time_till_live)
    time.sleep(time_to_wait)

    while True:
        if time_till_live == datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"):
            print(pair, ammount, 'BUY')
            #executed_order(order)
            break




def check_Schedules():
    
    if os.path.exists(schedules_file):
        schedules = load_json(schedules_file)
        
        for schedule in schedules:
            datetime = dparser.parse(schedule['time'], fuzzy=True, ignoretz=True)
            if datetime > datetime.utcnow():
                del schedule


            for pair in schedule['pairs']:
                
                
                threading.Thread(target=place_Order_On_Time, args=(datetime, pair)).start()


def main():

    if os.path.exists(file):
        existing_Anouncements = load_json(file)

    else:
        existing_Anouncements = get_Announcements()
        save_json(file, existing_Anouncements)
    
    threading.Thread(target=check_Schedules, args=()).start()
    
    new_Anouncements = get_Announcements()

    for announcement in new_Anouncements:
        if not announcement in existing_Anouncements:
            time_And_Pair = get_Pair_and_DateTime(announcement['code'])
            schedule_Order(time_And_Pair, announcement)
            for pair in time_And_Pair[1]:
                threading.Thread(target=place_Order_On_Time, args=(time_And_Pair[0], pair)).start()


#TODO:
# after the purchase is done remove it from scheduled
# posible integration with AWS lambda ping it time before the coin is listed so it can place a limit order a little bti more than opening price
# add config files
# once the code its better add support to other exchanges


if __name__ == '__main__':
    print('Starting')
    main()