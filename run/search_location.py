# -*- coding: utf-8 -*-
import argparse
import codecs
import os
import sys
import json

stdout = sys.stdout
sys.stdout = codecs.getwriter('utf8')(sys.stdout)
sys.path.append(os.path.join(sys.path[0], '../'))

parser = argparse.ArgumentParser(add_help=True)
parser.add_argument('-location', type=str, help="location")
parser.add_argument('-u', type=str, help="username")
parser.add_argument('-p', type=str, help="password")
args = parser.parse_args()

if not args.u or not args.p or not args.location:
    exit(0)

from instabot import Bot
bot = Bot(id_campaign=False,multiple_ip=None)
status  = bot.login(username=args.u,password=args.p)
if status!=1:
  exit("Could not login into account. Status error:" + str(status))
result = bot.searchLocation(query=args.location)

parsedResult=[]

if not result:
    exit(0)
else:
    for item in result:
        r={}
        r['id']=item['location']['pk']
        r['name']=item['title']
        parsedResult.append(r)

    result=json.dumps(parsedResult)
    print(result)

