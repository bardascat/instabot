# -*- coding: utf-8 -*-
import argparse
import codecs
import os
import sys
import json
from instabot.api import api_db
from instabot import Bot

stdout = sys.stdout
sys.stdout = codecs.getwriter('utf8')(sys.stdout)
sys.path.append(os.path.join(sys.path[0], '../'))

parser = argparse.ArgumentParser(add_help=True)
parser.add_argument('-id_campaign', type=str, help="campaign")
parser.add_argument('-instagramUsername', type=str, help="instagramUsername")
args = parser.parse_args()

if not args.id_campaign:
    exit(0)

campaign = api_db.fetchOne("select username,password,timestamp,id_campaign from campaign where id_campaign=%s",
                           args.id_campaign)

bot = Bot(id_campaign=args.id_campaign, multiple_ip=True, hide_output=True)
bot.logger.info("get_user_info: Going to get user info for username: %s" % (args.instagramUsername))

status = bot.login(username=campaign['username'], password=campaign['password'])
if status != True:
    print(bot.LastResponse.text)
    exit()

userId = bot.get_userid_from_username(args.instagramUsername)
bot.logger.info("Userid for username %s is: %s" % (args.instagramUsername, userId))
if userId is None:
  data={}
  data['error']="Username "+args.instagramUsername+" does no exist !"
else:
  userInfo = bot.get_user_info(userId)
  bot.logger.info("get_user_info: Followers count: %s", userInfo['follower_count'])
  data={}
  data['followers_count']=userInfo['follower_count']
  
result = json.dumps(data)
print(result)
