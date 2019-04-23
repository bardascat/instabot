# TODO: maybe the work can be implemented using a single process / multithreading ?
import time
from random import randint, shuffle

from pymongo import MongoClient

from instabot.api import api_db
import datetime
import urllib2
import json
import traceback
import time

class BotActionsCrawler:
    def __init__(self,
                 instabot,
                 campaign):
        self.instabot = instabot
        self.campaign = campaign
        self.logger = instabot.logger
        self.maxPostsPerUser = 1200

    def scanUsers(self):
        self.logger.info("scanUsers: Started with bot: %s !", self.campaign['username'])

        users = self.getUsersToScan()
        if len(users) == 0:
            self.logger.info("scanUsers: No users to scan for this crawler. Going to return !")
            return False

        self.logger.info("scanUsers: Found %s users to scan.", len(users))

        for user in users:
            start = time.time()
            self.logger.info("----------STARTED SCANNING ACTIONS USER %s/id_campaign: %s ---------------" % (user['instagram_username'], user['id_campaign']))

            result = self.scanUser(user)
            end = time.time()
            self.logger.info("----------DONE SCANNING ACTIONS FOR USER %s. EXECUTION TIME(m): %s  ---------------" % (user['instagram_username'], (end-start)//60))

            if result is not False:
                pause = randint(1, 3)
                self.logger.info("scanUsers: Pause for %s minutes until processing next user...", pause)
                time.sleep(pause * 60)

        self.logger.info("startScanUserFeed: Done scanning users, going to exit !")

    def scanUser(self, user):

        noOfPostsToScan = self.maxPostsPerUser - user['queued_items']

        self.logger.info("scanUser:[%s]: going to scan for %s posts, user already has in queue: %s posts, max limit: %s" % (user['instagram_username'],self.maxPostsPerUser - user['queued_items'], user['queued_items'], self.maxPostsPerUser))

        removeLikedPosts = True
        removeFollowedUsers = True

        tags = []
        hashtags = self.getHashtags(user['id_campaign'])
        locations = self.getLocations(user['id_campaign'])

        for tag in hashtags:
            tags.append({"tag": tag['hashtag'], "type": "hashtag"})

        for tag in locations:
            tags.append({"tag": tag['id_location'], "type": "location"})

        self.logger.info("scanUser: Received %s hashtags, %s locations" % (len(hashtags), len(locations)))
        # self.logger.info("scanUser: Tags: %s" % (tags))

        if len(tags) == 0:
            self.logger.info("Nothing to do with 0 tags, going to return")
            return False

        shuffle(tags)
        linksPerTag = noOfPostsToScan // len(tags)
        minimumLinksPerTag = 50

        if linksPerTag < minimumLinksPerTag:
            self.logger.info("LinksPerTag: %s links per tag, this is less than minimumLinksPerTag: %s, going to reset linksPerTag to: %s" % (
            linksPerTag, minimumLinksPerTag, minimumLinksPerTag))
            linksPerTag = minimumLinksPerTag

        self.logger.info("scanUser: Going to crawl %s links per tag", linksPerTag)

        # todo: make sure that we get tags from both categories
        shuffle(tags)

        linksSaved = 0
        for tag in tags:

            if tag['type'] == 'hashtag':
                feed = self.instabot.getHashtagFeed(hashtagString=tag['tag'], amount=linksPerTag,
                                                    id_campaign=user['id_campaign'],
                                                    removeLikedPosts=removeLikedPosts,
                                                    removeFollowedUsers=removeFollowedUsers)

            if tag['type'] == 'location':
                feed = self.instabot.getLocationFeed(locationId=tag['tag'], amount=linksPerTag,
                                                     id_campaign=user['id_campaign'],
                                                     removeLikedPosts=removeLikedPosts,
                                                     removeFollowedUsers=removeFollowedUsers)

            self.insertActions(feed, tag['type'], tag['tag'], user['id_campaign'])
            linksSaved += len(feed)

            if linksSaved >= noOfPostsToScan:
                self.logger.info("scanUser: Reached number of posts to scan: %s, going to exit", noOfPostsToScan)
                break

            # todo: recalculate linksPerTag after each operation

        return linksSaved

    def getHashtags(self, id_campaign):
        query = "select hashtag from instagram_hashtags join campaign_config using(id_config) where campaign_config.id_campaign=%s and instagram_hashtags.enabled=1 and campaign_config.enabled=1"
        result = api_db.select(query, id_campaign)
        return result

    def getLocations(self, id_campaign):
        query = "select id_location from instagram_locations join campaign_config using(id_config) where campaign_config.id_campaign=%s and instagram_locations.enabled=1 and campaign_config.enabled=1"
        result = api_db.select(query, id_campaign)
        return result

    def getDatabaseConnection(self):
        client = MongoClient(host='localhost', port=27017)
        return client

    def insertActions(self, feed, targetType, tag, id_campaign):
        if len(feed)==0:
            return False

        self.logger.info("insertActions: saving %s actions." % len(feed))
        client = self.getDatabaseConnection()
        db = client.angie_app

        for item in feed:
            object = {"targetType": targetType, "tag": tag, "link": "https://www.instagram.com/p/" + item["code"] + "/",
                      "code": item['code'], "instagram_username": item['user']['username'], "id_campaign": id_campaign,
                      "processed": 0, "id_crawler": self.campaign['id_user'], "timestamp": datetime.datetime.now()}
            db.user_actions_queue.insert(object)
        client.close()


        return True

    def getUsersToScan(self):
        eligibleUsers = self.getEligibleUsers()

        if len(eligibleUsers) == 0:
            return []

        noCrawlers = self.getNumberOfCrawlerBots()
        totalUsers = len(eligibleUsers)
        crawlerIndex = self.getCrawlerIndex()
        if totalUsers < noCrawlers:
            usersPersCrawler = totalUsers
        else:
            usersPersCrawler = totalUsers // noCrawlers
        offset = crawlerIndex * usersPersCrawler
        count = usersPersCrawler + offset
        if crawlerIndex == noCrawlers - 1:
            count = totalUsers

        # maxFollowersPerBot = 15
        # if (count-offset) > maxFollowersPerBot:
        #     raise Exception("Too many followers for bot %s. max value is set to: %s, actual: %s" % (self.campaign['username'], maxFollowersPerBot, count))

        self.logger.info(
            "getUsersToScan: Crawler Index:%s, Total Eligible Users:%s, offset:%s, count:%s, usersPerCrawler: %s, going to scan %s users" % (
                crawlerIndex, totalUsers, offset, count, usersPersCrawler, count - offset))

        users = eligibleUsers[offset:count]

        # shuffle(users)
        filteredUsers = []
        users = self.orderUsersByActions(users)

        for u in users:
            if u['queued_items'] > self.maxPostsPerUser:
                self.logger.info(
                    "getUsersToScaun: Campaign: %s has %s available actions queued, maxLimit is: %s, going to skip it for now !" % (
                    u['id_campaign'], u['queued_items'], self.maxPostsPerUser))
            else:
                filteredUsers.append(u)

        self.logger.info("getUsersToScan: Found %s users to scan for actions for this bot.", len(filteredUsers))

        self.logger.info("getUsersToScan: going to process the following users: %s", filteredUsers)
        return filteredUsers

    def orderUsersByActions(self, users):
        self.logger.info("orderUsersByActions: ordering users by number of actions...")
        try:
            url = "https://rest.angie.one/crons/bot/userActionsQueueStatus"
            contents = urllib2.urlopen(url).read()
            result = json.loads(contents)['data']

            for u in users:
                for r in result:
                    if u['id_campaign'] == r['id_campaign']:
                        u['queued_items'] = r['queue']
                        continue
                if 'queued_items' not in u:
                    u['queued_items'] = 0

            users.sort(key=lambda x: x['queued_items'], reverse=False)
            return users
        except:
            exceptionDetail = traceback.format_exc()
            self.logger.error("orderUsersByActions: Error ordering users, going to return default order. %s",
                              exceptionDetail)
            return users

    # returns users that eligible for scanning. Basically users with an active subscription and campaign is active and were not crawled for the past 3 days
    def getEligibleUsers(self):
        filteredUsers = []
        usersWithActiveSubscription = "select email, instagram_username, campaign.id_campaign, users.id_user from users  join campaign on (users.id_user=campaign.id_user)  join user_subscription on (users.id_user = user_subscription.id_user)  where (user_subscription.end_date>now() or user_subscription.end_date is null) and campaign.active=1 order by users.id_user desc"
        users = api_db.select(usersWithActiveSubscription)

        # filter users that have  already been crawled today
        for user in users:
            filteredUsers.append(user)

        self.logger.info("getTotalEligibleUsers: Found a total of eligible %s users that need to be split.",
                         len(filteredUsers))
        return filteredUsers

    def getCrawlerIndex(self):
        sql = "SELECT username FROM `campaign` WHERE bot_type='links_crawler' order by id_campaign asc"
        bots = api_db.select(sql)

        index = 0
        for bot in bots:
            if bot['username'] == self.campaign['username']:
                self.logger.info("getBotIndex: Bot %s has index: %s" % (bot['username'], index))
                return index
            index = index + 1

        raise Exception("getBotIndex: User %s is not a crawler bot", self.campaign['username'])

    def getNumberOfCrawlerBots(self):
        query = "select count(*) as no_crawlers from campaign where bot_type like 'links_crawler'"
        result = api_db.fetchOne(query)

        self.logger.info("getNumberOfCrawlerBots: Found %s crawlers of type links_crawler", result['no_crawlers'])
        return result['no_crawlers']
