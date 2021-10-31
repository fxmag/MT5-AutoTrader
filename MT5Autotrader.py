#!/usr/bin/env python
# -*- coding: utf-8 -*-
#--------------------------------#
"""
File name: MT5Autotrader.py
Author: WEI-TA KUAN
Date created: 9/10/2021
Date last modified: 31/10/2021
Version: 3.1
Python Version: 3.8.8
Status: Developing
"""
#--------------------------------#

from strategy import *


mt5.initialize()

while True:

    strategy()

    second = 3605 - datetime.now().minute * 60 - datetime.now().second
    
    time.sleep(second)



