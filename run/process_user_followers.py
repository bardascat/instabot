import logging
import time
import traceback
from instabot.bot.bot_process_followers import BotProcessFollowers
import psutil

BASE_DIR = "/home/ubuntu/instabot-log/"
#BASE_DIR="/home/ubuntu/instabot-log/"

logging.basicConfig(format='%(asctime)s %(message)s',
                    filename=BASE_DIR + 'process_followers/' + time.strftime("%d.%m.%Y") + '.log',
                    level=logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger = logging.getLogger('[pf]')
logger.setLevel(logging.DEBUG)
logger.addHandler(ch)


def canProcessStart(processName):
    timesStarted = 0

    for p in psutil.process_iter():
        cmdline = p.cmdline()
        if len(cmdline) > 1:
            if processName in cmdline[0]:
                timesStarted = timesStarted + 1

    if timesStarted > 1:
        return False
    else:
        return True


try:

    processName = "angie_process_user_followers"
    logger.info("angie_process_user_followers: checking if there is already a process started with name: %s",
                processName)
    canStart = canProcessStart(processName)

    if not canStart:
        raise Exception("Error: there is already a  process with name %s. Going to exit", processName)
    else:
        logger.info("process_user_followers: All good no other %s process is running.", processName)

    bot = BotProcessFollowers(logger)
    bot.process()
    logger.info("DONE PROCESS FOLLOWERS, GOING TO CLOSE THE APP !")

except:
    exceptionDetail = traceback.format_exc()
    print(exceptionDetail)
    logger.info("FATAL ERROR !")
    logger.info(exceptionDetail)
