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
parser.add_argument('-angie_campaign', type=str, help="angie_campaign")
parser.add_argument('-bot_process_pid', type=str, help="bot_process_pid")
args = parser.parse_args()


def canProcessStart(processName):
    timesStarted=0

    for p in psutil.process_iter():
        cmdline = p.cmdline()
        if len(cmdline) > 1:
            if processName==cmdline[0]:
                timesStarted=timesStarted+1

    if timesStarted>1:
        return False
    else:
        return True

if args.angie_campaign is None:
    exit("dispatcher: Error: Campaign id it is not specified !")

try:
    bot = Bot(
        id_campaign=args.angie_campaign,
        max_likes_per_day=3100,  # default 1000
        like_delay=50,
        like_delay_if_bot_blocked=50,
        multiple_ip=True,
        bot_type="like_for_like"
    )
 
    campaign = api_db.fetchOne("select username,password,timestamp,id_campaign from campaign where id_campaign=%s",
                               args.angie_campaign)

    processName = "angie_like_for_like_idc" + str(args.angie_campaign)
    bot.logger.info("like_for_like: checking if there is already a process started with name %s", processName)
    canStart = canProcessStart(processName)

    if not canStart:
        raise Exception("Error: there is already a like for like process with name %s. Going to exit", processName)

    status = bot.login(username=campaign['username'], password=campaign['password'], logoutFlag=False)

    if not status:
        bot.logger.info("like_for_like: Could not login, going to exit !")
        exit()

    bot.startLikeForLike()

except SystemExit:
    bot.logger.info("like_for_like: SystemExit: The like for like process was successfully stopped")
except:
    exceptionDetail = traceback.format_exc()
    # print(exceptionDetail)
    bot.logger.info("FATAL ERROR !")
    bot.logger.info(exceptionDetail)
finally:
    print("trying to resume bot process: pid is " + args.bot_process_pid)
    if args.bot_process_pid is not None and args.bot_process_pid is not False:
        try:
            pid = int(float(args.bot_process_pid))
            p = psutil.Process(pid)
            p.resume()
            bot.logger.info("Bot process %s is resumed", args.bot_process_pid)
        except ValueError:
            print "Bot Process pid is not a valid number"
            bot.logger.info("Bot process pid %s is not a valid number", args.bot_process_pid)
    else:
        bot.logger.info("There is no bot process to resume, going to exit !")
