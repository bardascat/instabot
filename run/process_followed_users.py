import re
import glob, os
from instabot import Bot
from instabot.api import api_db



def getActiveUsers():
    query = "select * from users join campaign on (users.id_user=campaign.id_user) join user_subscription on (users.id_user = user_subscription.id_user) where (user_subscription.end_date>now() or user_subscription.end_date is null) and campaign.active=1 and campaign.id_campaign=1 order by users.id_user asc"
    users = api_db.select(query)
    return users

def getFollowedUsers(path):
    followedUsers=[]
    files=[]
    os.chdir(path)
    for file in glob.glob("*.log"):
        files.append(file)


    for file in files:
        filePath=path+"/"+file
        print("Going to scan "+filePath)
        for i, line in enumerate(open(filePath)):
            m = re.search('(?<=Going to follow: )(.*)', line)
            if m is not None:
                userFollowed = m.group(1)
                followedUsers.append(userFollowed)

    return followedUsers

path="/home/instapy-log/campaign/logs"
users = getActiveUsers()

for user in users:
    print("Going to process user"+ user["email"])
    getFollowedUsers(path+"/"+user['id_campaign'])
