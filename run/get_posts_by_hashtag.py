# -*- coding: utf-8 -*-
import argparse
import codecs
import os
import sys
import json
from instabot.api import api_db
from instabot import Bot
import traceback

stdout = sys.stdout
sys.stdout = codecs.getwriter('utf8')(sys.stdout)
sys.path.append(os.path.join(sys.path[0], '../'))

parser = argparse.ArgumentParser(add_help=True)
parser.add_argument('-id_bot', type=str, help="id_bot")
parser.add_argument('-id_campaign', type=str, help="the users that needs this data")
parser.add_argument('-hashtag', type=str, help="hashtag")
parser.add_argument('-amount', type=str, help="amount")
parser.add_argument('-removeLikedPosts', type=str, help="removeLikedPosts")
parser.add_argument('-removeFollowedUsers', type=str, help="removeFollowedUsers")
args = parser.parse_args()
args.removeLikedPosts = args.removeLikedPosts == 'true'
args.removeFollowedUsers = args.removeFollowedUsers == 'true'
args.amount = int(args.amount)

# args.id_campaign = "1"
# args.id_campaign = "1"
# args.hashtag = "dcshoes"
# args.removeLikedPosts = True
# args.removeFollowedUsers = True
# args.amount = 150

try:
    if not args.id_campaign:
        exit(0)

    campaign = api_db.fetchOne("select username,password,timestamp,id_campaign from campaign where id_campaign=%s",
                               args.id_bot)

    bot = Bot(id_campaign=args.id_bot, multiple_ip=True, hide_output=True)
    bot.logger.info("get_posts_by_hashtag: Going to get posts for hashtag %s" % (args.hashtag))

    result = {}

    # todo -> to improve a bit the speed set force to True
    status = bot.login(username=campaign['username'], password=campaign['password'], storage=False, force=False)
    if status != True:
        result["error"] = bot.LastResponse.text
        print(json.dumps(result))

    posts = bot.getHashtagFeed(hashtagString=args.hashtag, amount=args.amount,
                               id_campaign=args.id_campaign,
                               removeLikedPosts=args.removeLikedPosts,
                               removeFollowedUsers=args.removeFollowedUsers)

    parsedPosts = []
    for post in posts:
        parsedPosts.append({'code': post['code'],
                            'user': post['user']['username'],
                            'link': 'https://www.instagram.com/p/' + post['code'] + '/',
                            'pk': post['p']})

    print(json.dumps(parsedPosts))

except:
    result = {}
    exceptionDetail = traceback.format_exc()
    result['error'] = exceptionDetail
    print(json.dumps(result))
