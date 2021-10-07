import os
import time
import traceback
from json_manage import *
from config import *
from datetime import datetime

executed_trades_file = 'executed_trades.json'
executed_sells_file = 'executed_sells_trades.json'

cnf = load_config('config.yml')

tp = cnf['TRADE_OPTIONS']['TP']
sl = cnf['TRADE_OPTIONS']['SL']

tsl_mode = cnf['TRADE_OPTIONS']['ENABLE_TSL']
tsl = cnf['TRADE_OPTIONS']['TSL']
ttp = cnf['TRADE_OPTIONS']['TTP']

pairing = cnf['TRADE_OPTIONS']['PAIRING']
ammount = cnf['TRADE_OPTIONS']['QUANTITY']
frequency = cnf['TRADE_OPTIONS']['RUN_EVERY']

test_mode = cnf['TRADE_OPTIONS']['TEST']
delay_mode = cnf['TRADE_OPTIONS']['CONSIDER_DELAY']
percentage = cnf['TRADE_OPTIONS']['PERCENTAGE']

def main():
    while True:
        try:
            flag_update = False
            not_sold_orders = []
            order = []
            if os.path.exists(executed_trades_file):
                order = load_json(executed_trades_file)
            if len(order) > 0:
                for coin in list(order):

                    # store some necesarry trade info for a sell
                    stored_price = float(coin['price'])
                    coin_tp = coin['tp']
                    coin_sl = coin['sl']
                    volume = coin['executedQty']
                    symbol = coin['symbol']
                    last_price = float(coin['last'])

                    # update stop loss and take profit values if threshold is reached
                    if float(last_price) > coin_tp and tsl_mode:
                        # increase as absolute value for TP
                        new_tp = float(last_price) + (float(last_price)*ttp /100)

                        # same deal as above, only applied to trailing SL
                        new_sl = float(last_price) - (float(last_price)*tsl /100)

                        # new values to be added to the json file
                        coin['tp'] = new_tp
                        coin['sl'] = new_sl
                        not_sold_orders.append(coin)
                        flag_update = True

                        print(f'Updated tp: {round(new_tp, 3)} and sl: {round(new_sl, 3)} for: {symbol}')
                    # close trade if tsl is reached or trail option is not enabled
                    elif float(last_price) < coin_sl or float(last_price) > coin_tp:
                        try:

                            # sell for real if test mode is set to false
                            if not test_mode:
                                sell = 12


                            print(f"Sold {symbol} at {(float(last_price) - stored_price) / float(stored_price)*100}")
                            flag_update = True
                            # remove order from json file by not adding it

                        except Exception as exception:
                            wrong = traceback.format_exc(limit=None, chain=True)
                            print(wrong)

                        # store sold trades data
                        else:
                            if os.path.exists(executed_sells_file):
                                sold_coins = load_json(executed_sells_file)

                            else:
                                sold_coins = []

                            if not test_mode:
                                sold_coins.append(sell)
                            else:
                                sell = {
                                            'symbol':symbol,
                                            'price':last_price,
                                            'volume':volume,
                                            'time':datetime.timestamp(datetime.now()),
                                            'profit': float(last_price) - stored_price,
                                            'relative_profit': round((float(last_price) - stored_price) / stored_price*100, 3)
                                            }
                                sold_coins.append(sell)
                            save_json(executed_sells_file, sold_coins)

                    else:
                        not_sold_orders.append(coin)
                    if flag_update: save_json(executed_trades_file, not_sold_orders)
        except Exception as exception:       
            wrong = traceback.format_exc(limit=None, chain=True)
            print(wrong)
        time.sleep(0.2)


if __name__ == '__main__':
    main()

    #{
    #    "last": "3.98000000",
    #    "symbol": "AGLDUSDT",
    #    "orderId": 38,
    #    "orderListId": -1,
    #    "clientOrderId": "CSWvQ0LOj8azSx4uGbQSCa",
    #    "transactTime": 1633417200060,
    #    "price": "3.98000000",
    #    "origQty": "12.50000000",
    #    "executedQty": "12.50000000",
    #    "cummulativeQuoteQty": "49.75000000",
    #    "status": "FILLED",
    #    "timeInForce": "GTC",
    #    "type": "MARKET",
    #    "side": "BUY",
    #    "fills": [
    #        {
    #            "price": "3.98000000",
    #            "qty": "12.50000000",
    #            "commission": "0.00006497",
    #            "commissionAsset": "BNB",
    #            "tradeId": 13
    #        }
    #    ],
    #    "tp": 4.0198,
    #    "sl": 3.9402 
    #}
    #{
#    "time": "2021-09-24 10:00:00",
#    "pairs": [
#        "DFUSDT",
#        "SYSUSDT"
#    ]
#}