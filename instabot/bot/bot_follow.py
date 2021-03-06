from tqdm import tqdm

from . import limits
from . import delay
from ..api import api_db
from random import randint
import time


def follow(self, user):
    self.logger.info('Going to Follow user: %s ' % user['username'])

    delay.follow_delay(self)
    if super(self.__class__, self).follow(user['instagram_id_user']):
        self.logger.info("Successfully followed user %s " % user['username'])
        self.total_followed += 1
        return True

    return False


# todo add check user
def follow_users_by_location(self, locationObject, amount):
    self.logger.info("Going to follow %s users from location %s." % (amount, locationObject['location']))

    # get some extra posts to make sure we have enough to follow
    medias = self.getLocationFeed(locationObject['id_location'], amount * 2)

    users = []

    for media in medias:
        user = media['user']
        user['media'] = {}
        user['instagram_id_user'] = user['pk']
        user['media']['code'] = media['code']
        user['media']['image'] = media['image_versions2']['candidates'][0]['url']
        user['media']['id'] = media['pk']
        users.append(user)

    bot_operation = 'follow_users_by_location'
    return self.follow_users(users, amount, bot_operation, locationObject['location'])


# todo add check user
def follow_users_by_hashtag(self, hashtag, amount):
    feed = self.getHashtagFeed(hashtag, amount * 2)
    users = []

    for media in feed:
        user = media['user']
        user['media'] = {}
        user['instagram_id_user'] = user['pk']
        user['media']['code'] = media['code']
        user['media']['image'] = media['image_versions2']['candidates'][0]['url']
        user['media']['id'] = media['pk']
        users.append(user)
    bot_operation = 'follow_users_by_hashtag'

    return self.follow_users(users, amount, bot_operation, hashtag)


def follow_other_users_followers(self, userObject, amount):
    self.logger.info('Going to follow %s followers of user: %s' % (amount, userObject['username']))

    self.crawl_other_user_followers(userObject=userObject, amount=500)

    totalFollowersResult = api_db.fetchOne(
        "select count(*) as total_followers from instagram_user_followers  where fk=%s order by id asc",
        userObject['id'])

    self.logger.info('Total followers in  database: %s', totalFollowersResult['total_followers'])

    batchSize = amount * 3

    self.logger.info('Getting followers from DATABASE limit %s' % (batchSize))
    query = "select iuf.*, id_campaign from instagram_user_followers iuf " \
            "join instagram_users on (iuf.fk=instagram_users.id) " \
            "join campaign_config on (instagram_users.id_config=campaign_config.id_config) " \
            "where instagram_users.username=%s " \
            "and iuf.username not in  " \
            "(select username from bot_action where id_campaign=campaign_config.id_campaign and bot_operation like %s) limit %s"

    followers = api_db.select(query, userObject['username'], 'follow' + '%', batchSize)

    self.logger.info('Received from database %s followers', len(followers))

    iteration = 0
    securityBreak = 0
    filteredFollowers = []

    # check if this follower is valid -> this might not be required / usefull as it takes alot of time to perform the check
    self.logger.info("Going to check users")

    while len(filteredFollowers) < amount and securityBreak < 400 and len(followers) > iteration + 1:
        iteration = iteration + 1
        securityBreak = securityBreak + 1

        follower = followers[iteration]

        if self.check_user(follower) == True:
            follower['friendship_status'] = {}
            follower['profile_pic_url'] = None
            follower['friendship_status']['following'] = False
            follower['media'] = {}
            follower['media']['code'] = None
            follower['media']['image'] = None
            follower['media']['id'] = None
            filteredFollowers.append(follower)
        else:
            # delete the user from database
            self.logger.info('User is not valid, going to delete it from database')
            api_db.insert("delete from instagram_user_followers where id=%s", follower['id'])

        sleep_time = randint(1, 3)
        self.logger.info("Sleeping %s seconds" % sleep_time)
        time.sleep(sleep_time)
        self.logger.info("Current followers %s, iteration %s" % (len(filteredFollowers), securityBreak))

    self.logger.info("Total received %s FILTERED followers" % len(filteredFollowers))

    bot_operation = 'follow_other_users_followers'
    return self.follow_users(filteredFollowers, amount, bot_operation, userObject['username'])

#todo remove already followed users and other filters should be done before this function.
def follow_users(self, users, amount, bot_operation, bot_operation_value):
    broken_items = []

    self.logger.info("Going to follow %s users" % amount)

    users = removeAlreadyFollowedUsers(users,self)

    self.logger.info("After removing already followed users, %s users left to follow." % len(users))

    totalFollowed = 0
    iteration = 0

    while totalFollowed < amount and iteration < len(users):
        user = users[iteration]

        if self.follow(user):

            api_db.insertBotAction(self.id_campaign, self.web_application_id_user, user['instagram_id_user'],
                                   user['full_name'],
                                   user['username'],
                                   user['profile_pic_url'], user['media']['id'], user['media']['image'],
                                   user['media']['code'], bot_operation, bot_operation_value, self.id_log)
            totalFollowed = totalFollowed + 1
        else:
            broken_items.append(user)
        iteration = iteration + 1

    self.logger.info("DONE: Total followed %d users." % totalFollowed)
    self.logger.warning("Could not follow %d users." % len(broken_items))

    return totalFollowed


def removeAlreadyFollowedUsers(users, bot):
    filteredList = []
    for u in users:
        
      result = api_db.fetchOne("select count(*) as total from bot_action where id_campaign=%s and instagram_id_user=%s and bot_operation like %s",bot.id_campaign,u['instagram_id_user'],"follow_%")
      
      if result['total']>0:
        bot.logger.warning("removeAlreadyFollowedUsers: The user %s has been already followed in the past! SKIP IT !", u['username'])
      else:
        #bot.logger.info("removeAlreadyFollowedUsers: OK. The user %s was not followed before !", u['username'])
        
        if 'friendship_status' in u:
          if not u['friendship_status']['following']:
              filteredList.append(u)
    
    return filteredList


def follow_followers(self, user_id, nfollows=None):
    self.logger.info("Follow followers of: %s" % user_id)
    if not limits.check_if_bot_can_follow(self):
        self.logger.info("Out of follows for today.")
        return
    if not user_id:
        self.logger.info("User not found.")
        return
    follower_ids = self.get_user_followers(user_id, nfollows)
    if not follower_ids:
        self.logger.info("%s not found / closed / has no followers." % user_id)
    else:
        self.follow_users(follower_ids[:nfollows])


def follow_following(self, user_id, nfollows=None):
    self.logger.info("Follow following of: %s" % user_id)
    if not limits.check_if_bot_can_follow(self):
        self.logger.info("Out of follows for today.")
        return
    if not user_id:
        self.logger.info("User not found.")
        return
    following_ids = self.get_user_following(user_id)
    if not following_ids:
        self.logger.info("%s not found / closed / has no following." % user_id)
    else:
        self.follow_users(following_ids[:nfollows])


def getCurrentUserFollowing(self):
    result = api_db.select("select d.*  "
                           "from default_followings d "
                           "where d.id_user=%s", self.web_application_id_user)

    if len(result) < 1:
        self.logger.info("Getting current user following from database: empty set")
        return []
    else:
        resultArray = []
        self.logger.info("Getting current user following from database. Found %s records" % len(result))
        for item in result:
            resultArray.append(item['following_id'])
        return resultArray
