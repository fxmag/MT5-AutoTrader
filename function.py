#!/usr/bin/env python
# -*- coding: utf-8 -*-
#--------------------------------#
"""
File name: function.py
Author: WEI-TA KUAN
Date created: 9/10/2021
Date last modified: 31/10/2021
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

def place_order(symbol, type, lot=1.0):
    """This function create buy and sell order in MT5 platform, the default lot is 1"""
    code = 0

    # Place buy order
    if type == "long":
        request = {
        "action": mt5.TRADE_ACTION_PENDING,
        "symbol": symbol,
        "volume": lot,
        "type": mt5.ORDER_TYPE_BUY_LIMIT,
        "price": mt5.symbol_info_tick(symbol).ask - os.environ['ADD_PIP']
        }

    elif type == "short":
        request = {
        "action": mt5.TRADE_ACTION_PENDING,
        "symbol": symbol,
        "volume": lot,
        "type": mt5.ORDER_TYPE_SELL_LIMIT,
        "price": mt5.symbol_info_tick(symbol).bid + os.environ['ADD_PIP']
        }
    
    while code != 10009:

        code = mt5.order_send(request).retcode

        if code == 10009:
            break
    
    create_log(f"Open {type} pending position")

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
    if (data.time[1].weekday() == 2) & (data.time[1].hour == 23):
        if open_position is not None:
            pending_trade = open_position['type'][0]
            close_position(open_position)
            create_log("Avoiding SWAP fee, Close position")

            # wait till next day continue trading
            time.sleep(3605 - datetime.now().minute * 60 - datetime.now().second)

            if pending_trade == 0:
                place_order('EURUSD', "long")
            
            else:
                place_order('EURUSD', "short")
        
        else:
            time.sleep(3605 - datetime.now().minute * 60 - datetime.now().second)


def create_log(msg):
    """This function create the basic log file to check the system is working normally"""
    logging.basicConfig(
        filename="trading_log.log",
        level=logging.INFO,
        filemode="a",
        format="%(asctime)s: %(levelname)s : %(message)s",
        datefmt="%m/%d/%Y %I:%M:%S %p ",
    )
    
    logging.info(msg)

def yourstrategy(symbol='EURUSD', timeframe=mt5.TIMEFRAME_H1):
    pass

