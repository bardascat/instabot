"""
    All methods must return media_ids that can be
    passed into e.g. like() or comment() functions.
"""

import random
from tqdm import tqdm
from ..api import api_db
from . import delay
from random import randint
import time
import datetime


def get_media_owner(self, media_id):
    self.mediaInfo(media_id)
    try:
        return str(self.LastJson["items"][0]["user"]["pk"])
    except:
        return False


def get_popular_medias(self):
    self.getPopularFeed()
    return [str(media['pk']) for media in self.LastJson['items']]


def get_your_medias(self, as_dict=False):
    self.getSelfUserFeed()
    if as_dict:
        return self.LastJson["items"]
    return self.filter_medias(self.LastJson["items"], False)


def get_archived_medias(self, as_dict=False):
    self.getArchiveFeed()
    if as_dict:
        return self.LastJson["items"]
    return self.filter_medias(self.LastJson["items"], False)


def get_timeline_medias(self, filtration=True, amount=50):
    medias = self.getTimelineFeed(amount)
    if not medias:
        self.logger.warning("Error while getting timeline feed.")
        return []
    return self.filter_medias(medias, filtration)


def get_user_medias(self, user_id, filtration=True, is_comment=False):
    self.getUserFeed(user_id)
    
    if 'status' in self.LastJson:
      if self.LastJson["status"] == 'fail':
          self.logger.warning("This is a closed account. lastJson: %s", self.LastJson)
          return []
    if 'items'not in self.LastJson:
        self.logger.info("get_user_medias: the response did not contain any items. LastJson: %s", self.LastJson)
        return []
    
    if filtration==False:
        return self.LastJson["items"]
    else:
        return self.filter_medias(self.LastJson["items"], filtration, is_comment=is_comment)

def get_recent_user_medias(self, instagram_user_id, recentThan):
    self.logger.info("get_recent_user_medias: Started for user_id %s", instagram_user_id)
    medias = self.get_user_medias(user_id=instagram_user_id, filtration=False)
    
    if len(medias)==0:
        self.logger.info("get_recent_user_medias: 0 medias received for user with instagra id: %s. Going to return", instagram_user_id)
        return 0
        
    self.logger.info("get_recent_user_medias: Going to validate %d posts recent than %s" % (len(medias), recentThan))
    validatedMedias=[]
    
    for media in medias:
        taken_at = datetime.datetime.fromtimestamp(int(media['taken_at']))
    
        #self.logger.info("get_recent_user_medias: Going to validate post id %s, taken at %s" % (media['pk'], taken_at))
        if taken_at>recentThan:
            self.logger.info("get_recent_user_medias: Post %s is VALID: taken_at: %s, recentThan %s" % (media['pk'], taken_at, recentThan))
            validatedMedias.append(media)
        else:
            self.logger.info("get_recent_user_medias: Post %s is INVALID: taken_at: %s, recentThan %s" % (media['pk'], taken_at, recentThan))
            
    self.logger.info("get_recent_user_medias: Found %s validated medias. Going to return", len(validatedMedias))
    
    return validatedMedias


def get_total_user_medias(self, user_id):
    user_id = self.convert_to_user_id(user_id)
    medias = self.getTotalUserFeed(user_id)
    if self.LastJson["status"] == 'fail':
        self.logger.warning("This is a closed account.")
        return []
    return self.filter_medias(medias, filtration=False)


def get_user_likers(self, user_id, media_count=10):
    your_likers = set()
    media_items = self.get_user_medias(user_id, filtration=False)
    if not media_items:
        self.logger.warning("Can't get %s medias." % user_id)
        return []
    for media_id in tqdm(media_items[:media_count],
                         desc="Getting %s media likers" % user_id):
        media_likers = self.get_media_likers(media_id)
        your_likers |= set(media_likers)
    return list(your_likers)


def get_hashtag_medias(self, hashtag, filtration=True, amount=50):
    medias = self.getHashtagFeed(hashtagString=hashtag, amount=amount)
    if not medias:
        self.logger.warning("get_hashtag_medias: Empty result for: %s." % hashtag)
        return []

    return self.filter_medias(medias, filtration)


def get_location_medias(self, id_location, filtration=True, amount=None):
    medias = self.getLocationFeed(id_location, amount)
    if not medias:
        self.logger.warning("get_location_medias: Empty result for %s" % id_location)
        return []

    return self.filter_medias(medias, filtration)


def get_geotag_medias(self, geotag, filtration=True):
    # TODO: returns list of medias from geotag
    pass


def get_locations_from_coordinates(self, latitude, longitude):
    self.searchLocation(lat=latitude, lng=longitude)
    return [location for location in self.LastJson["items"] if int(location["location"]["lat"]) == int(latitude) and
            int(location["location"]["lng"]) == int(longitude)]


def get_media_info(self, media_id):
    if isinstance(media_id, dict):
        return media_id
    self.mediaInfo(media_id)
    if "items" not in self.LastJson:
        self.logger.info("Media with %s not found." % media_id)
        return []
    return self.LastJson["items"]


