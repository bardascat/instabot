import requests
import json
import hashlib
import hmac
import urllib
import uuid
import sys
import logging
import time
from random import randint
from tqdm import tqdm
import os
import io
import traceback
from . import config
from .api_photo import configurePhoto
from .api_photo import uploadPhoto
from .api_photo import downloadPhoto

from .api_video import configureVideo
from .api_video import uploadVideo

from .api_search import fbUserSearch
from .api_search import searchUsers
from .api_search import searchUsername
from .api_search import searchTags
from .api_search import searchLocation

from .api_profile import removeProfilePicture
from .api_profile import setPrivateAccount
from .api_profile import setPublicAccount
from .api_profile import getProfileData
from .api_profile import editProfile
from .api_profile import setNameAndPhone

from .prepare import get_credentials
from .prepare import delete_credentials
from .api_db import insert, getBotIp, fetchOne, excludeAlreadyProcessedLinks
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.poolmanager import PoolManager
import socket

# The urllib library was split into other modules from Python 2 to Python 3
if sys.version_info.major == 3:
    import urllib.parse


class SourceAddressAdapter(HTTPAdapter):
    def __init__(self, source_address, **kwargs):
        self.source_address = source_address
        super(SourceAddressAdapter, self).__init__(**kwargs)

    def init_poolmanager(self, connections, maxsize, block=False):
        self.poolmanager = PoolManager(num_pools=connections,
                                       maxsize=maxsize,
                                       block=block,
                                       source_address=self.source_address)


