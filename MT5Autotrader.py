#!/usr/bin/env python
# -*- coding: utf-8 -*-
#--------------------------------#
"""
File name: MT5Autotrader.py
Author: WEI-TA KUAN
Date created: 9/10/2021
Date last modified: 3/11/2021
Version: 3.1
Python Version: 3.8.8
Status: Developing
"""
#--------------------------------#

from strategy import *


mt5.initialize()

while True:

    try:

        strategy()

        second = 3605 - datetime.now().minute * 60 - datetime.now().second
        
        time.sleep(second)

    # error handling
    except Exception as e:

        create_log(e, debug=True)

        lineNotifyMessage(os.environ['LINE_TOKEN'], e)



