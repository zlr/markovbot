import os
import time
import tweepy
import logging
from markovbot import MarkovBot

 
logger = logging.getLogger('markovbot')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
logger.addHandler(ch)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)


CONSUMER_KEY = os.environ["CONSUMER_KEY"]
CONSUMER_SECRET = os.environ["CONSUMER_SECRET"]
ACCESS_KEY = os.environ["ACCESS_KEY"]
ACCESS_SECRET = os.environ["ACCESS_SECRET"]
TWEETS = os.environ["TWEETS"]
SLEEPING = int(os.environ["SLEEPING"])


# use tweetpy instead 
try:
    auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
    auth.set_access_token(ACCESS_KEY, ACCESS_SECRET)
    api = tweepy.API(auth)
    logger.debug("Successfull auth")
except tweepy.TweepError as e:
    logger.debug("Failed to auth " + e.response.text)

# # # # #
# INITIALISE

# Initialise a MarkovBot instance
tweetbot = MarkovBot()

try:
    # Get the current directory's path
    dirname = os.path.dirname(os.path.abspath(__file__))
    # Construct the path to the book
    book = os.path.join(dirname, TWEETS)
    # Make your bot read the book!
    tweetbot.read(book)
except:
    logging.debug("Failed to load book " + TWEETS)



# # # # #
# TEXT GENERATION

# Generate text by using the generate_text method:
#   The first argument is the length of your text, in number of words
#   The 'seedword' argument allows you to feed the bot some words that it
#   should attempt to use to start its text. It's nothing fancy: the bot will
#   simply try the first, and move on to the next if he can't find something
#   that works.

# Print your text to the console

while True:
    try:
        tweet = tweetbot.generate_text(25, seedword=[u'loser', u'sad', u'china'])
        logger.debug('tweetbot says: ' + tweet)
        api.update_status(tweet)
        logger.debug("Sleeping for " + str(SLEEPING))
        time.sleep(SLEEPING)
        logger.debug("Finished sleeping")
    except tweepy.TweepError as e:
        logger.debug("Teweepy Error " + e.response.text)
        pass


# # # # # #
# # TWITTER

# # The MarkovBot uses @sixohsix' Python Twitter Tools, which is a Python wrapper
# # for the Twitter API. Find it on GitHub: https://github.com/sixohsix/twitter

# # ALL YOUR SECRET STUFF!
# # Make sure to replace the ''s below with your own values, or try to find
# # a more secure way of dealing with your keys and access tokens. Be warned
# # that it is NOT SAFE to put your keys and tokens in a plain-text script!

# # Consumer Key (API Key)
# cons_key = CONSUMER_KEY
# # Consumer Secret (API Secret)
# cons_secret = CONSUMER_SECRET
# # Access Token
# access_token = ACCESS_KEY
# # Access Token Secret
# access_token_secret = ACCESS_SECRET

# # Log in to Twitter
# tweetbot.twitter_login(cons_key, cons_secret, access_token, access_token_secret)

# # The target string is what the bot will reply to on Twitter. To learn more,
# # read: https://dev.twitter.com/streaming/overview/request-parameters#track
# targetstring = 'MarryMeFreud'
# # Keywords are words the bot will look for in tweets it'll reply to, and it
# # will attempt to use them as seeds for the reply
# keywords = ['marriage', 'ring', 'flowers', 'children', 'religion']
# # The prefix will be added to the start of all outgoing tweets.
# prefix = None
# # The suffix will be added to the end of all outgoing tweets.
# suffix = '#FreudSaysIDo'
# # The maxconvdepth is the maximum depth of the conversation that the bot will
# # still reply to. This is relevant if you want to reply to all tweets directed
# # at a certain user. You don't want to keep replying in the same conversation,
# # because that would be very annoying. Be responsible, and allow your bot only
# # a shallow conversation depth. For example, a value of 2 will allow the bot
# # to only reply in conversations where there are two or less replies to the
# # original tweet.
# maxconvdepth = None

# # Start auto-responding to tweets by calling twitter_autoreply_start
# # This function operates in a Thread in the background, so your code will not
# # block by calling it.
# # tweetbot.twitter_autoreply_start(targetstring, keywords=keywords, prefix=prefix, suffix=suffix, maxconvdepth=maxconvdepth)
 
# # Start periodically tweeting. This will post a tweet every X days, hours, and
# # minutes. (You're free to choose your own interval, but please don't use it to
# # spam other people. Nobody likes spammers and trolls.)
# # This function operates in a Thread in the background, so your code will not
# # block by calling it.
# tweetbot.twitter_tweeting_start(days=0, hours=0, minutes=10, keywords=None, prefix=None, suffix=None)

# # DO SOMETHING HERE TO ALLOW YOUR BOT TO BE ACTIVE IN THE BACKGROUND
# # You could, for example, wait for a week:
# secsinweek = 7 * 24 * 60 * 60
# time.sleep(secsinweek)
 
# # Use the following to stop auto-responding
# # (Don't do this directly after starting it, or your bot will do nothing!)
# #tweetbot.twitter_autoreply_stop()

# # Use the following to stop periodically tweeting
# # (Don't do this directly after starting it, or your bot will do nothing!)
# tweetbot.twitter_tweeting_stop()