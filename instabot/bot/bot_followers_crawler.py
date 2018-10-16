# TODO: maybe the work can be implemented using a single process / multithreading ?
import time
from random import randint, shuffle
from pymongo import MongoClient
from instabot.api import api_db
import datetime


class BotFollowersCrawler:
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

            pause = randint(13, 16)
            self.logger.info("scanUsers: Pause for %s minutes until processing next user...", pause)
            time.sleep(pause * 60)

        self.logger.info("startScanUserFeed: Done scanning users, going to exit !")

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

        #cleanup other unsuccessfull scans
        #self.removeFollowersFromToday(owner_instagram_username=user['instagram_username'])

        followers = self.crawlFollowers(usernameId=instagramUserId, instagram_username=user['instagram_username'])

        if followers is False:
            self.logger.info("scanUser: ERROR:  Could not retrieve the entire list of followers, going to skip this user.")
            #self.removeFollowersFromToday(user['instagram_username'])
            return False
        else:
            self.logger.info("scanUser: COMPLETED SCANNING FOR USER %s. Found %s followers." % (user['instagram_username'], len(followers)))
            self.logger.info("scanUser: Saving followers in database")
            self.insertFollowers({
                "owner_instagram_username" : user['instagram_username'],
                "owner_id": user['id_user'],
                "id_crawler": self.campaign['id_user'],
                "crawled_at": datetime.datetime.now(),
                "followers": followers
            })
            self.logger.info("scanUser: done saving")

            return True


    def getDatabaseConnection(self):
        client = MongoClient(host='localhost', port=27017)
        return client

    def insertFollowers(self, followers):
        self.logger.info("insertFollowers: inserting %s followers in db..." % len(followers))
        client = self.getDatabaseConnection()
        db = client.angie_app
        db.user_followers.insert(followers)
        client.close()
        self.logger.info("insertFollowers: done... ")

        return True

    def removeFollowersFromToday(self, owner_instagram_username):

        start = datetime.datetime.now()
        gte = start.replace(minute=0, hour=0, second=0, microsecond=0)

        end = datetime.datetime.now()
        lte = end.replace(minute=59, hour=23, second=59, microsecond=999)

        self.logger.info("removeFollowers: for user %s, between %s and %s" % (owner_instagram_username, gte, lte))
        client = self.getDatabaseConnection()
        db = client.angie_app
        db.user_followers.remove({"owner_instagram_username": owner_instagram_username, "created_at": {"$gte": gte, "$lte": lte}})
        client.close()
        self.logger.info("removeFollowers:done removing")

    def crawlFollowers(self, usernameId, instagram_username):
        self.logger.info("crawlFollowers: Getting followers for user: %s" % (instagram_username))
        followers=[]

        securityBreak = 0
        next_max_id = None

        while securityBreak < 200:

            if next_max_id == None:
                self.instabot.SendRequest('friendships/' + str(usernameId) + '/followers')
            else:
                self.instabot.SendRequest('friendships/' + str(usernameId) + '/followers/?max_id=' + str(next_max_id))

            temp = self.instabot.LastJson

            # the result is damaged
            if "users" not in temp:  # if no items
                self.logger.info("ERROR: INVALID RESPONSE: Total received: %s followers for user %s" % (len(followers), usernameId))
                return False

            for item in temp["users"]:
                item['crawled_at'] = datetime.datetime.now()
                followers.append(item)
            securityBreak = securityBreak + 1

            self.logger.info("Iteration %s ,received %s items, total received %s followers" % (securityBreak, len(temp['users']), len(followers)))

            if "next_max_id" not in temp:
                self.logger.info("crawlFollowers: End of the line: Total received %s followers for user %s. going to return." % (len(followers), usernameId))
                return followers
            next_max_id = temp["next_max_id"]

            sleep_time = randint(40,60)
            self.logger.info("Sleeping %s seconds" % sleep_time)
            time.sleep(sleep_time)

        self.logger.warning("crawlFollowers:  ERROR: did not retrieve the total followers. Stopped at iteration: %s. Followers scanned: %s" % (securityBreak, len(followers)))

        return None

    def getUsersToScan(self):
        eligibleUsers = self.getEligibleUsers()
        noCrawlers = self.getNumberOfCrawlerBots()
        totalUsers = len(eligibleUsers)
        crawlerIndex = self.getCrawlerIndex()
        usersPersCrawler = totalUsers // noCrawlers
        offset = crawlerIndex * usersPersCrawler
        count = usersPersCrawler + offset
        if crawlerIndex == noCrawlers - 1:
            count = totalUsers

        maxFollowersPerBot = 15
        if count > maxFollowersPerBot:
            raise Exception("Too many followers for bot %s. max value is set to: %s, actual: %s" % (self.campaign['username'], maxFollowersPerBot, count))

        self.logger.info("getUsersToScan: Crawler Index:%s, Total Eligible Users:%s, offset:%s, count:%s, usersPerCrawler: %s" % (crawlerIndex, totalUsers, offset, count, usersPersCrawler))

        users = eligibleUsers[offset:count]

        self.logger.info("getUsersToScan: Found %s users to scan for followers for this bot.", len(eligibleUsers))

        self.logger.info("getUsersToScan: going to process the following users: %s", users)
        return users

    # returns users that eligible for scanning. Basically users with an active subscription and campaign is active and were not crawled for the past 3 days
    def getEligibleUsers(self):
        filteredUsers = []
        usersWithActiveSubscription = "select email, instagram_username, users.id_user from users  join campaign on (users.id_user=campaign.id_user)  join user_subscription on (users.id_user = user_subscription.id_user)  where (user_subscription.end_date>now() or user_subscription.end_date is null) and campaign.active=1  order by users.id_user desc"
        users = api_db.select(usersWithActiveSubscription)

        client = self.getDatabaseConnection()
        db = client.angie_app

        #filter users that have  already been crawled today
        for user in users:

            start = datetime.datetime.now()
            gte = start.replace(minute=0, hour=0, second=0, microsecond=0)

            end = datetime.datetime.now()
            lte = end.replace(minute=59, hour=23, second=59, microsecond=999)

            wasCrawledToday = db.user_followers.find({"owner_id":user['id_user'],"created_at": {"$gte": gte, "$lte": lte}})
            if wasCrawledToday.count() == 0:
                filteredUsers.append(user)

        client.close()
        self.logger.info("getTotalEligibleUsers: Found a total of eligible %s users that need to be split.", len(filteredUsers))
        return filteredUsers

    def getCrawlerIndex(self):
        sql = "SELECT username FROM `campaign` WHERE bot_type='followers_crawler' order by id_campaign asc"
        bots = api_db.select(sql)

        index = 0
        for bot in bots:
            if bot['username'] == self.campaign['username']:
                self.logger.info("getBotIndex: Bot %s has index: %s" % (bot['username'], index))
                return index
            index = index + 1

        raise Exception("getBotIndex: User %s is not a crawler bot", self.campaign['username'])

    def getNumberOfCrawlerBots(self):
        query = "select count(*) as no_crawlers from campaign where bot_type like 'followers_crawler'"
        result = api_db.fetchOne(query)

        self.logger.info("getNumberOfCrawlerBots: Found %s crawlers of type followers_crawler", result['no_crawlers'])
        return result['no_crawlers']

