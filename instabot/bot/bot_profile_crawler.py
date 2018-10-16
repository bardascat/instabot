# TODO: maybe the work can be implemented using a single process / multithreading ?
import time
from random import randint, shuffle
from pymongo import MongoClient
from instabot.api import api_db
import datetime
import json

class BotProfileCrawler:
    def __init__(self,
                 instabot,
                 campaign):
        self.instabot = instabot
        self.campaign = campaign
        self.logger = instabot.logger


    def scanUsers(self):
        self.logger.info("scanUsers: Started with bot: %s !", self.campaign['username'])

        users = self.getUsersToScan()
        if len(users) == 0:
            self.logger.info("scanUsers: No users to scan for this crawler. Going to return !")
            return False

        self.logger.info("scanUsers: Found %s users to scan.", len(users))

        for user in users:
            self.logger.info("----------STARTED SCANNING USER %s ---------------", user['instagram_username'])

            self.scanUser(user)

            self.logger.info("----------DONE SCANNING USER %s ---------------", user['instagram_username'])

            pause = randint(10, 30)
            self.logger.info("scanUsers: Pause for %s seconds until processing next user...", pause)
            time.sleep(pause)

        self.logger.info("startScanUser: Done scanning users, going to exit !")

    def scanUser(self, user):

        if user['instagram_username'] is None:
            self.logger.warning("scanUser: Error: Instagram username is %s for user %s. Going to skip this user" % (
                user['instagram_username'], user['email']))
            return False

        instagramUserId = self.instabot.get_userid_from_username(user['instagram_username'])
        self.logger.info("scanUser:  %s has instagram id %s" % (user['instagram_username'], instagramUserId))

        if instagramUserId is None:
            self.logger.warning("scanUser:  ERROR: Userid is none, probably the instagram username is invalid. Going to skip this user: %s...",user['email'])
            return False

        status = self.instabot.getUsernameInfo(usernameId=instagramUserId)
        if status is True:
            api_db.insert("insert into instagram_user_followers (id_bot, id_user, followers_count, following_count,json) values (%s, %s, %s, %s, %s)", self.campaign['id_user'], user['id_user'], self.instabot.LastJson['user']['follower_count'],self.instabot.LastJson['user']['following_count'], json.dumps(self.instabot.LastJson))

    def getUsersToScan(self):
        eligibleUsers = self.getEligibleUsers()
        noCrawlers = self.getNumberOfCrawlerBots()
        totalUsers = len(eligibleUsers)
        crawlerIndex = self.getCrawlerIndex()
        usersPersCrawler = totalUsers // noCrawlers
        offset = crawlerIndex * usersPersCrawler
        count = usersPersCrawler + offset

        if crawlerIndex == noCrawlers - 1:
            count = totalUsers - offset

        self.logger.info("getUsersToScan: Crawler Index:%s, Total Eligible Users:%s, offset:%s, count:%s" % (crawlerIndex, totalUsers, offset, count))

        users = eligibleUsers[offset:count]

        self.logger.info("getUsersToScan: Found %s users to scan for followers for this bot.", len(eligibleUsers))

        self.logger.info("getUsersToScan: going to process the following users: %s", users)
        return users

    def getEligibleUsers(self):
        usersWithActiveSubscription = "select email, instagram_username, users.id_user from users  join campaign on (users.id_user=campaign.id_user)  join user_subscription on (users.id_user = user_subscription.id_user)  where (user_subscription.end_date>now() or user_subscription.end_date is null) and campaign.active=1  order by users.id_user desc"
        users = api_db.select(usersWithActiveSubscription)
        self.logger.info("getTotalEligibleUsers: Found a total of eligible %s users that need to be split.", len(users))
        return users

    def getCrawlerIndex(self):
        sql = "SELECT username FROM `campaign` WHERE bot_type='profile_crawler' order by id_campaign asc"
        bots = api_db.select(sql)

        index = 0
        for bot in bots:
            if bot['username'] == self.campaign['username']:
                self.logger.info("getBotIndex: Bot %s has index: %s" % (bot['username'], index))
                return index
            index = index + 1

        raise Exception("getBotIndex: User %s is not a crawler bot", self.campaign['username'])

    def getNumberOfCrawlerBots(self):
        query = "select count(*) as no_crawlers from campaign where bot_type like 'profile_crawler'"
        result = api_db.fetchOne(query)

        self.logger.info("getNumberOfCrawlerBots: Found %s crawlers of type profile_crawler", result['no_crawlers'])
        return result['no_crawlers']

