"""
    All methods must return media_ids that can be
    passed into e.g. like() or comment() functions.
"""

from ..api import api_db
import math
import datetime

def getBotOperations(self, id_campaign):

    totalLikePercentage = 0
    totalFollowPercentage = 0
    totalLikeOperations=0
    totalFollowOperations=0

    operations = api_db.select("SELECT configName,id_config, percentageAmount FROM campaign_config where id_campaign=%s and enabled=1",
                               id_campaign)
    for operation in operations:

        if 'like_other_users_followers' in operation['configName'] or 'follow_other_users_followers' in operation['configName']:
            users = api_db.select("select * from instagram_users where id_config=%s and enabled=1",
                                  operation['id_config'])
            operation['list'] = users

        if 'like_posts_by_hashtag' in operation['configName'] or 'follow_users_by_hashtag' in operation['configName']:
            hashtags = api_db.select("select * from instagram_hashtags where id_config=%s and enabled=1",
                                     operation['id_config'])
            operation['list'] = hashtags

        if 'like_posts_by_location' in operation['configName'] or 'follow_users_by_location' in operation['configName']:
            locations = api_db.select("select * from instagram_locations where id_config=%s and enabled=1",
                                      operation['id_config'])
            operation['list'] = locations

        if 'like' in operation['configName']:
            totalLikePercentage += operation['percentageAmount']
            totalLikeOperations+=1

        elif 'follow' in operation['configName']:
            totalFollowPercentage += operation['percentageAmount']

            #the unfollow operation has a fixed percentage of 40%
            if operation['configName']!="unfollow":
                totalFollowOperations+=1


        parameters = api_db.select("select * from campaign_config_parameters where id_config=%s",
                                   operation['id_config'])

        operation['parameters'] = parameters


    #apply percentage
    if totalLikePercentage<100 and totalLikePercentage>0:
        self.logger.info("BOTUTIL: Unused LIKE percentage is %s, going to distribute it to %s like operations" % (100-totalLikePercentage, totalLikeOperations))
        remainingLikePercentage = math.ceil (math.ceil(100-totalLikePercentage) / math.ceil(totalLikeOperations))
        self.logger.info("BOTUTIL: Each operation will receive %s extra percentage !", remainingLikePercentage)

        for operation in operations:
            if 'like' in operation['configName']:
                operation['percentageAmount']+=remainingLikePercentage

    if totalFollowPercentage<100 and totalFollowPercentage>0:
        
        self.logger.info("BOTUTIL: Unused follow percentage is %s, going to distribute it to %s follow operations" % (100- totalFollowPercentage, totalFollowOperations))
        
        if totalFollowOperations==0:
          self.logger.info("BOTUTIL: no available operations of type follow. Probably it is set the unfollow operation with fixed percentage !")
        else:
          remainingFollowPercentage = math.ceil(math.ceil(100 - totalFollowPercentage) / math.ceil(totalFollowOperations))
          self.logger.info("BOTUTIL: Each operation of type follow will receive %s extra percentage !", remainingFollowPercentage)

          for operation in operations:
              if  str(operation['configName']).startswith("follow") and operation['configName']!="unfollow":
                  operation['percentageAmount'] += remainingFollowPercentage

    for op in operations:
        self.logger.info("Percentage: %s , Amount: %s" % (op['percentageAmount'], op['configName']))


    return operations