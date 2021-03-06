#!/usr/bin/env python
# -*- coding: utf-8 -*-
#--------------------------------#
"""
File name: MT5Autotrader.py
Author: WEI-TA KUAN
Date created: 9/10/2021
Date last modified: 18/11/2021
Version: 4.0
Python Version: 3.8.8
Status: Developing
"""
#--------------------------------#

from strategy import *

mt5.initialize('C:/Program Files/ForexTime (FXTM) MT5/terminal64.exe')

# check everything up to date
time.sleep(10)

create_log("System Activated, Start Making Profit")

notify = True

while True:

    try:

        strategy()

        second = 3603 - datetime.datetime.now().minute * 60 - datetime.datetime.now().second
        
        time.sleep(second)

    # error handling
    except Exception as e:

        create_log(e, debug=True)

        mt5.shutdown()

        time.sleep(10)

        mt5.initialize('C:/Program Files/ForexTime (FXTM) MT5/terminal64.exe')

        continue



