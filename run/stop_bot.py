import time
import psutil
import logging
import os
import signal
from random import randint

logging.basicConfig(format='%(asctime)s %(message)s',filename='/home/instabot-log/stop_bot.log',level=logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger = logging.getLogger('[l4l]')
logger.setLevel(logging.DEBUG)
logger.addHandler(ch)

def killProcess(pid):
	logger.info("killProcess: killing process: %s",pid)
	os.kill(pid, signal.SIGKILL) 

def stopProcesses():
	logger.info("stopProcesses:Searching process...")
	
	for p in psutil.process_iter():
		cmdline=p.cmdline()
		processname = 'angie_idc'
		processnameInstapy = 'angie_instapy_idc' 
		if len(cmdline)>0:
			if processname in cmdline[0] or processnameInstapy in cmdline[0]:
				logger.info("stopProcesses:Found %s, pid %s, going to kill it" % (cmdline[0], p.pid))
				killProcess(p.pid)
				sleep_minutes = randint(1, 2)
				logger.info("stopProcesses: Going to sleep %s until killing the next bot", sleep_minutes)
				time.sleep(sleep_minutes*60)
				
				
	logger.info("stopProcesses: DONE")

stopProcesses()
	