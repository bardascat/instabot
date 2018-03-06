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
        max_unlikes_per_day=500,  # default 1000
        max_follows_per_day=800,  # default 350
        max_unfollows_per_day=800,  # default 350
        max_comments_per_day=0,
        max_followers_to_follow=9000000,  # default 2000
        min_followers_to_follow=10,  # default 10
        max_following_to_follow=9000000,  # default 2000
        min_following_to_follow=10,  # default 10
        max_following_to_followers_ratio=4,  # default 2
        min_media_count_to_follow=20,  # default 3
        like_delay=35,  # default 10,
        like_delay_if_bot_blocked=70,
        unlike_delay=15,  # default 1-
        follow_delay=60,  # default 30,
        unfollow_delay=40,  # default 30,
        multiple_ip=True
    )

    campaign = api_db.fetchOne("select username,password,timestamp,id_campaign from campaign where id_campaign=%s",
                               args.angie_campaign)
    bot.canBotStart(args.angie_campaign)
    status = bot.login(username=campaign['username'], password=campaign['password'])
    u={}
    u['username']='mcmoris'
    u['instagram_id_user']=1778632774
    bot.follow(u)
    if status != True:
        bot.logger.info("dispatcher: Could not login, going to exit !")
        exit()

except SystemExit:
    bot.logger.info("dispatcher_v2: SystemExit: The bot was successfully stopped")
except:
    exceptionDetail = traceback.format_exc()
    #print(exceptionDetail)
    bot.logger.info("FATAL ERROR !")
    bot.logger.info(exceptionDetail)
