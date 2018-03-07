import time
import psutil
import logging
import os
from instabot.api import api_db
import subprocess

logging.basicConfig(format='%(asctime)s %(message)s',filename='/home/instabot-log/like_for_like_dispatcher.log',level=logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger = logging.getLogger('[l4l]')
logger.setLevel(logging.DEBUG)
logger.addHandler(ch)

DEVNULL = open(os.devnull, 'wb')

def pauseProcess(pid):
	logger.info("pauseProcess: pausing process: %s",pid)
	p = psutil.Process(pid)
	p.suspend()
	logger.info("pauseProcess: process %s is paused", pid)
	
def startLikeForLikeProcess(id_campaign):
	logger.info("startLikeForLikeProcess: Starting like for like process for campaign %s",id_campaign)
	processName = "angie_like_for_like_idc" + str(id_campaign)
	
	logger.info("startLikeForLikeProcess: checking if there is already a process started with name %s", processName)
	pid=findProcessPid(processName)
	if pid!=False:
	   logger.info("startLikeForLikeProcess: Error - there is already an active like for like process for campaign %s, GOING TO SKIP THIS USER", id_campaign)
	   return False
	else:
	   logger.info("startLikeForLikeProcess: All good, the like for like process with name %s is not active, going to start it now !", processName)
	   
	subprocess.Popen("bash -c \"exec -a " + processName + " /usr/bin/python /projects/instabot/run/like_for_like.py -angie_campaign=" + str(
            id_campaign) + "\"", stdin=None, stdout=DEVNULL, stderr=DEVNULL, close_fds=True, shell=True)
	logger.info("startLikeForLikeProcess: Successfully started process for campaign %s", id_campaign)

def findProcessPid(processName):
	logger.info("getProcessPid:Searching process with name :%s ", processName)
	for p in psutil.process_iter():
		cmdline=p.cmdline()
		if len(cmdline)>0:
			if processName in cmdline[0]:
				logger.info("getProcessPid:Found %s, pid %s" % (cmdline[0], p.pid))
				return p.pid
			
	logger.info("getProcessPid: Did not find any process for name  %s",processName)
	return False

def startLikeForLike(user):
	pid=findProcessPid('angie_idc'+str(user['id_campaign']))
	if pid==False:
		logger.info("startLikeForLike: Bot campaign process is NOT running for campaign %s.",user['id_campaign'])
		#start process
		startLikeForLikeProcess(user['id_campaign'])
	else:
		#pause current process and start a new one
		logger.info("startLikeForLike: Bot campaign process %s is RUNNING for campaign %s, going to pause it " % ('angie_idc'+str(user['id_campaign']), user['id_campaign'])
		pauseProcess(pid)
		startLikeForLikeProcess(user['id_campaign'])
	



#select users that have an active subscription, and have pending posts to like
result = api_db.select("select users.id_user,email,username,campaign.password,campaign.id_campaign from users  join campaign on (users.id_user=campaign.id_user) join user_subscription on (users.id_user = user_subscription.id_user)  where (user_subscription.end_date>now() or user_subscription.end_date is null) and (select count(*) from user_post_log where id_user=users.id_user)<(select count(*) from user_post) and users.id_user=1");
#logger.info(result)
logger.info("Found %s users with pending work",len(result))
for user in result:
	logger.info("Going to process user %s",user['email'])
	#check if bot is already running for this campaign
	
	startLikeForLike(user)
	
	logger.info("Going to wait 1 seconds before processing another user !")
	time.sleep(1)
	
	
	

	