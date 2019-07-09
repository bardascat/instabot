import datetime
import glob
import os
import re

from instabot.api import api_db


def getActiveUsers():
    query = "select * from users join campaign on (users.id_user=campaign.id_user) join user_subscription on (users.id_user = user_subscription.id_user) where (user_subscription.end_date>now() or user_subscription.end_date is null) and campaign.active=1 and campaign.id_campaign=1 order by users.id_user asc"
    users = api_db.select(query)
    return users


def getFollowedUsers(path):
    followedUsers = []
    files = []
    os.chdir(path)
    for file in glob.glob("*.log"):
        files.append(file)

    for file in files:
        filePath = path + "/" + file
        print("Going to scan " + filePath)
        for i, line in enumerate(open(filePath)):
            m = re.search('(?<=Going to follow: )(.*)', line)
            if m is not None:
                userFollowed = m.group(1)
                followedUsers.append(userFollowed)

    return followedUsers


path = "/home/instapy-log/campaign/logs"
#path = "/Users/cbardas/instapy-log/campaign/logs"
users = getActiveUsers()


def isUserFollowed(id_campaign, instagramUsername):
    id_campaign = str(id_campaign)
    print("checkIfUserIsFollowed: id_campaign:" + id_campaign + " instagramUsername:" + instagramUsername)
    client = api_db.getMongoConnection()
    db = client.angie_app
    userFollowed = db.bot_action.find_one({"username": instagramUsername, "id_campaign": int(id_campaign),
                                           "bot_operation": {"$regex": "^follow_engagement_"}})
    client.close()
    if userFollowed is None:
        return False
    print("User " + instagramUsername + " will be skipped, it's already in db!")
    return True


def markUserFollowed(id_campaign, instagramUsername, id_user):
    client = api_db.getMongoConnection()
    db = client.angie_app

    db.bot_action.insert({
        "id_campaign": id_campaign,
        "id_user": id_user,
        "instagram_id_user": None,
        "full_name": instagramUsername,
        "username": instagramUsername,
        "user_image": None,
        "post_id": None,
        "post_image": None,
        "post_link": None,
        "bot_operation": "follow_engagement_by_hashtag",
        "bot_operation_value": None,
        "bot_operation_reverted": None,
        "id_log": None,
        "status": True,
        "timestamp": datetime.datetime.now(),
    })

    client.close()
    return True


users = getActiveUsers()

for user in users:
    print("Going to process angie user" + user["email"])
    followerUsers = getFollowedUsers(path + "/" + str(user['id_campaign']))
    print("Found " + str(len(users)) + " followed users for this user.")
    print("Going to check with database")

    for followedUser in followerUsers:
        if isUserFollowed(user['id_campaign'], followedUser) == False:
            print("User " + followedUser + " is not followed, going to save it in db.")
            markUserFollowed(user['id_campaign'], followedUser, user['id_user'])
    print("Done processing angie user" + user["email"])

print("Done executing the script, going to exit !")

# TODO: check if the users are in database, otherwise create the follow record.
