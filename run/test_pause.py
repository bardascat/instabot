# -*- coding: utf-8 -*-
import argparse
import codecs
import os
import sys
import json
from instabot.api import api_db
from instabot import Bot

stdout = sys.stdout
sys.stdout = codecs.getwriter('utf8')(sys.stdout)
sys.path.append(os.path.join(sys.path[0], '../'))

parser = argparse.ArgumentParser(add_help=True)
parser.add_argument('-id_campaign', type=str, help="campaign")
args = parser.parse_args()


campaign = api_db.fetchOne("select username,password,timestamp,id_campaign from campaign where id_campaign=%s",
                           args.id_campaign)

bot = Bot(id_campaign=args.id_campaign, multiple_ip=True, hide_output=False)

delay = bot.get_spam_delay(bot)

print(delay)

