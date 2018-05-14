# -*- coding: utf-8 -*-
import argparse
import codecs
import os
import sys
import traceback
import json
from instabot import Bot

stdout = sys.stdout
sys.stdout = codecs.getwriter('utf8')(sys.stdout)
sys.path.append(os.path.join(sys.path[0], '../'))

parser = argparse.ArgumentParser(add_help=True)
parser.add_argument('-settings', type=str, help="settings")
args = parser.parse_args()

if args.settings is None:
    exit("dispatcher: settings are not specified !")

result = {}
try:
    settings=json.loads(args.settings)
    bot = Bot(id_campaign=str(settings['id_campaign']), multiple_ip=True, hide_output=True, bot_type="verify_account")
    bot.logger.info("verify_account:Going to verify the account... username %s, password %s" % (settings['u'], settings['p']))
    status = bot.login(username=settings['u'], password=settings['p'], force=True, storage=False)
    result["status"] = True
    result["data"] = bot.LastResponse.text
    print(json.dumps(result))
except:
    exceptionDetail = traceback.format_exc()
    #print(exceptionDetail)
    result["status"] = False

    if bot.LastResponse != None:
        result["data"] = bot.LastResponse.text
    result["exception"] = exceptionDetail
    print(json.dumps(result))
