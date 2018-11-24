# -*- coding: utf-8 -*-
import argparse
import codecs
import os
import sys
import traceback

import psutil

from instabot import Bot
from instabot.api import api_db
from instabot.bot.bot_profile_crawler import BotProfileCrawler

stdout = sys.stdout
sys.stdout = codecs.getwriter('utf8')(sys.stdout)
sys.path.append(os.path.join(sys.path[0], '../'))

parser = argparse.ArgumentParser(add_help=True)
parser.add_argument('-angie_campaign', type=str, help="angie_campaign")
args = parser.parse_args()

#args.angie_campaign = 1

if args.angie_campaign is None:
    exit("dispatcher: Error: Campaign id it is not specified !")


def canProcessStart(processName):
    timesStarted = 0

    for p in psutil.process_iter():
        cmdline = p.cmdline()
        if len(cmdline) > 1:
            if processName in cmdline[0]:
                timesStarted = timesStarted + 1

    if timesStarted > 1:
        return False
    else:
        return True


try:

    campaign = api_db.fetchOne(
        "select username,password,campaign.timestamp,id_campaign,id_user, bot_type from campaign where id_campaign=%s",
        args.angie_campaign)

    if campaign is None:
        raise Exception("Could not find campaign for bot user %s", campaign['username'])

    if campaign['bot_type'] != "profile_crawler":
        raise Exception(
            "Error: user %s is not a profile_crawler bot, is: %s" % (campaign['username'], campaign['bot_type']))

    bot = Bot(
        id_campaign=str(campaign['id_campaign']),
        multiple_ip=True,
        bot_type="scan_user_profile"
    )

    processName = "angie_scan_users_profile_" + str(campaign['id_campaign'])
    bot.logger.info("angie_scan_users_profile_: checking if there is already a process started with name: %s",
                    processName)
    canStart = canStart = canProcessStart(processName)


    if not canStart:
        raise Exception("Error: there is already a  process with name %s. Going to exit", processName)
    else:
        bot.logger.info("scan_user_profile: All good no other %s process is running.", processName)

    status = bot.login(username=campaign['username'], password=campaign['password'], storage=False)

    if not status:
        bot.logger.info("scan_user_profile: Could not login, going to exit !")
        exit()

    crawler = BotProfileCrawler(bot, campaign)
    crawler.scanUsers()

    bot.logger.info("DONE SCANNING USERS, GOING TO CLOSE THE APP !")

except:
    exceptionDetail = traceback.format_exc()
    print(exceptionDetail)
    bot.logger.info("FATAL ERROR !")
    bot.logger.info(exceptionDetail)
