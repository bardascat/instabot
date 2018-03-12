# -*- coding: utf-8 -*-
import argparse
import codecs
import os
import sys
import traceback
import psutil
import time

from instabot import Bot
from instabot.api import api_db

stdout = sys.stdout
sys.stdout = codecs.getwriter('utf8')(sys.stdout)
sys.path.append(os.path.join(sys.path[0], '../'))

parser = argparse.ArgumentParser(add_help=True)
args = parser.parse_args()


def canProcessStart(processName):
    timesStarted=0

    for p in psutil.process_iter():
        cmdline = p.cmdline()
        if len(cmdline) > 1:
            if processName in cmdline[0]:
                timesStarted=timesStarted+1

    if timesStarted>1:
        return False
    else:
        return True

try:
    
    bot_username="johncryansnow"
    campaign = api_db.fetchOne("select username,password,timestamp,id_campaign from campaign where username=%s",bot_username)
    if campaign is None:
        raise Exception("Could not find campaign for bot user %s", bot_username)
    
    bot = Bot(
        id_campaign=str(campaign['id_campaign']),
        multiple_ip=True,
        bot_type="scan_user_feed"
    )

    processName = "angie_scan_user_feed" + str(campaign['id_campaign'])
    bot.logger.info("angie_scan_user_feed: checking if there is already a process started with name %s", processName)
    canStart = canProcessStart(processName)

    if not canStart:
        raise Exception("Error: there is already a  process with name %s. Going to exit", processName)
    else:
        bot.logger.info("scan_user_feed: All good no other process is running.")

    while True:
        status = bot.login(username=campaign['username'], password=campaign['password'])
    
        if not status:
            bot.logger.info("scan_user_feed: Could not login, going to exit !")
            exit()
    
        bot.startScanUserFeed()
        
    

except SystemExit:
    bot.logger.info("like_for_like: SystemExit: The angie_scan_user_feed process was successfully stopped")
except:
    exceptionDetail = traceback.format_exc()
    print(exceptionDetail)
    bot.logger.info("FATAL ERROR !")
    bot.logger.info(exceptionDetail)