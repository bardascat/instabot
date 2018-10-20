# TODO: maybe the work can be implemented using a single process / multithreading ?
import datetime

from pymongo import MongoClient


class BotProcessFollowers:
    def __init__(self, logger):
        self.logger = logger

    def process(self):

        self.logger.info("process: Started processing followers")

        client = self.getDatabaseConnection()
        db = client.angie_app
        items = db.user_followers.find({"processed": 0, "owner_instagram_username":"noemimeilman"}, {"followers": 0})

        self.logger.info("process: Found %s documents to process", items.count())

        for leftDocument in items:
            unfollowers = []
            newFollowers = []

            self.logger.info("process: Going to process left document: %s", leftDocument)

            rightDocument = db.user_followers.find_one(
                {"owner_instagram_username": leftDocument['owner_instagram_username'],
                 "crawled_at": {'$gt': leftDocument['crawled_at']}}, {"followers": 0},
                sort=[("crawled_at", 1)])
            if rightDocument is None:
                self.logger.info("process: error: could not find the matching right document for above left doc.")
                continue

            # going to compare them
            leftDocumentFollowers = db.user_followers.find_one({"_id": leftDocument['_id']}, {"crawled_at":0})
            rightDocumentFollowers = db.user_followers.find_one({"_id": rightDocument['_id']}, {"crawled_at":0})

            self.logger.info(
                "process: left document has %s followers, right documents has %s followers. Going to compare them." % (
                    len(leftDocumentFollowers['followers']), len(rightDocumentFollowers['followers'])))

            self.logger.info("process: Start Comparing lists for unfollowers")
            for leftItem in leftDocumentFollowers['followers']:
                followerFound = False
                for rightItem in rightDocumentFollowers['followers']:
                    if leftItem['username'] == rightItem['username']:
                        followerFound = True

                if followerFound == False:
                    self.logger.info("Follower %s was not found in right list", leftItem['username'])
                    unfollowers.append(leftItem)
            self.logger.info("process: done comparing lists for unfollowers")

            self.logger.info("process: Start Comparing lists for new followers")
            for rightItem in rightDocumentFollowers['followers']:
                followerFound = False
                for leftItem in leftDocumentFollowers['followers']:
                    if leftItem['username'] == rightItem['username']:
                        followerFound = True
                        break

                if followerFound == False:
                    self.logger.info("Follower %s was not found in left list -> new Follower", rightItem['username'])
                    newFollowers.append(rightItem)

            self.logger.info("process: Done comparing lists for new followers")

            self.logger.info("process: going to insert restults into database")
            db.processed_user_followers.insert({
                "processed_at":datetime.datetime.now(),
                "start_date":leftDocument['crawled_at'],
                "end_date":rightDocument['crawled_at'],
                "new_followers":newFollowers,
                "unfollowers":unfollowers
            })

            db.user_followers.update({"_id":leftDocument["_id"]},{"$set":{"processed":1}})

            self.logger.info("process: Done processing this document. Found %s unfollowers, %s new followers Going to process next user..." % (len(unfollowers), len(newFollowers)))


        client.close()
        self.logger.info("process: done... ")

    def getDatabaseConnection(self):
        client = MongoClient(host='localhost', port=27017)
        return client

    def insertFollowers(self, followersObject):
        self.logger.info("insertFollowers: inserting %s followers in db..." % len(followersObject['followers']))
        client = self.getDatabaseConnection()
        db = client.angie_app
        db.user_followers.insert(followersObject)
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
        db.user_followers.remove(
            {"owner_instagram_username": owner_instagram_username, "crawled_at": {"$gte": gte, "$lte": lte}})
        client.close()
        self.logger.info("removeFollowers:done removing")
