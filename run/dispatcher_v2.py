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
        like_delay=50,
        like_delay_if_bot_blocked=100,
        follow_delay_if_bot_blocked=110,
        follow_delay=70,  # default 30,
        unfollow_delay=70,  # default 30,
        multiple_ip=True
    ) 

    campaign = api_db.fetchOne("select username,password,timestamp,id_campaign from campaign where id_campaign=%s",
                               args.angie_campaign)
    bot.canBotStart(args.angie_campaign)
    status = bot.login(username=campaign['username'], password=campaign['password'], storage=False)
    if status != True:
        bot.logger.info("dispatcher: Could not login, going to exit !")
        exit()

    calculatedAmount = bot.getAmountDistribution(args.angie_campaign)

    totalExpectedLikesAmount = int(bot.getLikeAmount(args.angie_campaign, calculatedAmount))
    totalExpectedFollowAmount = int(bot.getFollowAmount(args.angie_campaign, calculatedAmount))

    
    bot.like_delay = bot.get_like_delay(totalExpectedLikesAmount)
    bot.follow_delay = bot.get_follow_delay(totalExpectedFollowAmount)
    
    
    bot.logger.info("dispatcher: Initial calculated Amount(SOD): %s, totalExpectedLike:%s, totalExpectedFollow: %s" % (
    calculatedAmount, totalExpectedLikesAmount, totalExpectedFollowAmount))

    numberOfIterations = randint(13, 15)
    pauses = [3, 5, 8, 11]
    bot.logger.info("DISPATCHER: Daily pause are set for iteration %s", pauses)
    currentIteration = 1

    totalPerformedLikes = int(bot.getLikesPerformed(datetime.today().date()))
    totalPerformedFollows = int(bot.getFollowPerformed(datetime.today().date()))

    securityBreak = 30
    startingDate = datetime.now().date()

    bot.logger.info("DISPATCHER: Started bot, going to perform %s likes, %s follow/unfollow during %s iterations" % (
    totalExpectedLikesAmount, totalExpectedFollowAmount, numberOfIterations))

    while (
            totalPerformedLikes < totalExpectedLikesAmount or totalPerformedFollows < totalExpectedFollowAmount) and currentIteration < securityBreak and startingDate.day == datetime.now().date().day:
        if currentIteration in pauses:
            dailyPause = randint(10, 30)
            bot.logger.info("dispatcher: Daily pause of %s minutes at iteration: %s" % (dailyPause, currentIteration))
            time.sleep(dailyPause * 60)

        currentIterationPerformedLikes = 0

        # if no more likes needed to perform
        if totalExpectedLikesAmount <= totalPerformedLikes:
            currentIterationLikeAmount = 0
        else:
            currentIterationLikeAmount = int(math.ceil(math.ceil(totalExpectedLikesAmount) / math.ceil(numberOfIterations)))
                
    
        # if no more follows are needed
        if totalExpectedFollowAmount <= totalPerformedFollows:
            currentIterationFollowAmount = 0
        else:
            currentIterationFollowAmount = int(math.ceil(math.ceil(totalExpectedFollowAmount) / math.ceil(numberOfIterations)))

        bot.logger.info(
            "DISPATCHER: STARTED ITERATION no %s. Going to perform in this ITERATION: %s likes , %s follow/unfollow. Total to perform %s likes, %s follow/unfollow. Already performed %s likes, %s follow/unfollow" % (
                currentIteration, currentIterationLikeAmount, currentIterationFollowAmount,
                totalExpectedLikesAmount, totalExpectedFollowAmount, totalPerformedLikes, totalPerformedFollows))


        # standard operation
        standardResult = bot.startStandardOperation(likesAmount=currentIterationLikeAmount,
                                                    followAmount=currentIterationFollowAmount,
                                                    operations=bot.getBotOperations(args.angie_campaign))


        totalPerformedLikes = totalPerformedLikes + standardResult['no_likes']
        totalPerformedFollows = totalPerformedFollows + standardResult['no_follows']

        bot.logger.info(
            "DISPATCHER: Iteration %s end. Summary: Likes performed %s Likes expected %s . Follows/Unfollow performed %s , Expected follow/unfollow %s .  "
            % (currentIteration, standardResult['no_likes'], currentIterationLikeAmount,
               standardResult['no_follows'], currentIterationFollowAmount))

        bot.logger.info("DISPATCHER: Total likes to perform: %s, total performed likes: %s,  likes remained: %s" % (
        totalExpectedLikesAmount, totalPerformedLikes, totalExpectedLikesAmount - totalPerformedLikes))
        bot.logger.info(
            "DISPATCHER: Total follow to perform: %s, total performed follow/unfollow: %s,  follow remained: %s" % (
            totalExpectedFollowAmount, totalPerformedFollows, totalExpectedFollowAmount - totalPerformedFollows))

        currentIteration = currentIteration + 1

    bot.logger.info(
        "DISPATCHER: END. Summary: Last iteration %s, Likes performed %s Likes expected %s . Follows/Unfollow performed %s , Expected follow/unfollow %s ." % (
        currentIteration - 1, totalPerformedLikes, totalExpectedLikesAmount, totalPerformedFollows,
        totalExpectedFollowAmount))

    bot.crawl_user_followers(amount=500)
except SystemExit:
    bot.logger.info("dispatcher_v2: SystemExit: The bot was successfully stopped")
except:
    exceptionDetail = traceback.format_exc()
    #print(exceptionDetail)
    bot.logger.info("FATAL ERROR !")
    bot.logger.info(exceptionDetail)
