import os
import re
import time
import json
import requests
import threading
from json_manage import *
from binance_key import *
from config import *
from datetime import datetime
import dateutil.parser as dparser



ARTICLES_URL = 'https://www.binance.com/bapi/composite/v1/public/cms/article/catalog/list/query?catalogId=48&pageNo=1&pageSize=15'
ARTICLE      = 'https://www.binance.com/bapi/composite/v1/public/cms/article/detail/query?articleCode='

key_words = ['Futures', 'Isolated', 'Margin', 'Launchpool', 'Launchpad', 'Cross', 'Perpetual']
filter_List = ['body', 'type', 'catalogId', 'catalogName', 'publishDate']

file = 'announcements.json'
schedules_file = 'scheduled_order.json'
executed_trades_file = 'executed_trades.json'



cnf = load_config('config.yml')
client = load_binance_creds(r'auth.yml')



tp = cnf['TRADE_OPTIONS']['TP']
sl = cnf['TRADE_OPTIONS']['SL']

tsl_mode = cnf['TRADE_OPTIONS']['ENABLE_TSL']
tsl = cnf['TRADE_OPTIONS']['TSL']
ttp = cnf['TRADE_OPTIONS']['TTP']

pairing = cnf['TRADE_OPTIONS']['PAIRING']
ammount = cnf['TRADE_OPTIONS']['QUANTITY']
frequency = cnf['TRADE_OPTIONS']['RUN_EVERY']

test_mode = cnf['TRADE_OPTIONS']['TEST']

regex = '\S{2,6}?/'+ pairing


####announcements

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
    
    raw_pairs = re.findall(regex, new_Coin)
    pairs = []
    
    for pair in raw_pairs:
        pairs.append(pair.replace('/', ''))
    return [datetime, pairs]
    

####orders

def get_price(coin):
     return client.get_ticker(symbol=coin)['lastPrice']

def create_order(pair, usdt_to_spend, action):
    return client.create_order(
        symbol = pair,
        side = action,
        type = 'MARKET',
        quoteOrderQty = usdt_to_spend,
        recvWindow = "10000"
    )


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
    order = {}

    if test_mode:
        price = get_price(pair)
        while True:
            if time_till_live == datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"):
                order = {
                    "symbol": pair,
                    "transactTime": datetime.timestamp(datetime.now()),
                    "price": price,
                    "origQty": ammount/float(price),
                    "executedQty": ammount/float(price),
                    "cummulativeQuoteQty": ammount,
                    "status": "FILLED",
                    "type": "MARKET",
                    "side": "BUY"
                    }
                break
    else:
        while True:
            if time_till_live == datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"):
                #order = create_order(pair, ammount, 'BUY')
                break
    
    executed_order(order)

######


def check_Schedules():
    
    if os.path.exists(schedules_file):
        unfiltered_schedules = load_json(schedules_file)
        schedules = []
        
        for schedule in unfiltered_schedules:
            
            flag = True
            datetime = dparser.parse(schedule['time'], fuzzy=True, ignoretz=True)
            
            if datetime < datetime.utcnow():
                flag = False
            
            if flag:
                schedules.append(schedule)
                
                for pair in schedule['pairs']:
                    threading.Thread(target=place_Order_On_Time, args=(datetime, pair)).start()
        
        save_json(schedules_file, schedules)

                
                


def main():

    if os.path.exists(file):
        existing_Anouncements = load_json(file)

    else:
        existing_Anouncements = get_Announcements()
        for announcement in existing_Anouncements:
            time_And_Pair = get_Pair_and_DateTime(announcement['code'])
            if time_And_Pair[0] >= datetime.utcnow():
                schedule_Order(time_And_Pair, announcement)
                
        save_json(file, existing_Anouncements)
    
    threading.Thread(target=check_Schedules, args=()).start()
    
    
    while True:
        new_Anouncements = get_Announcements()

        for announcement in new_Anouncements:
            if not announcement in existing_Anouncements:
                time_And_Pair = get_Pair_and_DateTime(announcement['code'])
                if time_And_Pair[0] >= datetime.utcnow():
                    schedule_Order(time_And_Pair, announcement)
                    for pair in time_And_Pair[1]:
                        threading.Thread(target=place_Order_On_Time, args=(time_And_Pair[0], pair)).start()
        time.sleep(frequency)


#TODO:
# posible integration with AWS lambda ping it time before the coin is listed so it can place a limit order a little bti more than opening price
# once the code its better add support to other exchanges


if __name__ == '__main__':
    print('Starting')
    main()









#debuggin order
#{
#    "time": "2021-09-24 10:00:00",
#    "pairs": [
#        "DFUSDT",
#        "SYSUSDT"
#    ]
#}