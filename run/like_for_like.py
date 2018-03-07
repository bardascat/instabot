# -*- coding: utf-8 -*-
import argparse
import os
import sys
import codecs
from instabot import Bot
import traceback
from instabot.api import api_db
import math
from datetime import datetime
from random import randint
import time

stdout = sys.stdout
sys.stdout = codecs.getwriter('utf8')(sys.stdout)
sys.path.append(os.path.join(sys.path[0], '../'))

parser = argparse.ArgumentParser(add_help=True)
parser.add_argument('-angie_campaign', type=str, help="angie_campaign")
args = parser.parse_args()

if args.angie_campaign is None:
    exit("dispatcher: Error: Campaign id it is not specified !")

try:
    bot = Bot(
        id_campaign=args.angie_campaign,
        max_likes_per_day=3100,  # default 1000
        like_delay=40,
        like_delay_if_bot_blocked=160,
        multiple_ip=True
    )

    campaign = api_db.fetchOne("select username,password,timestamp,id_campaign from campaign where id_campaign=%s",
                               args.angie_campaign)
    #bot.canBotStart(args.angie_campaign)
    #todo change the log file(make a setter)
    status = bot.login(username=campaign['username'], password=campaign['password'])

    if status != True:
        bot.logger.info("dispatcher: Could not login, going to exit !")
        exit()
    
    bot.startLikeForLike()
    
   
except SystemExit:
    bot.logger.info("dispatcher_v2: SystemExit: The like for like process was successfully stopped")
except:
    exceptionDetail = traceback.format_exc()
    #print(exceptionDetail)
    bot.logger.info("FATAL ERROR !")
    bot.logger.info(exceptionDetail)
