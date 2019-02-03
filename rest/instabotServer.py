"""
Main module of the server file
"""
from random import randint
from time import sleep
import json
# -*- coding: utf-8 -*-
import traceback

from flask import Flask
from flask import request
from instabot import Bot
from instabot.api import api_db

id_bot = "401"
bot = Bot(
    id_campaign=id_bot,
    max_likes_per_day=3100,  # default 1000
    like_delay=40,
    like_delay_if_bot_blocked=160,
    multiple_ip=True
)
campaign = api_db.fetchOne("select username,password,timestamp,id_campaign from campaign where id_campaign=%s", id_bot)

# wait a few seconds between gunicorn workers
seconds = randint(1, 15)
bot.logger.info("Sleeping %s seconds before starting.", seconds)
sleep(seconds)

status = bot.login(username=campaign['username'], password=campaign['password'], storage=False)

# Create the application instance
app = Flask(__name__)


# create a URL route in our application for "/"
@app.route('/')
def home():
    print("this is home")
    return "ANGIE PYTHON REST API"

@app.route('/api/status')
def status():
    status = {"status": "up"}
    return status

@app.route('/api/posts/hashtag')
def hashtag():
    global bot
    try:
        hashtag = request.args.get('hashtag')
        amount = request.args.get('amount')
        id_campaign = request.args.get('id_campaign')
        removeLikedPosts = request.args.get('removeLikedPosts')
        removeFollowedUsers = request.args.get('removeFollowedUsers')
        removeLikedPosts = removeLikedPosts == 'true'
        removeFollowedUsers = removeFollowedUsers == 'true'
        amount = int(amount)

        feed = bot.getHashtagFeed(hashtagString=hashtag, amount=amount,
                                  id_campaign=id_campaign,
                                  removeLikedPosts=removeLikedPosts,
                                  removeFollowedUsers=removeFollowedUsers)

        result = []
        for post in feed:
            result.append({'code': post['code'],
                           'user': post['user']['username'],
                           'link': 'https://www.instagram.com/p/' + post['code'] + '/',
                           'pk': post['pk']})

    except Exception as exc:
        exceptionDetail = traceback.format_exc()
        bot.logger.info("hashtag: exception while getting hahtags: %s", exceptionDetail)
        result['error'] = exceptionDetail

    return json.dumps(result)


@app.route('/api/posts/location')
def location():
    global bot
    try:
        locationId = request.args.get('id_location')
        amount = request.args.get('amount')
        id_campaign = request.args.get('id_campaign')
        removeLikedPosts = request.args.get('removeLikedPosts')
        removeFollowedUsers = request.args.get('removeFollowedUsers')
        removeLikedPosts = removeLikedPosts == 'true'
        removeFollowedUsers = removeFollowedUsers == 'true'
        amount = int(amount)

        feed = bot.getLocationFeed(locationId=locationId, amount=amount,
                                   id_campaign=id_campaign,
                                   removeLikedPosts=removeLikedPosts,
                                   removeFollowedUsers=removeFollowedUsers)
        result = []
        for post in feed:
            result.append({'code': post['code'],
                           'user': post['user']['username'],
                           'link': 'https://www.instagram.com/p/' + post['code'] + '/',
                           'pk': post['pk']})


    except Exception as exc:
        exceptionDetail = traceback.format_exc()
        bot.logger.info("location:exception while getting locations: %s", exceptionDetail)
        result['error'] = exceptionDetail

    return json.dumps(result)


if __name__ == '__main__':
    app.run(debug=True, port=50001, threaded=False)
