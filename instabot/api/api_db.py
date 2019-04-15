import MySQLdb
import sys
import json
from pymongo import MongoClient


def getMongoConnection():
    client = MongoClient(host='localhost', port=27017)
    return client

def excludeAlreadyCrawledLinks(links, queue, id_campaign, logger):

    filteredLinks = []

    for post in links:
        if any(x for x in queue if x['user']['username'] == post['user']['username']) is False:
            filteredLinks.append(post)


    client = getMongoConnection()
    db = client.angie_app

    for item in links:
        postExists = db.user_actions_queue.find_one({"instagram_username":item['user']['username'], "processed":0, 'id_campaign':id_campaign})

        if postExists is None:
            filteredLinks.append(item)

    client.close()

    #logger.info("excludeAlreadyCrawledLinks: Received %s links, filtered: %s" % (len(links), len(filteredLinks)))

    return filteredLinks

def excludeAlreadyProcessedLinks(links, id_campaign, removeLikedPosts, removeFollowedUsers, logger):
    client = getMongoConnection()
    db = client.angie_app

    filteredLinks = []

    for item in links:
        if removeLikedPosts is True:
            postLiked = db.bot_action.find_one({"post_link": "https://www.instagram.com/p/"+item["code"]+"/", "id_campaign": int(id_campaign),"bot_operation": {"$regex": "^like_engagement_"}})
            if postLiked is not None:
                #logger.info("excludeAlreadyProcessedLinks: Post %s was already liked, going to skip it" % (item["code"]))
                continue

        if removeFollowedUsers is True:
            #logger.info("excludeAlreadyProcessedLinks: checking username: %s, id_campaign: %s, " % (item['user']['username'], id_campaign))

            userFollowed = db.bot_action.find_one({"username": item["user"]["username"], "id_campaign": int(id_campaign), "bot_operation": {"$regex": "^follow_engagement_"}})
            if userFollowed is not None:
                #logger.info("excludeAlreadyProcessedLinks: User %s was already followed, going to skip it" % (item["user"]["username"]))
                continue

        filteredLinks.append(item)

    client.close()

    #logger.info("excludeAlreadyProcessedLinks: Total links received: %s, filtered links: %s" % (len(links), len(filteredLinks)))
    return filteredLinks


def getMysqlConnection():
    db = MySQLdb.connect(host="52.36.217.85",  # your host, usually localhost
                         user="angie_app",  # your username
                         passwd="angiePasswordDB",  # your password
                         db="angie_app")
    db.set_character_set('utf8mb4')
    dbc = db.cursor()
    dbc.execute('SET NAMES utf8mb4;')
    dbc.execute('SET CHARACTER SET utf8mb4;')
    dbc.execute('SET character_set_connection=utf8mb4;')

    return db


def getCampaign(campaignId):
    if campaignId != False:
        row = fetchOne(
            "select username,id_user,id_campaign,timestamp,id_account_type from campaign where id_campaign=%s",
            campaignId)
        return row
    else:
        return None


def getWebApplicationUser(id_user):
    if id_user != False:
        row = fetchOne("select * from users where id_user=%s", id_user)
        return row
    else:
        return False


def fetchOne(query, *args):
    db = getMysqlConnection()
    cur = db.cursor(MySQLdb.cursors.DictCursor)
    cur.execute(query, args)
    db.close()
    return cur.fetchone()


def select(query, *args):
    db = getMysqlConnection()
    cur = db.cursor(MySQLdb.cursors.DictCursor)
    cur.execute(query, args)
    rows = cur.fetchall()
    db.close()
    return list(rows)


def insert(query, *args):
    db = getMysqlConnection()
    cur = db.cursor()
    cur.execute(query, args)
    db.commit()
    id = cur.lastrowid
    db.close()
    return id


def updateCampaignChekpoint(key, value, id_campaign):
    query = 'INSERT INTO campaign_checkpoint (id_campaign, _key, value, timestamp) VALUES(%s, %s, %s, CURDATE()) ON DUPLICATE KEY UPDATE  value=%s'

    id = insert(query, id_campaign, key, value, value)

    return id


def insertBotAction(*args):
    query = "insert into bot_action (id_campaign, id_user, instagram_id_user, " \
            "full_name, username, user_image, post_id, post_image, " \
            "post_link,bot_operation,bot_operation_value,id_log,timestamp) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,now())"

    id = insert(query, *args)
    return id


def insertOwnFollower(*args):
    query = "insert into own_followers (id_user,instagram_id_user,full_name,username,user_image,is_verified,timestamp) " \
            " VALUES (%s,%s,%s,%s,%s,%s,now()) ON DUPLICATE KEY UPDATE instagram_id_user=instagram_id_user"

    id = insert(query, *args)
    return id


def insertUserFollower(*args):
    query = "insert into instagram_user_followers (fk,instagram_id_user,full_name,username,user_image,is_verified,timestamp) " \
            " VALUES (%s,%s,%s,%s,%s,%s,now()) ON DUPLICATE KEY UPDATE instagram_id_user=instagram_id_user"

    id = insert(query, *args)
    return id


def getBotIp(bot, id_user, id_campaign, is_bot_account):
    query = "select ip,type from  campaign left join ip_bot on campaign.id_ip_bot=ip_bot.id_ip_bot where id_campaign=%s"

    result = fetchOne(query, id_campaign)

    if result is None or result['ip'] is None:
        bot.logger.warning("getBotIp: Could not find an ip for user %s", id_user)
        raise Exception("getBotIp: Could not find an ip for user" + str(id_user))

    bot.logger.info("User %s, has ip: %s" % (id_user, result['ip']))
    return result
