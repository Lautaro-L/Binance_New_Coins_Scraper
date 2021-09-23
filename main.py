import os
import re
import time
import json
import requests
import threading
from datetime import datetime
import dateutil.parser as dparser

ARTICLES_URL = 'https://www.binance.com/bapi/composite/v1/public/cms/article/catalog/list/query?catalogId=48&pageNo=1&pageSize=15'
ARTICLE      = 'https://www.binance.com/bapi/composite/v1/public/cms/article/detail/query?articleCode='

key_words = ['Futures', 'Isolated', 'Margin', 'Launchpool', 'Launchpad', 'Cross', 'Perpetual']
filter_List = ['body', 'type', 'catalogId', 'catalogName', 'publishDate']

file = 'announcements.json'
schedules_file = 'scheduled_order.json'


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
    pair = re.findall(r'\S{2,6}?/USDT', new_Coin)
    return [datetime, pair]
    

def save_json(file, order):
    with open(file, 'w') as f:
        json.dump(order, f, indent=4)

def load_json(file):
    with open(file, "r+") as f:
        return json.load(f)



def update_announcements(announcement, existing_Anouncements):
    existing_Anouncements.append(announcement)
    save_json(file, existing_Anouncements)


def schedule_Order(time_And_Pair, announcement, existing_Anouncements):
    scheduled_order = {'time':time_And_Pair[0].strftime("%Y-%m-%d %H:%M:%S"), 'pairs':time_And_Pair[1]}
    
    if os.path.exists(schedules_file):
        existing_schedules = load_json(schedules_file)
        existing_schedules.append(scheduled_order)
    else: existing_schedules = [scheduled_order]
    
    save_json(schedules_file, existing_schedules)
    update_announcements(announcement, existing_Anouncements)


def place_Order_On_Time(time_till_live, pair, time_to_wait):
    time.sleep(time_to_wait)
    while True:
        if time_till_live == datetime.now().strftime("%Y-%m-%d %H:%M:%S"):
            print(datetime.now().strftime("%Y-%m-%d %H:%M:%S:%f"))
            print('check')
            break

def check_Schedules():
    
    if os.path.exists(schedules_file):
        schedules = load_json(schedules_file)
        
        for schedule in schedules:
            
            for pair in schedule['pairs']:
                
                datetime = dparser.parse(schedule['time'], fuzzy=True, ignoretz=True)
                
                time_to_wait = ((datetime - datetime.now()).total_seconds() - 9)
                
                threading.Thread(target=place_Order_On_Time, args=(str(datetime), pair, time_to_wait)).start()
            


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
            schedule_Order(time_And_Pair, announcement, existing_Anouncements)
            for pair in time_And_Pair[1]:
                time_to_wait = ((time_And_Pair[0] - datetime.now()).total_seconds() - 9)
                threading.Thread(target=place_Order_On_Time, args=(time_And_Pair[0], pair, time_to_wait)).start()


#TODO:
# after the purchase is done remove it from scheduled
# posible integration with AWS lambda ping it time before the coin is listed so it can place a limit order a little bti more than opening price
# add config files


if __name__ == '__main__':
    print('Starting')
    main()