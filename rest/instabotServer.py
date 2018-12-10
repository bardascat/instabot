"""
Main module of the server file
"""
from random import randint
from time import sleep
import json
# -*- coding: utf-8 -*-
import traceback

from flask import Flask

from instabot import Bot
from instabot.api import api_db

seconds=randint(1,15)

id_campaign="3"
bot = Bot(
    id_campaign=id_campaign,
    max_likes_per_day=3100,  # default 1000
    like_delay=40,
    like_delay_if_bot_blocked=160,
    multiple_ip=True
)

campaign = api_db.fetchOne("select username,password,timestamp,id_campaign from campaign where id_campaign=%s",id_campaign)
bot.logger.info("Sleeping %s seconds before starting.",  seconds)
status = bot.login(username=campaign['username'], password=campaign['password'], storage=False)

#Create the application instance
app = Flask(__name__)

# create a URL route in our application for "/"
@app.route('/')
def home():
    print("this is home")
    return "ANGIE PYTHON REST API"


@app.route('/api/posts/hashtag')
def hashtag():

    print("getting data")

    global bot
    try:
        posts = bot.getHashtagFeed(hashtagString2="pantofi", amount=10,
                                    id_campaign=1,
                                    removeLikedPosts=False,
                                    removeFollowedUsers=False)
    except Exception as exc:
        exceptionDetail = traceback.format_exc()
        bot.logger.info("exception: %s", exceptionDetail)

    return json.dumps(posts)


@app.route('/api/posts/location')
def location():
    global bot


    posts = bot.getHashtagFeed(hashtagStringx="ronaldo", amount=10,
                                id_campaign=1,
                                removeLikedPosts=False,
                                removeFollowedUsers=False)

    return json.dumps(posts)



if __name__ == '__main__':
    app.run(debug=True, port=50001,threaded=False)
