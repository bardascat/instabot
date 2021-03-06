# TODO: maybe the work can be implemented using a single process / multithreading ?
import time
from random import randint, shuffle
import datetime
from instabot.api import api_db


class BotFeedCrawler:
    def __init__(self,
                 instabot,
                 campaign):
        self.instabot = instabot
        self.campaign = campaign
        self.logger = instabot.logger

    def scanUsers(self):
        self.logger.info("scanUsers: Started with bot: %s !", self.campaign['username'])
        iteration = 0

        while True:
            users = self.getUsersToScan()

            self.logger.info("scanUsers: Going to scan %s users", len(users))

            for user in users:
                self.scanUser(user)

                pause = randint(2, 3)
                self.logger.info("scanUsers: Pause for %s seconds until processing next user...", pause)
                time.sleep(pause)

            pause = randint(2, 3)
            self.logger.info("scanUsers: Iteration %s ended, going to sleep for %s minutes" % (iteration, pause))
            iteration = iteration + 1
            time.sleep(pause * 60)

        self.logger.info("startScanUserFeed: Done scanning users feed, going to exit !")

    def scanUser(self, user):

        self.logger.info("scanUser---------------------Going to scan user's %s feed--------------------------",
                         user['email'])

        if user['instagram_username'] is None:
            self.logger.warning(
                "scanUser: Error: Instagram username is %s for user %s. Going to skip this user" % (
                    user['instagram_username'], user['email']))
            return False

        instagramUserId = self.instabot.get_userid_from_username(user['instagram_username'])

        if self.instabot.LastResponse.status_code is 404:
            self.logger.info("Instagram returned %s for user %s" %  (user['instagram_username'],self.instabot.LastResponse.status_code))
            return False

        if self.instabot.LastResponse.status_code is not 200 and self.instabot.LastResponse.status_code is not 404:
            self.logger.info("Previous http rest failed, going to kill the process.")
            exit("There was an error with this bot. Going to kill the process")

        self.logger.info(
            "scanUser:  %s has instagram id %s" % (user['instagram_username'], instagramUserId))

        if instagramUserId is None:
            self.logger.warning(
                "scanUser:  ERROR: Userid is none, probably the instagram username is invalid. Going to skip this user: %s...",
                user['email'])
            return False

        self.logger.info("scanUser: Getting last post inserted in database for user %s", user['email'])
        lastPost = api_db.fetchOne("select * from user_post where id_user=%s order by timestamp DESC limit 1",
                                   user['id_user'])

        self.logger.info("scanUser: Last post is %s", lastPost)

        if lastPost is None:
            recentThan = user['start_date']
            self.logger.info("scanUser: Last post is none, going to set recentThan date to user subscription  %s",recentThan)
        else:
            recentThan = lastPost['instagram_published_date']
            self.logger.info("scanUser: Last post is NOT NONE, going to set recentThan date to %s",recentThan)

        medias = self.instabot.get_recent_user_medias(instagramUserId, recentThan)
        self.logger.info("scanUser:  Found %s medias for user %s, going to save them in database." % (len(medias), user['email']))

        if len(medias) > 0:
            for media in medias:
                taken_at = datetime.datetime.fromtimestamp(int(media['taken_at']))
                api_db.insert(
                    "insert into user_post (id_campaign,id_user,instagram_post_id,code, crawler, instagram_published_date, timestamp) values (%s, %s, %s, %s, %s, %s, now())",
                    user['id_campaign'], user['id_user'], media['pk'], str(media['code']), self.campaign['id_user'],
                    taken_at)
            self.logger.info("scanUser: All posts were inserted in database.")

        self.logger.info("scanUser---------------------DONE scanning user's %s feed--------------------------",
                         user['email'])

    def getUsersToScan(self):

        noCrawlers = self.getNumberOfCrawlerBots()
        totalUsers = self.getTotalEligibleUsers()
        crawlerIndex = self.getCrawlerIndex()
        usersPersCrawler = totalUsers // noCrawlers
        offset = crawlerIndex * usersPersCrawler
        count = usersPersCrawler

        if crawlerIndex == noCrawlers - 1:
            count = totalUsers - offset

        self.logger.info("getUsersToScan: Crawler Index:%s, Total Users:%s, offset:%s, count:%s" % (
        crawlerIndex, totalUsers, offset, count))

        query = "select * from users join campaign on (users.id_user=campaign.id_user) join user_subscription on (users.id_user = user_subscription.id_user) where (user_subscription.end_date>now() or user_subscription.end_date is null) and campaign.active=1 order by users.id_user asc limit %s,%s"

        users = api_db.select(query, offset, count)

        shuffle(users)

        self.logger.info("getUsersToScan: Found %s users", len(users))

        return users

    def getNumberOfCrawlerBots(self):
        query = "select count(*) as no_crawlers from campaign where bot_type like 'feed_crawler'"
        result = api_db.fetchOne(query)

        self.logger.info("getNumberOfCrawlerBots: Found %s crawlers", result['no_crawlers'])
        return result['no_crawlers']

    # returns users that eligible for scanning. Basically users with an active subscription and campaign is active
    def getTotalEligibleUsers(self):

        query = "select count(*) as total_users from users join campaign on (users.id_user=campaign.id_user) join user_subscription on (users.id_user = user_subscription.id_user) where (user_subscription.end_date>now() or user_subscription.end_date is null) and campaign.active=1";
        result = api_db.fetchOne(query)

        self.logger.info("getTotalEligibleUsers: Found a total of %s users that need to be split.",
                         result['total_users'])
        return result['total_users']

    def getCrawlerIndex(self):
        sql = "SELECT username FROM `campaign` WHERE bot_type='feed_crawler' order by id_campaign asc"
        bots = api_db.select(sql)

        index = 0
        for bot in bots:
            if bot['username'] == self.campaign['username']:
                self.logger.info("getBotIndex: Bot %s has index: %s" %  ( bot['username'], index))
                return index
            index = index + 1

        raise Exception("getBotIndex: User %s is not a crawler bot", self.campaign['username'])
