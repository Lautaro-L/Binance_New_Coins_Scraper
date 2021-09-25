import os
import re
import time
import json
import requests
import threading
import logging
import traceback
from telegram import Bot, Chat
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
executed_sells_file = 'executed_sells_trades.json'



cnf = load_config('config.yml')
client = load_binance_creds(r'auth.yml')

telegram_status = True

if os.path.exists('telegram.yml'):
    global telegram_keys 
    telegram_keys = load_config('telegram.yml')

    global tbot
    tbot = Bot(telegram_keys['telegram_key'])

    global chat_id 
    chat_id = telegram_keys['chat_id']

    global chat 
    chat = Chat(chat_id, "private", bot=tbot)
else: telegram_status = False


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

def sendmsg(message):
    if telegram_status:
        threading.Thread(target=chat.send_message, args=(message,)).start()


def ping_binance():
    time_before = datetime.timestamp(datetime.now())
    client.ping()
    time_after = datetime.timestamp(datetime.now())
    return (time_after - time_before)

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
    try:
        order = client.create_order(
            symbol = pair,
            side = action,
            type = 'MARKET',
            quoteOrderQty = usdt_to_spend,
            recvWindow = "10000"
        )
    except Exception as exception:       
        wrong = traceback.format_exc(limit=None, chain=True)
        sendmsg(wrong)
    return order

def executed_order(order):
    update_json(executed_trades_file, order)#needs more logic maybe to remove finished schedules tho is not critical


def schedule_Order(time_And_Pair, announcement):
    try:
        scheduled_order = {'time':time_And_Pair[0].strftime("%Y-%m-%d %H:%M:%S"), 'pairs':time_And_Pair[1]}

        sendmsg(f'scheduled an order for: {time_And_Pair[1]} at: {time_And_Pair[0]}')
        update_json(schedules_file, scheduled_order)
        update_json(file, announcement)
    except Exception as exception:       
        wrong = traceback.format_exc(limit=None, chain=True)
        sendmsg(wrong)


def place_Order_On_Time(time_till_live, pair):
    try:
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
                    order = create_order(pair, ammount, 'BUY')
                    break
        order['tp'] = tp
        order['sl'] = sl
        executed_order(order)
        amount = order['executedQty']
        price =order['price']
        sendmsg(f'bougth {amount} of {pair} at {price}')
    except Exception as exception:       
        wrong = traceback.format_exc(limit=None, chain=True)
        sendmsg(wrong)
######


def check_Schedules():
    try:
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
                        sendmsg(f'found new announcement preparing schedule for {pair}')
            save_json(schedules_file, schedules)
    except Exception as exception:       
        wrong = traceback.format_exc(limit=None, chain=True)
        sendmsg(wrong)
                

def sell():
    try:
        while True:
            if os.path.exists(executed_trades_file):
                order = load_json(executed_trades_file)

                for coin in list(order):

                    # store some necesarry trade info for a sell
                    stored_price = float(coin['price'])
                    coin_tp = coin['tp']
                    coin_sl = coin['sl']
                    volume = coin['executedQty']
                    symbol = coin['symbol']
                    not_sold_orders = []

                    last_price = get_price(symbol)

                    # update stop loss and take profit values if threshold is reached
                    if float(last_price) > stored_price + (stored_price * float(coin_tp) /100) and tsl_mode:
                        # increase as absolute value for TP
                        new_tp = float(last_price) + (float(last_price)*ttp /100)
                        # convert back into % difference from when the coin was bought
                        new_tp = float( (new_tp - stored_price) / stored_price*100)

                        # same deal as above, only applied to trailing SL
                        new_sl = float(last_price) - (float(last_price)*tsl /100)
                        new_sl = float((new_sl - stored_price) / stored_price*100)

                        # new values to be added to the json file
                        coin['tp'] = new_tp
                        coin['sl'] = new_sl
                        not_sold_orders.append(coin)
                        save_json(executed_trades_file, not_sold_orders)

                        print(f'updated tp: {round(new_tp, 3)} and sl: {round(new_sl, 3)}')
                        sendmsg(f'updated tp: {round(new_tp, 3)} and sl: {round(new_sl, 3)} for: {symbol}')
                    # close trade if tsl is reached or trail option is not enabled
                    elif float(last_price) < stored_price - (stored_price*sl /100) or float(last_price) > stored_price + (stored_price*tp /100) and not tsl_mode:

                        try:

                            # sell for real if test mode is set to false
                            if not test_mode:
                                sell = client.create_order(symbol = symbol, side = 'SELL', type = 'MARKET', quantity = volume, recvWindow = "10000")


                            print(f"sold {symbol} at {(float(last_price) - stored_price) / float(stored_price)*100}")
                            sendmsg(f"sold {symbol} at {(float(last_price) - stored_price) / float(stored_price)*100}")
                            # remove order from json file by not adding it

                        except Exception as exception:
                            wrong = traceback.format_exc(limit=None, chain=True)
                            sendmsg(wrong)

                        # store sold trades data
                        else:
                            if os.path.exists(executed_sells_file):
                                sold_coins = load_json(executed_sells_file)

                            else:
                                sold_coins = []

                            if not test_mode:
                                sold_coins.append(sell)
                                save_json(executed_sells_file, sold_coins)
                            else:
                                sell = {
                                            'symbol':symbol,
                                            'price':last_price,
                                            'volume':volume,
                                            'time':datetime.timestamp(datetime.now()),
                                            'profit': float(last_price) - stored_price,
                                            'relative_profit': round((float(last_price) - stored_price) / stored_price*100, 3)
                                            }

                                save_json(executed_sells_file, sold_coins)
            time.sleep(0.2)
    except Exception as exception:       
        wrong = traceback.format_exc(limit=None, chain=True)
        sendmsg(wrong)


def main():

    if os.path.exists(file):
        existing_Anouncements = load_json(file)

    else:
        existing_Anouncements = get_Announcements()
        for announcement in existing_Anouncements:
            time_And_Pair = get_Pair_and_DateTime(announcement['code'])
            if time_And_Pair[0] >= datetime.utcnow():
                schedule_Order(time_And_Pair, announcement)
                sendmsg(f'found new announcement preparing schedule for {time_And_Pair[1]}')
        save_json(file, existing_Anouncements)

    threading.Thread(target=check_Schedules, args=()).start()
    threading.Thread(target=sell, args=()).start()
    
    while True:
        new_Anouncements = get_Announcements()

        for announcement in new_Anouncements:
            if not announcement in existing_Anouncements:
                time_And_Pair = get_Pair_and_DateTime(announcement['code'])
                if time_And_Pair[0] >= datetime.utcnow():
                    schedule_Order(time_And_Pair, announcement)
                    for pair in time_And_Pair[1]:
                        threading.Thread(target=place_Order_On_Time, args=(time_And_Pair[0], pair)).start()
                        sendmsg(f'found new announcement preparing schedule for {pair}')
        time.sleep(frequency)


#TODO:
# posible integration with AWS lambda ping it time before the coin is listed so it can place a limit order a little bti more than opening price
# once the code its better add support to other exchanges


if __name__ == '__main__':
    try:
        sendmsg(f'starting')
        print('Starting')
        print(ping_binance())
        main()
    except Exception as exception:
        wrong = traceback.format_exc(limit=None, chain=True)
        sendmsg(wrong)









#debuggin order
#{
#    "time": "2021-09-24 10:00:00",
#    "pairs": [
#        "DFUSDT",
#        "SYSUSDT"
#    ]
#}