class API(object):
    def __init__(self):
        self.isLoggedIn = False
        self.LastResponse = None
        self.total_requests = 0

    def initLogging(self, id_campaign,bot_type):
        if bot_type=="like_for_like":
            filename = time.strftime("%d.%m.%Y") + "_l4l.log"
        elif bot_type=="scan_user_feed":
            filename = time.strftime("%d.%m.%Y") + "_scan_feed.log"
        elif bot_type=="scan_user_followers":
            filename = time.strftime("%d.%m.%Y") + "_scan_user_followers.log"
        elif bot_type=="scan_user_profile":
            filename = time.strftime("%d.%m.%Y") + "_scan_user_profile.log"
        else:
            filename = time.strftime("%d.%m.%Y") + ".log"

        # this is not working atm
        # logs_folder = os.environ['INSTABOT_LOGS_PATH']
        logs_folder = "/home/instabot-log"
        campaign_folder = logs_folder + "/campaign/" + id_campaign

        log_path = campaign_folder + "/" + filename

        if not os.path.exists(campaign_folder):
            os.makedirs(campaign_folder)
        # handle logging
        self.logger = logging.getLogger('[instabot]')
        self.logger.setLevel(logging.DEBUG)
        logging.basicConfig(format='%(asctime)s %(message)s',
                            filename=log_path,
                            level=logging.INFO
                            )
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)

        if self.hide_output == False:
            self.logger.addHandler(ch)

    def setUser(self, username, password):
        self.username = username
        self.password = password
        self.uuid = self.generateUUID(True)

    def canUserLogin(self, id_campaign):
        blockLimit=12
        self.logger.info("canUserLogin: Checking if user with campaign: %s can loggin...", id_campaign)

        result = fetchOne("select count(*) as total_blocks from bot_log join campaign using(id_user) where date(bot_log.timestamp)=CURDATE() and id_campaign=%s and (details='spam' or details='sentry_block' or details='ip_block')", id_campaign)
        if result['total_blocks']>=blockLimit:
            self.logger.info("canUserLogin: Error: User cannot login because it was blocked more than %s times today. Actual block %s" % (blockLimit, result['total_blocks']))
            return False
        else:
            self.logger.info("canUserLogin: SUCCESS, User Can login ! Today it was blocked %s times. Max limit is %s blocks." % (result['total_blocks'], blockLimit))
            return True


    def login(self, username=None, password=None, force=False, proxy=None, storage=True, logoutFlag=True):
        self.logger.info("login: Trying to login user %s with force flag value: %s, storage value: %s, logoutFlag: %s" % (username, force, storage, logoutFlag))



        if self.canUserLogin(self.id_campaign)==False and force==False:
            raise Exception("login: User cannot login anymore today since it reached tha maximum blocks per day !")

        if force==True:
            self.logger.info("login. Going to login the user no matter what since force flag is true.")
        if (not self.isLoggedIn or force):
            self.session = requests.Session()
            if self.multiple_ip is not None and self.multiple_ip is not False:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.bot_ip = getBotIp(self, self.web_application_id_user, self.id_campaign, self.is_bot_account)
                if self.bot_ip['type'] == "proxy":
                    self.logger.info("login: We are going to use a proxy: %s", self.bot_ip['ip'])
                    proxies = {
                        'http': self.bot_ip['ip'],
                        'https': self.bot_ip['ip']
                    }
                    self.session.proxies.update(proxies)
                else:
                    self.logger.info("We are going to use a regular ip %s", self.bot_ip['ip'])
                    self.session.mount("http://", SourceAddressAdapter((str(self.bot_ip['ip']), 0)))
                    self.session.mount("https://", SourceAddressAdapter((str(self.bot_ip['ip']), 0)))
            self.logger.info("Going to test the proxy/ip")

            response=self.session.get('https://api.ipify.org?format=json')
            self.logger.info("Proxy test respone %s",response.text)


            if storage==False:
                self.logger.info("login: Storage login is disabled !")
                return self.newLogin(username,password,proxy)
            elif self.loginFromStorage(username, password)!=True:
                return self.newLogin(username,password,proxy)
            else:
                return True



    def loginFromStorage(self, username, password):
        self.logger.info("loginFromStorage: Trying to login from storage...")

        try:
            with open('/home/instabot-log/campaign/'+self.id_campaign+'/user-identity.json') as json_data:
                userIdentity = json.load(json_data)
                #self.logger.info("canLoginFromStorage: userIdentity:%s",userIdentity)

                self.session.cookies.set(name="csrftoken",value=userIdentity['csrftoken'],domain="i.instagram.com",path="/")
                self.session.cookies.set(name="ds_user",value=userIdentity['ds_user'],domain="i.instagram.com",path="/")
                self.session.cookies.set(name="ds_user_id",value=userIdentity['ds_user_id'],domain="i.instagram.com",path="/")
                self.session.cookies.set(name="mid",value=userIdentity['mid'],domain="i.instagram.com",path="/")
                self.session.cookies.set(name="rur",value=userIdentity['rur'],domain="i.instagram.com",path="/")
                self.session.cookies.set(name="sessionid",value=userIdentity['sessionid'],domain="i.instagram.com",path="/")
                self.session.cookies.set(name="social_hash_bucket_id",value=userIdentity['social_hash_bucket_id'],domain="i.instagram.com",path="/")
                self.session.cookies.set(name="urlgen",value=userIdentity['urlgen'],domain="i.instagram.com",path="/")
                self.device_id=userIdentity['device_id']
                self.uuid=userIdentity['uuid']
                self.user_id = userIdentity['user']['pk']
                self.rank_token = userIdentity['rank_token']
                self.token = userIdentity['token']
                self.isLoggedIn = True
                self.username = username
                self.password = password

                self.get_timeline_medias(amount=1)
                self.logger.info("loginFromStorage: ****************** SUCCESS - USER LOGGED IN FROM STORAGE ************************")
                return True
        except:
                exceptionDetail = traceback.format_exc()
                self.logger.info("loginFromStorage: ************ Cannot login from storage. Error: %s:",exceptionDetail)
                return False
        return False



    def newLogin(self, username,password, proxy):
        self.logger.info("newLogin: trying a new login...")

        m = hashlib.md5()
        m.update(username.encode('utf-8') + password.encode('utf-8'))
        self.proxy = proxy
        self.device_id = self.generateDeviceId(m.hexdigest())
        self.setUser(username, password)
        self.session.cookies.clear_session_cookies()

        #self.logger.info("cookies 1: %s", self.session.cookies.list_domains())
        if (self.SendRequest('si/fetch_headers/?challenge_type=signup&guid=' + self.generateUUID(False), None, True)):

            data = {'phone_id': self.generateUUID(True),
            '_csrftoken': self.LastResponse.cookies['csrftoken'],
            'username': self.username,
            'guid': self.uuid,
            'device_id': self.device_id,
            'password': self.password,
            'login_attempt_count': '0'}

            #self.logger.info("cookies 2: %s", self.session.cookies.list_domains())

            if self.SendRequest('accounts/login/', self.generateSignature(json.dumps(data)), True):
                #self.logger.info("cookies 3: %s", self.session.cookies.list_domains())
                userIdentity={}
                self.isLoggedIn = True

                self.user_id = self.LastJson["logged_in_user"]["pk"]
                self.rank_token = "%s_%s" % (self.user_id, self.uuid)
                self.token = self.LastResponse.cookies["csrftoken"]
                self.logger.info("newLogin: ****************** SUCCESS - USER PERFORMED A NEW LOGIN as %s ************************", self.username)


                #set instagram username
                #self.logger.info("login: Going to set the real instagram username:%s", self.LastJson["logged_in_user"]['username'])
                #insert("update campaign set instagram_username=%s where id_campaign=%s",self.LastJson['logged_in_user']['username'], self.id_campaign)



                # userIdentity['uuid']=self.uuid
                # userIdentity['device_id']=self.device_id
                # userIdentity['user'] = self.LastJson["logged_in_user"]
                # userIdentity['token'] = self.LastResponse.cookies["csrftoken"]
                # userIdentity['csrftoken'] = self.session.cookies.get("csrftoken",domain="i.instagram.com")
                # userIdentity['rank_token'] = self.rank_token
                # userIdentity['ds_user'] = self.session.cookies.get("ds_user",domain="i.instagram.com")
                # userIdentity['ds_user_id'] = self.session.cookies.get("ds_user_id",domain="i.instagram.com")
                # userIdentity['mid'] = self.session.cookies.get("mid",domain="i.instagram.com")
                # userIdentity['rur'] = self.session.cookies.get("rur",domain="i.instagram.com")
                # userIdentity['sessionid'] = self.session.cookies.get("sessionid",domain="i.instagram.com")
                # userIdentity['social_hash_bucket_id'] = self.session.cookies.get("social_hash_bucket_id",domain="i.instagram.com")
                # userIdentity['urlgen'] = self.session.cookies.get("urlgen",domain="i.instagram.com")
                #
                # with io.open('/Users/cbardas/instapy-log//campaign/'+self.id_campaign+'/user-identity.json', 'w', encoding='utf-8') as f:
                #     f.write(json.dumps(userIdentity, ensure_ascii=False))

                return True
            else:
                self.logger.info("login: Incorrect credentials or instagram verification required !")
                return False
        else:
            self.logger.info("login: Could not login user %s !", username)
            return False

    def loadJson(self, value):
        try:
            r = json.loads(value)
            # self.logger.info("loadJson: Successfully loaded json !")
            return r
        except:
            exceptionDetail = traceback.format_exc()
            # print(exceptionDetail)
            self.logger.info("loadJson: Could not load json, exception: %s", exceptionDetail)
            self.logger.info("loadJson: json value: %s", value)
            return {}

    def logout(self):

        if not self.isLoggedIn:
            return True
        self.isLoggedIn = not self.SendRequest('accounts/logout/')
        self.logger.info("logout: The bot is logged out !")
        return not self.isLoggedIn

    def SendRequest(self, endpoint, post=None, login=False, pauseOnBlock=True):
        if (not self.isLoggedIn and not login):
            self.logger.critical("Not logged in while accessing endpoint %s.",endpoint)
            return False

        # self.logger.info("Requesting %s: ",config.API_URL + endpoint)
        self.session.headers.update({'Connection': 'close',
                                     'Accept': '*/*',
                                     'Content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
                                     'Cookie2': '$Version=1',
                                     'Accept-Language': 'en-US',
                                     'User-Agent': config.USER_AGENT})
        try:
            self.total_requests += 1
            if post is not None:  # POST
                response = self.session.post(
                    config.API_URL + endpoint, data=post, verify=True)
            else:  # GET
                response = self.session.get(
                    config.API_URL + endpoint, verify=True)
        except Exception as e:
            self.logger.warning("ERROR: Processing the request: %s",str(e))
            return False

        if response.status_code == 200:
            self.LastResponse = response
            self.LastJson = self.loadJson(response.text)
            return True
        else:
            self.LastResponse = response
            details = None
            self.LastJson = self.loadJson(response.text)
            responseInfo = response.text
            self.logger.info("sendRequest: Request error url: %s: ", config.API_URL + endpoint)

            if response.status_code == 404  and pauseOnBlock!=False:
                responseInfo = "Page not found!"
                self.logger.warning(
                    "sendRequest: HTTP ERROR: STATUS %s, going to sleep 1 minute !" % (str(response.status_code)))
                sleep_minutes = 1
                time.sleep(sleep_minutes * 60)
            else:
                self.logger.warning(
                    "sendRequest: HTTP ERROR: STATUS %s , BODY: %s " % (str(response.status_code), response.text))

            if response.status_code == 400:
                errorFound=0
                responseObject = self.loadJson(response.text)

                if 'spam' in responseObject:
                    errorFound=1
                    details = "spam"
                    #if self.bot_type=="like_for_like":
                        #self.logger.warning("sendRequest: BOT IS BLOCKED. Going to exit like for like process. Reponse %s", responseObject)
                        #currentOperation = self.currentOperation if hasattr(self, "currentOperation") else None
                        #self.logApiError(responseInfo, currentOperation, config.API_URL, endpoint, response.status_code,details)
                        #raise Exception("sendRequest: SPAM: bot is blocked, going to exit")

                    sleep_minutes = self.get_spam_delay()
                    self.like_delay = self.like_delay_if_bot_blocked
                    self.follow_delay = self.follow_delay_if_bot_blocked
                    self.logger.warning(
                        "sendRequest: BOT IS BLOCKED, going to sleep %s minutes. The like delay was increased to %s seconds, and follow delay to %s" % (
                        sleep_minutes, self.like_delay, self.follow_delay))

                    time.sleep(sleep_minutes * 60)

                if 'message' in responseObject:

                    if responseObject['message']=="login_required":
                        errorFound=1
                        details="login_required"
                        currentOperation = self.currentOperation if hasattr(self, "currentOperation") else None
                        self.logApiError(responseInfo, currentOperation, config.API_URL, endpoint, response.status_code,details)
                        raise Exception("sendRequest: The user is not logged in")
                if 'error_type' in responseObject:
                    currentOperation = self.currentOperation if hasattr(self, "currentOperation") else None


                    if responseObject['error_type'] == 'sentry_block':
                        errorFound=1
                        details="sentry_block"
                        self.logger.warning("sendRequest: ********** FATAL ERROR ************* sentry_block")
                        self.logApiError(responseInfo, currentOperation, config.API_URL, endpoint,response.status_code, details)
                        raise Exception("sendRequest: ********** FATAL ERROR ************* sentry_block")

                    if responseObject['error_type'] == 'ip_block':
                        errorFound=1
                        details="ip_block"
                        self.logger.warning("sendRequest: ********** FATAL ERROR ************* ip_block")
                        self.logApiError(responseInfo, currentOperation, config.API_URL, endpoint,response.status_code, details)
                        raise Exception("sendRequest: ********** FATAL ERROR ************* ip_block")

                    self.logApiError(responseInfo, currentOperation, config.API_URL, endpoint,response.status_code, details)

                    if responseObject['error_type'] == 'checkpoint_challenge_required':
                        errorFound=1
                        self.logger.warning("sendRequest: Instagram requries phone verification")
                        self.notifyUserToVerifyInstagramAccount()
                        raise Exception("sendRequest: Instagram requires phone verification")


                    if responseObject['error_type'] == 'invalid_user':
                        errorFound=1
                        self.logger.warning("sendRequest: Invalid instagram user")
                        self.notifyUserInvalidCredentials()
                        raise Exception("sendRequest: Invalid instagram username")

                    if responseObject['error_type'] == 'bad_password':
                        errorFound=1
                        self.logger.warning("sendRequest: Invalid instagram password")
                        self.notifyUserInvalidCredentials()
                        raise Exception("sendRequest: Invalid instagram password")

                if errorFound==0 and self.bot_type!="scan_user_feed" and self.bot_type!="scan_user_profile" and self.bot_type!="scan_user_followers":
                    sleep_minutes = 1
                    self.logger.warning("Request return 400 error. Going to sleep %s minutes" % sleep_minutes)
                    # don t sleep on login fail
                    if login == False:
                        time.sleep(sleep_minutes * 60)

            elif response.status_code == 429:
                sleep_minutes = randint(6, 8)
                details = "That means too many requests"
                self.logger.warning("That means 'too many requests'. ""I'll go to sleep for %d minutes." % (sleep_minutes))
                time.sleep(sleep_minutes * 60)

            currentOperation = self.currentOperation if hasattr(self, "currentOperation") else None
            self.logApiError(responseInfo, currentOperation, config.API_URL, endpoint, response.status_code, details)

            # for debugging
            # try:
            #    self.LastResponse = response
            #    self.LastJson = self.loadJson(response.text)
            # except:
            #    pass
            # self.LastResponse=response
            return False

    def logApiError(self, responseInfo, currentOperation, apiUrl, endpoint,statusCode, details):
        insert(
            "insert into bot_log (id_user,log,operation,request,http_status,details,timestamp) values (%s,%s,%s,%s,%s,%s,now())",
            self.web_application_id_user, responseInfo, currentOperation, apiUrl + endpoint,
            str(statusCode), details)

    def syncFeatures(self):
        data = json.dumps({
            '_uuid': self.uuid,
            '_uid': self.user_id,
            'id': self.user_id,
            '_csrftoken': self.token,
            'experiments': config.EXPERIMENTS
        })
        return self.SendRequest('qe/sync/', self.generateSignature(data))

    def autoCompleteUserList(self):
        return self.SendRequest('friendships/autocomplete_user_list/')

    def notifyUserToVerifyInstagramAccount(self):

        if self.bot_type!="like_for_like":
            self.logger.info(
                "notifyUserToVerifyInstagramAccount: Going to send mail to user id: %s to enable instagram ccount",
                self.web_application_id_user)
            self.session.get("https://rest.angie.one/email/verifyInstagramAccount?id=" + str(self.web_application_id_user))
            self.logger.info("notifyUserToVerifyInstagramAccount: done sending email")

    def notifyUserInvalidCredentials(self):
        self.logger.info("notifyUserInvalidCredentials: bot type is %s",self.bot_type)

        #set instagram verified to 0
        insert("update campaign set instagram_verified=0,active=0 where id_campaign=%s",self.id_campaign)

        if self.bot_type != "like_for_like" and self.bot_type!="verify_account":
            self.logger.info(
                "notifyUserInvalidCredentials: Going to send mail to user id: %s to regarding invalid credentials",
                self.web_application_id_user)
            self.session.get(
                "https://rest.angie.one/email/notifyUserInvalidCredentials?id=" + str(self.web_application_id_user))
            self.logger.info("notifyUserInvalidCredentials: done sending email")

    def getTimelineFeed(self, amount=20):
        self.logger.info("Trying to get %s items from timeline feed" % amount)

        user_feed = []
        next_max_id = None
        securityBreak = 0

        while len(user_feed) < amount and securityBreak < 50:

            if not next_max_id:
                self.SendRequest('feed/timeline/')
            else:
                self.SendRequest('feed/timeline/?max_id=' + str(next_max_id))

            temp = self.LastJson
            if "items" not in temp:  # maybe user is private, (we have not access to posts)
                return []

            for item in temp["items"]:
                if 'pk' in item.keys():
                    user_feed.append(item)

            if "next_max_id" not in temp:
                self.logger.info("Total received %s posts from timeline feed" % len(user_feed))
                return user_feed

            next_max_id = temp["next_max_id"]

            securityBreak = securityBreak + 1
            self.logger.info("Iteration %s ,received %s items, total received %s" % (
            securityBreak, len(temp['items']), len(user_feed)))

            sleep_time = randint(1, 3)
            self.logger.info("Sleeping %s seconds" % sleep_time)
            time.sleep(sleep_time)

        self.logger.info("Total received %s posts from timeline feed" % len(user_feed))

        return user_feed

    def megaphoneLog(self):
        return self.SendRequest('megaphone/log/')

    def expose(self):
        data = json.dumps({
            '_uuid': self.uuid,
            '_uid': self.user_id,
            'id': self.user_id,
            '_csrftoken': self.token,
            'experiment': 'ig_android_profile_contextual_feed'
        })
        return self.SendRequest('qe/expose/', self.generateSignature(data))

    def uploadPhoto(self, photo, caption=None, upload_id=None):
        return uploadPhoto(self, photo, caption, upload_id)

    def downloadPhoto(self, media_id, filename, media=False, path='photos/'):
        return downloadPhoto(self, media_id, filename, media, path)

    def configurePhoto(self, upload_id, photo, caption=''):
        return configurePhoto(self, upload_id, photo, caption)

    def uploadVideo(self, photo, caption=None, upload_id=None):
        return uploadVideo(self, photo, caption, upload_id)

    def configureVideo(self, upload_id, video, thumbnail, caption=''):
        return configureVideo(self, upload_id, video, thumbnail, caption)

    def editMedia(self, mediaId, captionText=''):
        data = json.dumps({
            '_uuid': self.uuid,
            '_uid': self.user_id,
            '_csrftoken': self.token,
            'caption_text': captionText
        })
        return self.SendRequest('media/' + str(mediaId) + '/edit_media/', self.generateSignature(data))

    def removeSelftag(self, mediaId):
        data = json.dumps({
            '_uuid': self.uuid,
            '_uid': self.user_id,
            '_csrftoken': self.token
        })
        return self.SendRequest('media/' + str(mediaId) + '/remove/', self.generateSignature(data))

    def mediaInfo(self, mediaId):
        data = json.dumps({
            '_uuid': self.uuid,
            '_uid': self.user_id,
            '_csrftoken': self.token,
            'media_id': mediaId
        })
        return self.SendRequest('media/' + str(mediaId) + '/info/', self.generateSignature(data))

    def archiveMedia(self, media, undo=False):
        action = 'only_me' if not undo else 'undo_only_me'
        data = json.dumps({
            '_uuid': self.uuid,
            '_uid': self.user_id,
            '_csrftoken': self.token,
            'media_id': media['id']
        })
        return self.SendRequest('media/' + str(media['id']) + '/' + str(action) + '/?media_type=' +
                                str(media['media_type']), self.generateSignature(data))

    def deleteMedia(self, mediaId):
        data = json.dumps({
            '_uuid': self.uuid,
            '_uid': self.user_id,
            '_csrftoken': self.token,
            'media_id': mediaId
        })
        return self.SendRequest('media/' + str(mediaId) + '/delete/', self.generateSignature(data))

    def changePassword(self, newPassword):
        data = json.dumps({
            '_uuid': self.uuid,
            '_uid': self.user_id,
            '_csrftoken': self.token,
            'old_password': self.password,
            'new_password1': newPassword,
            'new_password2': newPassword
        })
        return self.SendRequest('accounts/change_password/', self.generateSignature(data))

    def explore(self):
        return self.SendRequest('discover/explore/')

    def comment(self, mediaId, commentText):
        data = json.dumps({
            '_uuid': self.uuid,
            '_uid': self.user_id,
            '_csrftoken': self.token,
            'comment_text': commentText
        })
        return self.SendRequest('media/' + str(mediaId) + '/comment/', self.generateSignature(data))

    def deleteComment(self, mediaId, commentId):
        data = json.dumps({
            '_uuid': self.uuid,
            '_uid': self.user_id,
            '_csrftoken': self.token
        })
        return self.SendRequest('media/' + str(mediaId) + '/comment/' + str(commentId) + '/delete/',
                                self.generateSignature(data))

    def removeProfilePicture(self):
        return removeProfilePicture(self)

    def setPrivateAccount(self):
        return setPrivateAccount(self)

    def setPublicAccount(self):
        return setPublicAccount(self)

    def getProfileData(self):
        return getProfileData(self)

    def editProfile(self, url, phone, first_name, biography, email, gender):
        return editProfile(self, url, phone, first_name, biography, email, gender)

    def getUsernameInfo(self, usernameId):
        return self.SendRequest('users/' + str(usernameId) + '/info/')

    def getSelfUsernameInfo(self):
        return self.getUsernameInfo(self.user_id)

    def getRecentActivity(self):
        activity = self.SendRequest('news/inbox/?')
        return activity

    def getFollowingRecentActivity(self):
        activity = self.SendRequest('news/?')
        return activity

    def getv2Inbox(self):
        inbox = self.SendRequest('direct_v2/inbox/?')
        return inbox

    def getUserTags(self, usernameId):
        tags = self.SendRequest('usertags/' + str(usernameId) +
                                '/feed/?rank_token=' + str(self.rank_token) + '&ranked_content=true&')
        return tags

    def getSelfUserTags(self):
        return self.getUserTags(self.user_id)

    def tagFeed(self, tag):
        userFeed = self.SendRequest(
            'feed/tag/' + str(tag) + '/?rank_token=' + str(self.rank_token) + '&ranked_content=true&')
        return userFeed

    def getMediaLikers(self, media_id):
        likers = self.SendRequest('media/' + str(media_id) + '/likers/?')
        return likers

    def getGeoMedia(self, usernameId):
        locations = self.SendRequest('maps/user/' + str(usernameId) + '/')
        return locations

    def getSelfGeoMedia(self):
        return self.getGeoMedia(self.user_id)

    def fbUserSearch(self, query):
        return fbUserSearch(self, query)

    def searchUsers(self, query):
        return searchUsers(self, query)

    def searchUsername(self, username):
        return searchUsername(self, username)

    def searchTags(self, query):
        return searchTags(self, query)

    def searchLocation(self, query='', lat=None, lng=None):
        return searchLocation(self, query, lat, lng)

    def syncFromAdressBook(self, contacts):
        return self.SendRequest('address_book/link/?include=extra_display_name,thumbnails',
                                "contacts=" + json.dumps(contacts))

    def getTimeline(self):
        query = self.SendRequest(
            'feed/timeline/?rank_token=' + str(self.rank_token) + '&ranked_content=true&')
        return query

    def getArchiveFeed(self):
        query = self.SendRequest(
            'feed/only_me_feed/?rank_token=' + str(self.rank_token) + '&ranked_content=true&')
        return query

    def getUserFeed(self, usernameId, maxid='', minTimestamp=None):

        query = self.SendRequest(
            'feed/user/' + str(usernameId) + '/?max_id=' + str(maxid) + '&min_timestamp=' + str(minTimestamp) +
            '&rank_token=' + str(self.rank_token) + '&ranked_content=true')

        items = 0

        if 'items' in self.LastJson:
            items = len(self.LastJson['items'])

        self.logger.info("api: Received %s items from user %s feed" % (items, usernameId))

        sleep_time = randint(1, 2)
        self.logger.info("api: Sleeping %s seconds" % sleep_time)
        time.sleep(sleep_time)

        return query

    def getSelfUserFeed(self, maxid='', minTimestamp=None):
        return self.getUserFeed(self.user_id, maxid, minTimestamp)

    def getHashtagFeed(self, hashtagString, amount=50, id_campaign=None, removeLikedPosts=False, removeFollowedUsers = False):
        if hashtagString[:1] == "#":
            hashtagString = hashtagString[1:]

        tries = 3
        feed = []
        next_max_id = None
        securityBreak = 0

        self.logger.info("getHashtagFeed: c:%s/hashtag:%s/amount:%s/removeLikedPosts:%s/removeFollowedUsers:%s. Started searching for posts by hashtag during 3 iterations." % (id_campaign, hashtagString, amount, removeLikedPosts, removeFollowedUsers))


        while len(feed) < amount and securityBreak < tries:
            if not next_max_id:
                self.SendRequest('feed/tag/' + hashtagString)
            else:
                self.SendRequest('feed/tag/' + hashtagString + '/?max_id=' + str(next_max_id))

            temp = self.LastJson

            # the result is damaged
            if "items" not in temp:
                self.logger.info("getHashtagFeed: c:%s/hashtag:%s/amount:%s/it:%s: No more posts with this hashtag found in http response, going to return %s posts " % (id_campaign, hashtagString, amount, securityBreak, len(feed)))
                return feed
            #todo: set the context message for above functions
            items = self.filterLinks(temp["items"], id_campaign=id_campaign, removeLikedPosts=removeLikedPosts, removeFollowedUsers=removeFollowedUsers)

            for item in items:
                feed.append(item)

            if "next_max_id" not in temp:
                self.logger.info("getHashtagFeed: c:%s/hashtag:%s/amount:%s/it:%s: Next max id is none, this means end of results/no more posts. Going to return %s posts. " % (id_campaign, hashtagString, amount, securityBreak, len(feed)))
                return feed

            next_max_id = temp["next_max_id"]

            self.logger.info("getHashtagFeed: c:%s/hashtag:%s/amount:%s/it:%s: This iteration received: %s posts, total received %s, total expected: %s " % (id_campaign, hashtagString, amount, securityBreak, len(temp["items"]), len(feed), amount))
            securityBreak = securityBreak + 1
            sleep_time = randint(1, 1)
            #self.logger.info("Sleeping %s seconds" % sleep_time)
            if len(feed) < amount and securityBreak < tries:
                time.sleep(sleep_time)

            self.logger.info("getHashtagFeed: c:%s/hashtag:%s/amount:%s/it:%s: END iterations, total received %s, total expected: %s " % (id_campaign, hashtagString, amount, securityBreak, len(feed), amount))
        return feed[:amount]

    def filterLinks(self, links, id_campaign=False, removeLikedPosts=False, removeFollowedUsers=False):

        self.logger.info("filterLinks: Going to filter %s links using options: id_campaign: %s, removeLikedPosts:%s, removeFollowedUsers:%s " % (len(links), id_campaign, removeLikedPosts, removeFollowedUsers))
        filteredLinks = []

        for item in links:
            if 'pk' in item.keys():
                filteredLinks.append(item)

        if id_campaign is False:
            return filteredLinks

        if removeLikedPosts is False and removeFollowedUsers is False:
            return filteredLinks

        filteredLinks = excludeAlreadyProcessedLinks(filteredLinks, id_campaign, removeLikedPosts, removeFollowedUsers, self.logger)

        return filteredLinks

    def getLocationFeed(self, locationId, amount=50, id_campaign=None, removeLikedPosts=False,removeFollowedUsers=False):
        self.logger.info("getLocationFeed: c:%s/location:%s/amount:%s/removeLikedPosts:%s/removeFollowedUsers:%s. Started searching for posts by location during 3 iterations." % (id_campaign, locationId, amount, removeLikedPosts, removeFollowedUsers))

        tries = 3
        feed = []
        next_max_id = None
        security_check = 0

        while len(feed) < amount and security_check < tries:

            if not next_max_id:

                self.SendRequest('feed/location/' + str(locationId))
            else:
                self.SendRequest('feed/location/' + str(locationId) + '/?max_id=' + str(next_max_id))

            temp = self.LastJson

            # the result is damaged
            if "items" not in temp:  # if no items
                self.logger.info("getLocationFeed: c:%s/location:%s/amount:%s/it:%s: No more posts with this location found in http response, going to return %s posts " % (id_campaign, locationId, amount, security_check, len(feed)))
                return feed

            items = self.filterLinks(temp["items"], id_campaign=id_campaign, removeLikedPosts=removeLikedPosts,removeFollowedUsers=removeFollowedUsers)

            for item in items:
                feed.append(item)

            if "next_max_id" in temp:
                next_max_id = temp["next_max_id"]
            else:
                self.logger.info("getLocationFeed: c:%s/location:%s/amount:%s/it:%s: Next max id is none, this means end of results/no more posts. Going to return %s posts. " % (id_campaign, locationId, amount, security_check, len(feed)))
                return feed

            security_check += 1

            sleep_time = randint(1, 1)
            self.logger.info("getLocationFeed: c:%s/location:%s/amount:%s/it:%s: This iteration received: %s posts, total received %s, total expected: %s " % (id_campaign, locationId, amount, security_check, len(temp["items"]), len(feed), amount))
            #self.logger.info("Sleeping %s seconds" % sleep_time)
            if len(feed)<amount and security_check < tries:
                time.sleep(sleep_time)

        self.logger.info("getLocationFeed: c:%s/location:%s/amount:%s/it:%s: END iterations, total received %s, total expected: %s " % (id_campaign, locationId, amount, security_check, len(feed), amount))
        return feed[:amount]

    def getPopularFeed(self):
        popularFeed = self.SendRequest(
            'feed/popular/?people_teaser_supported=1&rank_token=' + str(self.rank_token) + '&ranked_content=true&')
        return popularFeed

    def getUserFollowings(self, usernameId, maxid=''):
        return self.SendRequest('friendships/' + str(usernameId) + '/following/?max_id=' + str(maxid) +
                                '&ig_sig_key_version=' + config.SIG_KEY_VERSION + '&rank_token=' + self.rank_token)

    def getSelfUsersFollowing(self):
        return self.getUserFollowings(self.user_id)

    def getSelfUserFollowers(self):
        return self.getUserFollowers(self.user_id)

    def like(self, mediaId):
        data = json.dumps({
            '_uuid': self.uuid,
            '_uid': self.user_id,
            '_csrftoken': self.token,
            'media_id': mediaId
        })
        return self.SendRequest('media/' + str(mediaId) + '/like/', self.generateSignature(data))

    def unlike(self, mediaId):
        data = json.dumps({
            '_uuid': self.uuid,
            '_uid': self.user_id,
            '_csrftoken': self.token,
            'media_id': mediaId
        })
        return self.SendRequest('media/' + str(mediaId) + '/unlike/', self.generateSignature(data))

    def getMediaComments(self, mediaId):
        return self.SendRequest('media/' + str(mediaId) + '/comments/?')

    def setNameAndPhone(self, name='', phone=''):
        return setNameAndPhone(self, name, phone)

    def getDirectShare(self):
        return self.SendRequest('direct_share/inbox/?')

    def follow(self, userId):
        data = json.dumps({
            '_uuid': self.uuid,
            '_uid': self.user_id,
            'user_id': userId,
            '_csrftoken': self.token
        })
        return self.SendRequest('friendships/create/' + str(userId) + '/', self.generateSignature(data))

    def unfollow(self, userId):
        data = json.dumps({
            '_uuid': self.uuid,
            '_uid': self.user_id,
            'user_id': userId,
            '_csrftoken': self.token
        })
        return self.SendRequest('friendships/destroy/' + str(userId) + '/', self.generateSignature(data))

    def block(self, userId):
        data = json.dumps({
            '_uuid': self.uuid,
            '_uid': self.user_id,
            'user_id': userId,
            '_csrftoken': self.token
        })
        return self.SendRequest('friendships/block/' + str(userId) + '/', self.generateSignature(data))

    def unblock(self, userId):
        data = json.dumps({
            '_uuid': self.uuid,
            '_uid': self.user_id,
            'user_id': userId,
            '_csrftoken': self.token
        })
        return self.SendRequest('friendships/unblock/' + str(userId) + '/', self.generateSignature(data))

    def userFriendship(self, userId):
        data = json.dumps({
            '_uuid': self.uuid,
            '_uid': self.user_id,
            'user_id': userId,
            '_csrftoken': self.token
        })
        return self.SendRequest('friendships/show/' + str(userId) + '/', self.generateSignature(data))

    def generateSignature(self, data):
        try:
            parsedData = urllib.parse.quote(data)
        except AttributeError:
            parsedData = urllib.quote(data)

        return 'ig_sig_key_version=' + config.SIG_KEY_VERSION + '&signed_body=' + hmac.new(
            config.IG_SIG_KEY.encode('utf-8'), data.encode('utf-8'), hashlib.sha256).hexdigest() + '.' + parsedData

    def generateDeviceId(self, seed):
        volatile_seed = "12345"
        m = hashlib.md5()
        m.update(seed.encode('utf-8') + volatile_seed.encode('utf-8'))
        return 'android-' + m.hexdigest()[:16]

    def generateUUID(self, uuid_type):
        generated_uuid = str(uuid.uuid4())
        if (uuid_type):
            return generated_uuid
        else:
            return generated_uuid.replace('-', '')

    def getLikedMedia(self, maxid=''):
        return self.SendRequest('feed/liked/?max_id=' + str(maxid))

    def getUserFollowers(self, usernameId, amount=50, next_max_id=None):
        self.logger.info("Trying to get %s followers  of %s This might take a while." % (amount, usernameId))
        self.logger.info("Next max id is: %s", next_max_id)
        followers = []
        securityBreak = 0
        result = {}
        previous_next_max_id = next_max_id
        while len(followers) < amount and securityBreak < 100:

            if next_max_id == '' or next_max_id == None:
                self.SendRequest('friendships/' + str(usernameId) + '/followers')
            else:
                self.SendRequest('friendships/' + str(usernameId) + '/followers/?max_id=' + str(next_max_id))

            temp = self.LastJson

            # the result is damaged
            if "users" not in temp:  # if no items
                self.logger.info(
                    "End of the line: Total received %s followers of user %s" % (len(followers), usernameId))
                result['followers'] = followers
                result['next_max_id'] = None
                result['previous_next_max_id'] = previous_next_max_id
                return result

            for item in temp["users"]:
                followers.append(item)

            securityBreak = securityBreak + 1
            self.logger.info("Iteration %s ,received %s items, total received %s followers" % (
            securityBreak, len(temp['users']), len(followers)))

            if "next_max_id" not in temp:
                self.logger.info(
                    "End of the line: Total received %s followers of user %s" % (len(followers), usernameId))
                result['followers'] = followers
                result['next_max_id'] = None
                result['previous_next_max_id'] = previous_next_max_id
                return result

            next_max_id = temp["next_max_id"]
            previous_next_max_id = next_max_id

            sleep_time = randint(5, 10)
            self.logger.info("Sleeping %s seconds" % sleep_time)
            time.sleep(sleep_time)

        self.logger.info("Total received %s followers of user %s" % (len(followers), usernameId))

        result['followers'] = followers
        result['next_max_id'] = next_max_id
        result['previous_next_max_id'] = previous_next_max_id
        return result

    def getTotalFollowings(self, usernameId, amount=None):
        sleep_track = 0
        following = []
        next_max_id = ''
        self.getUsernameInfo(usernameId)
        if "user" in self.LastJson:
            if amount:
                total_following = amount
            else:
                total_following = self.LastJson["user"]['following_count']
            if total_following > 200000:
                print("Consider temporarily saving the result of this big operation. This will take a while.\n")
        else:
            return False
        with tqdm(total=total_following, desc="Getting following", leave=False) as pbar:
            while True:
                self.getUserFollowings(usernameId, next_max_id)
                temp = self.LastJson
                try:
                    pbar.update(len(temp["users"]))
                    for item in temp["users"]:
                        following.append(item)
                        sleep_track += 1
                        if sleep_track >= 20000:
                            sleep_time = randint(120, 180)
                            print("\nWaiting %.2f min. due to too many requests." % float(sleep_time / 60))
                            time.sleep(sleep_time)
                            sleep_track = 0
                    if len(temp["users"]) == 0 or len(following) >= total_following:
                        return following[:total_following]
                except:
                    return following[:total_following]
                if temp["big_list"] is False:
                    return following[:total_following]
                next_max_id = temp["next_max_id"]

    def getTotalUserFeed(self, usernameId, minTimestamp=None):
        user_feed = []
        next_max_id = ''
        while 1:
            self.getUserFeed(usernameId, next_max_id, minTimestamp)
            temp = self.LastJson
            if "items" not in temp:  # maybe user is private, (we have not access to posts)
                return []
            for item in temp["items"]:
                user_feed.append(item)
            if "more_available" not in temp or temp["more_available"] is False:
                return user_feed
            next_max_id = temp["next_max_id"]

    # this gives all medias posted by the logged user
    def getTotalSelfUserFeed(self, minTimestamp=None):
        return self.getTotalUserFeed(self.user_id, minTimestamp)

    def getTotalSelfFollowers(self):
        return self.getTotalFollowers(self.user_id)

    def getTotalSelfFollowings(self):
        return self.getTotalFollowings(self.user_id)

    def getTotalLikedMedia(self, scan_rate=1):
        next_id = ''
        liked_items = []
        for _ in range(0, scan_rate):
            temp = self.getLikedMedia(next_id)
            temp = self.LastJson
            next_id = temp["next_max_id"]
            for item in temp["items"]:
                liked_items.append(item)
        return liked_items
