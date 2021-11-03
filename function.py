#!/usr/bin/env python
# -*- coding: utf-8 -*-
#--------------------------------#
"""
File name: function.py
Author: WEI-TA KUAN
Date created: 9/10/2021
Date last modified: 1/11/2021
Version: 3.1
Python Version: 3.8.8
Status: Developing
"""
#--------------------------------#

from datetime import datetime
from dotenv import load_dotenv
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import time
import pickle
import joblib
import logging
import os

load_dotenv()

def place_order(symbol, type, close_price, lot=1.0):
    """This function create buy and sell order in MT5 platform, the default lot is 1"""
    code = 0

    # Place buy order
    if type == "long":
        request = {
        "action": mt5.TRADE_ACTION_PENDING,
        "symbol": symbol,
        "volume": lot,
        "type": mt5.ORDER_TYPE_BUY_LIMIT,
        "price": close_price - float(os.environ['ADD_PIP'])
        }

    elif type == "short":
        request = {
        "action": mt5.TRADE_ACTION_PENDING,
        "symbol": symbol,
        "volume": lot,
        "type": mt5.ORDER_TYPE_SELL_LIMIT,
        "price": close_price + float(os.environ['ADD_PIP'])
        }
    
    while code !=  mt5.TRADE_RETCODE_DONE:

        code = mt5.order_send(request).retcode

        if code ==  mt5.TRADE_RETCODE_DONE:
            break
    
    create_log(f"Open {type} pending position {request}")

def close_position(open_position):
    """This function is for closing all the existing position 
    by sending signal to place_order function"""

    for _, row in open_position.iterrows():
        # MT5 Order Type == 1 is short order Type == 0 is long Order
        if row['type'] == 0:
            order_price = mt5.symbol_info_tick(row['symbol']).bid
            request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": row['symbol'],
            "volume": row["volume"],
            "type": mt5.ORDER_TYPE_SELL,
            "price": order_price,
            "position": row["ticket"]
            }
        
        else:
            order_price = mt5.symbol_info_tick(row['symbol']).ask
            request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": row['symbol'],
            "volume": row["volume"],
            "type": mt5.ORDER_TYPE_BUY,
            "price": order_price,
            "position": row["ticket"]
            }


        mt5.order_send(request)
        
        create_log(f"Close position {row['ticket']} at {order_price}")


def history_data(symbol="EURUSD", period=mt5.TIMEFRAME_M5, ticks=70):
    """This method return the historical dataframe of a forex pair, the default symbol is EURUSD"""

    data = pd.DataFrame(mt5.copy_rates_from_pos(symbol, period, 0, ticks))

    data['time'] = pd.to_datetime(data['time'], unit='s')
    data['hours'] = [i.hour for i in data.time]
    data['day'] = [i.day for i in data.time]
    data['weekday'] = [i.weekday() for i in data.time]
    data['tick_size'] = data['high'] - data['low']

    return data

def avoid_SWAP(data, open_position):
    """Avoid SWAP Expensed and don't trade at this time"""
    if (data.time[1].weekday() in [1, 2]) & (data.time[1].hour == 23):
        if open_position is not None:
            pending_trade = open_position['type'][0]
            close_position(open_position)
            create_log("Avoiding SWAP fee, Close position")

            # wait till next day continue trading
            time.sleep(3605 - datetime.now().minute * 60 - datetime.now().second)

            data = history_data(symbol="EURUSD", ticks=2, period=mt5.TIMEFRAME_H1)

            if pending_trade == 0:
                place_order('EURUSD', "long", data.close[0])
            
            else:
                place_order('EURUSD', "short", data.close[0])
        
        else:
            time.sleep(3605 - datetime.now().minute * 60 - datetime.now().second)
        
        return True
    
    return False


def create_log(msg, debug=False):
    """This function create the basic log file to check the system is working normally"""
    if debug:
        logging.basicConfig(
        filename="trading_log.log",
        level=logging.DEBUG,
        filemode="a",
        format="%(asctime)s: %(levelname)s : %(message)s",
        datefmt="%m/%d/%Y %I:%M:%S %p ",
    )
    else:
        logging.basicConfig(
            filename="trading_log.log",
            level=logging.INFO,
            filemode="a",
            format="%(asctime)s: %(levelname)s : %(message)s",
            datefmt="%m/%d/%Y %I:%M:%S %p ",
        )
    
    logging.info(msg)


def modifyTP(open_position, close_price):
    """Modify position take profit price"""
    
    code = 0

    for _, row in open_position.iterrows():
            
        if row['type'] == 0:
            request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "symbol": row['symbol'],
            "type": mt5.ORDER_TYPE_SELL,
            "tp": close_price + float(os.environ['ADD_PIP']),
            "position": row["ticket"]
            }
        
        else:
            request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "symbol": row['symbol'],
            "type": mt5.ORDER_TYPE_BUY,
            "tp": close_price - float(os.environ['ADD_PIP']),
            "position": row["ticket"]
            }
        
        while code !=  mt5.TRADE_RETCODE_DONE:

            code = mt5.order_send(request).retcode

            if code ==  mt5.TRADE_RETCODE_DONE:
                break
        
        create_log(f"Modify position {row['ticket']} : {request}")

def remove_order():
    """Remove pending orders"""

    code = 0

    request = {
    "action": mt5.TRADE_ACTION_REMOVE,
    "order": mt5.orders_get()[0][0]
    }

    while code !=  mt5.TRADE_RETCODE_DONE:

        code = mt5.order_send(request).retcode

        if code ==  mt5.TRADE_RETCODE_DONE:
            break
    
    create_log(f"Removed Pending Order: {request}")

def yourstrategy(symbol='EURUSD', timeframe=mt5.TIMEFRAME_H1):
    pass