def get_timeline_users(self):
    # TODO: returns list userids who just posted on your timeline feed
    if not self.getTimelineFeed():
        self.logger.warning("Error while getting timeline feed.")
        return []
    return [str(i['user']['pk']) for i in self.LastJson['items'] if i.get('user')]


def get_hashtag_users(self, hashtag):
    users = []
    feed = self.getHashtagFeed(hashtag)
    for i in feed:
        users.append(str(i['user']))
    return users


def get_geotag_users(self, geotag):
    # TODO: returns list userids who just posted on this geotag
    pass


def get_userid_from_username(self, username):
    self.searchUsername(username)
    if "user" in self.LastJson:
        return str(self.LastJson["user"]["pk"])
    return None  # Not found


def get_username_from_userid(self, userid):
    self.getUsernameInfo(userid)
    if "user" in self.LastJson:
        return str(self.LastJson["user"]["username"])
    return None  # Not found


def get_user_info(self, user_id):
    user_id = self.convert_to_user_id(user_id)
    self.getUsernameInfo(user_id)
    if 'user' not in self.LastJson:
        return False
    return self.LastJson['user']


def crawl_other_user_followers(self, userObject, amount=100):
   
    if userObject['next_max_id']=='-1':
      self.logger.info("crawl_other_user_followers:Next max id is -1, meaning that we have the entire list of followers for user: %s . SKIPPING" , userObject['username'])
      return False
    
    user_id = self.get_userid_from_username(username=userObject['username'])
    
    self.logger.info('crawl_other_user_followers: Getting some followers from instagram')
    
    instagramFollowersResult = self.getUserFollowers(user_id, amount=amount, next_max_id = userObject['next_max_id'])

    #insert follower in db
    for follower in instagramFollowersResult['followers']:
      
      if follower['is_private']==False:
        api_db.insertUserFollower(userObject['id'], follower['pk'], follower['full_name'],follower['username'],follower['profile_pic_url'], follower['is_verified'])
  
    #update the next id
    if instagramFollowersResult['next_max_id']==None:
      next_id=-1
      self.logger.info("Next max id is null, meaning that we have the entire list of followers for user: %s" , userObject['username'])
    else:
      next_id=instagramFollowersResult['next_max_id']
        
    self.logger.info('crawl_other_user_followers: Going to update the next_max_id with: %s ',next_id)
    api_db.insert("update instagram_users set next_max_id=%s where id=%s",next_id,userObject['id'])
      
   

#this function is used to crawl followers of the logged user.
def crawl_user_followers(self, amount):
    self.logger.info("crawl_user_followers:Going to extract followers from instagram !")
    sleep_time = randint(1, 4)
    self.logger.info("crawl_user_followers:Sleeping %s seconds" % sleep_time)
    time.sleep(sleep_time)
      
    webApplicationUser = api_db.getWebApplicationUser(self.web_application_id_user)

    if not webApplicationUser['followers_next_max_id']:
        next_max_id = None
    else:
        next_max_id = webApplicationUser['followers_next_max_id']
    
    result = self.getUserFollowers(usernameId=self.user_id, amount=amount, next_max_id=next_max_id)

    if len(result['followers']) == 0:
        self.logger.info("crawl_user_followers:No followers received for user: %s ! SKIPPING" % self.user_id)
        return False

    for follower in result['followers']:
        api_db.insertOwnFollower(webApplicationUser['id_user'], follower['pk'], follower['full_name'],
                              follower['username'],
                              follower['profile_pic_url'], follower['is_verified'])

    next_id = result['next_max_id']
    if next_id == None:
        next_id = result['previous_next_max_id']

    self.logger.info("crawl_user_followers:Going to update the followers_next_max_id: %s of user: %s" % (next_id, self.web_application_id_user))
    api_db.insert("update users set followers_next_max_id=%s where id_user=%s",next_id, self.web_application_id_user)

    self.logger.info("crawl_user_followers:DONE updating followers list !")


def get_user_following(self, user_id, nfollows=None):
    user_id = self.convert_to_user_id(user_id)
    following = self.getTotalFollowings(user_id, nfollows)
    return [str(item['pk']) for item in following][::-1] if following else []


def get_media_likers(self, media_id):
    self.getMediaLikers(media_id)
    if "users" not in self.LastJson:
        self.logger.info("Media with %s not found." % media_id)
        return []
    return list(map(lambda user: str(user['pk']), self.LastJson["users"]))


def get_media_comments(self, media_id, only_text=False):
    self.getMediaComments(media_id)
    if 'comments' not in self.LastJson:
        return []
    if only_text:
        return [str(item["text"]) for item in self.LastJson['comments']]
    return self.LastJson['comments']


def get_media_commenters(self, media_id):
    self.getMediaComments(media_id)
    if 'comments' not in self.LastJson:
        return []
    return [str(item["user"]["pk"]) for item in self.LastJson['comments']]


def get_comment(self):
    if len(self.comments):
        return random.choice(self.comments).strip()
    return "wow"


def convert_to_user_id(self, smth):
    smth = str(smth)
    if not smth.isdigit():
        if smth[0] == "@":  # cut first @
            smth = smth[1:]
        smth = self.get_userid_from_username(smth)
        delay.very_small_delay(self)
    # if type is not str than it is int so user_id passed
    return smth
