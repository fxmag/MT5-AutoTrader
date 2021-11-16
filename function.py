#!/usr/bin/env python
# -*- coding: utf-8 -*-
#--------------------------------#
"""
File name: function.py
Author: WEI-TA KUAN
Date created: 9/10/2021
Date last modified: 12/11/2021
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
import requests
import time
import pickle
import joblib
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
    data['RollingVol'] = data.iloc[:, 5].rolling(window=int(os.environ['ROLLVOL'])).mean()
    
    # calculate the changing rate
    for index, row in data.iterrows():
        try:
            data.at[index, 'change'] = row['MovingAverage']/data.at[index -1, 'MovingAverage']
            data.at[index, 'vol_change'] = row['RollingVol']/data.at[index -1, 'RollingVol']
        except:
            pass

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

def PlaceOrder(types, symbol='EURUSD', lot=1.0):
    """This function help placing order in MT5"""

    if types == 'long':
        request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot,
        "type": mt5.ORDER_TYPE_BUY,
        "price": mt5.symbol_info_tick(symbol).ask,
        'magic':int(os.environ['BOT'])
        }
    else:
        request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot,
        "type": mt5.ORDER_TYPE_SELL,
        "price": mt5.symbol_info_tick(symbol).bid,
        'magic':int(os.environ['BOT'])
        }
    
    if OrderChecker(request):
        
        create_log(f'Order Placed Successful - {types}')
        
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

def AvoidSwap():
    """Avoid SWAP Fee Expensed and don't trade at this time"""
    
    # Get existed position
    opened = mt5.positions_get()

    # If there is existing position, check the condition for SWAP avoiding
    if len(opened) != 0:

        opened = opened[0]._asdict()

        # keeping pending trade
        pending_trade = opened['type'] 

        # only avoid swap for long position, check contract size
        if pending_trade == 0:                

            # close long position
            ClosePosition(opened)
            
            # create log record
            create_log("SWAP Fee Avoid Success")

            # wait till next day continue the remaining trading
            time.sleep(3605 - datetime.now().minute * 60 - datetime.now().second)

            PlaceOrder("long")

            # update the existing position
            opened = mt5.positions_get()[0]._asdict()

        else:
            time.sleep(3605 - datetime.now().minute * 60 - datetime.now().second)
    
    else:
        # set opened to None
        opened = None

        time.sleep(3605 - datetime.now().minute * 60 - datetime.now().second)
    
    return HistoricalData(ticks=12).iloc[-2:,:].reset_index(), opened
        
 
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
def StopLoss(opened):
    """This function check the stop loss condition had met or not"""
    reference = HistoricalData(ticks=9)

    # Condition met, close position and open another position
    if reference.iloc[-2].change < float(os.environ['SL_THRESHOLD']) and opened['profit'] < 0:
        
        ClosePosition(opened)
        
        PlaceOrder('short')
    
    # update existed position
    return mt5.positions_get()[0]._asdict()
