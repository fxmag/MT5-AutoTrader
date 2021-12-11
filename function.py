#!/usr/bin/env python
# -*- coding: utf-8 -*-
#--------------------------------#
"""
File name: function.py
Author: WEI-TA KUAN
Date created: 9/10/2021
Date last modified: 11/12/2021
Version: 4.0
Python Version: 3.8.8
Status: Developing
"""
#--------------------------------#

from datetime import datetime
from json.decoder import JSONDecodeError
from dotenv import load_dotenv, find_dotenv, set_key
import MetaTrader5 as mt5
import dotenv
import pandas as pd
import numpy as np
import requests
import time
import pickle
from json import dumps, loads
import logging
import os

load_dotenv()

#================= Historical Data ==================

def HistoricalData(symbol="EURUSD", period=mt5.TIMEFRAME_H1, ticks=70):
    """This method return the historical dataframe of a forex pair, the default symbol is AUDUSD"""

    data = pd.DataFrame(mt5.copy_rates_from_pos(symbol, period, 0, ticks))

    data['time'] = pd.to_datetime(data['time'], unit='s')
    data['hour'] = [i.hour for i in data.time.tolist()]
    data['MovingAverage'] = data.iloc[:, 4].rolling(window=int(os.environ["MOVAVG"])).mean()
    data['MovingAverage_2'] = data.iloc[:, 4].rolling(window=int(os.environ["MOVAVG_2"])).mean()
    data['RollingVol'] = data.iloc[:, 5].rolling(window=int(os.environ['ROLLVOL'])).mean()
    data['Bias'] = (data['close'] - data['MovingAverage_2']) / data['MovingAverage_2']
    
    # calculate the changing rate
    for index, row in data.iterrows():
        try:
            data.at[index, 'change'] = row['MovingAverage']/data.at[index -1, 'MovingAverage']
            data.at[index, 'vol_change'] = row['RollingVol']/data.at[index -1, 'RollingVol']
        except:
            pass
    
    data = stohastic_oscillator(data, int(os.environ['K']), int(os.environ['D']))
    data['KDR'] = data['K'] - data['D'] 

    return data

# ========== Order Helper Function =================
def OrderChecker(request):
    """This function check the order had sent correctly or not"""
    success = None
    
    while success != mt5.TRADE_RETCODE_DONE:
        
        success = mt5.order_send(request).retcode
        
        if success == mt5.TRADE_RETCODE_DONE:
            
            break

    return True

def PlaceOrder(types, comment, symbol='EURUSD', lot=0.5):
    """This function help placing order in MT5"""

    if types == 'long':
        request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot,
        "type": mt5.ORDER_TYPE_BUY,
        "price": mt5.symbol_info_tick(symbol).ask,
        'magic':int(os.environ['BOT']),
        'comment':comment
        }
    else:
        request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot,
        "type": mt5.ORDER_TYPE_SELL,
        "price": mt5.symbol_info_tick(symbol).bid,
        'magic':int(os.environ['BOT']),
        'comment':comment
        }

    # make sure there is only one position opened
    if len(mt5.positions_get()) == 0:
        if OrderChecker(request):
            
            create_log(f'Order Placed Successful - {types}')
    else:
        create_log(f'Exceed Order Limit', debug=True)
        
def ClosePosition(opened):
    """This function is for closing all the existing position 
    by sending signal to place_order function"""

    if opened['type'] == 0:
        request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": opened['symbol'],
        "volume": opened["volume"],
        "type": mt5.ORDER_TYPE_SELL,
        "price":  mt5.symbol_info_tick(opened['symbol']).bid,
        "position": opened["ticket"]
        }
    else:
        request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": opened['symbol'],
        "volume": opened["volume"],
        "type": mt5.ORDER_TYPE_BUY,
        "price": mt5.symbol_info_tick(opened['symbol']).ask,
        "position": opened["ticket"]
        }
    if OrderChecker(request):
        create_log(f'Order Closed Successful - {opened["ticket"]}')


# ========== SWAP =================

def AvoidSwap(opened):
    """Avoid SWAP Fee Expensed and don't trade at this time"""

    # only avoid swap for long position, check contract size
    if opened['type'] == 0:

        # close long position
        ClosePosition(opened)

        # create log record
        create_log("SWAP Fee Avoid Success")

        opened = None

        # save the trade
        pending = True
    
    return opened, pending
        
 
# =========== Trading Information ==============
def create_log(msg, debug=False):
    """This function create the basic log file to check 
        the system is working normally"""

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


# =========== Stop Loss ==============
def StopLoss(opened, position):
    """This function check the stop loss condition had met or not"""
    reference = HistoricalData(ticks=50)

    # Condition met, close position and open another position
    if position == 0:
        if reference.iloc[-2].Bias < float(os.environ['SL_THRESHOLD_2']) * -1 and opened['K'] < int(os.environ['SL_THRESHOLD_3']):
            
            ClosePosition(opened)
            
            PlaceOrder('short', os.environ['STOPLOSS'])
    else:
        if reference.iloc[-2].KDR > int(os.environ["SL_THRESHOLD"]) and opened['profit'] < 0:

            ClosePosition(opened)

            return None

    
    # update existed position
    return mt5.positions_get()[0]._asdict()


# =========== Technical Indicator =============
def stohastic_oscillator(data, k, d):
    data['highest'] = data['high'].rolling(k).max()
    data['lowest'] = data['low'].rolling(k).min()
    data['K'] = (data['close'] - data['lowest']) * 100 / (data['highest'] - data['lowest'])
    data['D'] = data['K'].rolling(d).mean()
    return data

# =========== Store Environmental Variable =============
def EnvValue(key, write_value=None, write=False):
    env_file = find_dotenv()
    load_dotenv(env_file)

    if write:
        if isinstance(write_value, dict):
            os.environ[key] = dumps(write_value)
        else:
            os.environ[key] = write_value
        set_key(env_file, key, os.environ[key])
    
    else:
        try:
            value = loads(os.environ[key])
        except JSONDecodeError:
            value = os.environ[key]
        
        return value

    return write_value
