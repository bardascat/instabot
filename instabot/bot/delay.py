"""
    Function to calculate delays for like/follow/unfollow etc.
"""

import time
import random
import logging
from random import randint

def add_dispersion(delay_value):
    return delay_value * 3 / 4 + delay_value * random.random() / 2


# this function will sleep only if elapsed time since `last_action` is less than `target_delay`
def sleep_if_need(last_action, target_delay):
    logger = logging.getLogger('[instabot]')
    now = time.time()
    elapsed_time = now - last_action
    if (elapsed_time < target_delay):
        remains_to_wait = target_delay - elapsed_time
        sleep_time = add_dispersion(remains_to_wait)
        logger.info("Sleep %s seconds" % sleep_time)
        time.sleep(sleep_time)

#remove the original implementation just to make sure the boot sleeps
def like_delay(bot):
    #sleep_if_need(bot.last_like, bot.like_delay)
    bot.last_like = time.time()

    logger = logging.getLogger('[instabot]')
    sleep_time = randint(8,30)
    logger.info("like_delay: Sleeping %s seconds, Max delay is: %s" % (sleep_time,bot.like_delay))
    time.sleep(sleep_time)


def unlike_delay(bot):
    sleep_if_need(bot.last_unlike, bot.unlike_delay)
    bot.last_unlike = time.time()

#todo fix this
def follow_delay(bot):
    sleep_if_need(bot.last_follow, bot.follow_delay)
    bot.last_follow = time.time()


def unfollow_delay(bot):
    sleep_if_need(bot.last_unfollow, bot.unfollow_delay)
    bot.last_unfollow = time.time()


def comment_delay(bot):
    sleep_if_need(bot.last_comment, bot.comment_delay)
    bot.last_comment = time.time()


def block_delay(bot):
    sleep_if_need(bot.last_block, bot.block_delay)
    bot.last_block = time.time()


def unblock_delay(bot):
    sleep_if_need(bot.last_unblock, bot.unblock_delay)
    bot.last_unblock = time.time()


def error_delay(bot):
    time.sleep(10)


def small_delay(bot):
    time.sleep(add_dispersion(3))


def very_small_delay(bot):
    time.sleep(add_dispersion(0.7))
