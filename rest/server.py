"""
Main module of the server file
"""
import json
# -*- coding: utf-8 -*-
import traceback

from flask import Flask

from instabot import Bot
from instabot.api import api_db

id_campaign="1"
bot = Bot(
    id_campaign=id_campaign,
    max_likes_per_day=3100,  # default 1000
    like_delay=40,
    like_delay_if_bot_blocked=160,
    multiple_ip=True
)

campaign = api_db.fetchOne("select username,password,timestamp,id_campaign from campaign where id_campaign=%s",id_campaign)

status = bot.login(username=campaign['username'], password=campaign['password'], storage=False)

# Create the application instance
app = Flask(__name__)

# create a URL route in our application for "/"
@app.route('/')
def home():
    return "ANGIE PYTHON REST API"


@app.route('/api/posts/hashtag')
def hashtag():

    print("getting data")

    global bot
    try:
        posts = bot.getHashtagFeed(hashtagString="pantofi", amount=10,
                                    id_campaign=1,
                                    removeLikedPosts=False,
                                    removeFollowedUsers=False)
    except Exception as exc:
        exceptionDetail = traceback.format_exc()
        print(exceptionDetail)

    return json.dumps(posts)


@app.route('/api/posts/location')
def location():
    global bot


    posts = bot.getHashtagFeed(hashtagString="ronaldo", amount=10,
                                id_campaign=1,
                                removeLikedPosts=False,
                                removeFollowedUsers=False)

    return json.dumps(posts)



if __name__ == '__main__':
    app.run(debug=False, port=50001,threaded=True)
