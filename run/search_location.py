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
parser.add_argument('-location', type=str, help="location")
parser.add_argument('-id_campaign', type=str, help="campaign")
args = parser.parse_args()

if not args.location:
    exit(0)

campaign = api_db.fetchOne("select username,password,timestamp,id_campaign from campaign where id_campaign=%s",
                           args.id_campaign)

bot = Bot(id_campaign=args.id_campaign, multiple_ip=True, hide_output=True)
bot.logger.info("search_location:Going to search the location %s" % (args.location))

status = bot.login(username=campaign['username'], password=campaign['password'], storage=False)
if status != True:
    print(bot.LastResponse.text)
    exit()
result = bot.searchLocation(query=args.location)
parsedResult = []

if not result:
    exit(0)
else:
    for item in result:
        r = {}
        r['address']=item['subtitle']
        r['id'] = item['location']['pk']
        r['name'] = item['title']
        parsedResult.append(r)

    result = json.dumps(parsedResult)
    print(result)
