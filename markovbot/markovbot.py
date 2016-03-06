# -*- coding: utf-8 -*-
#
# For installation instructions and more information, please refer to:
# http://www.pygaze.org/2016/03/tutorial-creating-a-twitterbot/
# (This includes instructions to install the Twitter library used here)
#
# This file is part of markovbot, created by Edwin Dalmaijer
# GitHub: https://github.com/esdalmaijer/markovbot
#
# Markovbot is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# Markovbot is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with markovbot.  If not, see <http://www.gnu.org/licenses/>.


# native imports
import os
import sys
import copy
import time
import pickle
import random
from threading import Thread, Lock
from multiprocessing import Queue

# external imports
# Twitter package: https://pypi.python.org/pypi/twitter
# Homepage of Twitter package: http://mike.verdone.ca/twitter/
try:
	import twitter
	IMPTWITTER = True
except:
	print(u"WARNING from Markovbot: Could not load the 'twitter' library, so Twitter functionality is not available.")
	IMPTWITTER = False


class MarkovBot():
	
	"""Class to generate text with a Markov chain, with support to read and
	post updates to Twitter accounts.
	"""
	
	def __init__(self):
		
		"""Initialises the bot.
		"""
		
		# # # # #
		# DATA

		# Create an empty dict for the data
		self.data = {}
		

		# # # # #
		# TWITTER

		# Starting value for the Twitter and TwitterStream instances
		self._t = None
		self._ts = None
		# Create locks for these instances, so they won't be accessed at the
		# same time by different threads.
		self._tlock = Lock()
		self._tslock = Lock()

		# Create a Boolean that indicates whether the bot is logged in, and
		# a placeholder for the credentials of the user that is logged in
		self._loggedin = False
		self._credentials = None
		
		# Create variables to keep track of tweets that should not be
		# replied to. The self._maxconvdepth value determines the maximum
		# conversation lenght that this bot is allowed to participate in.
		# Keep the number low to prevent the bot from being spammy.
		self._nonotweets = []
		self._maxconvdepth = None
		
		# Placeholders for debugging values of the last incoming and
		# outgoing tweets
		self._lasttweetin = None
		self._lasttweetout = None
		
		# Start the autoreplying thread
		self._autoreplying = False
		self._targetstring = None
		self._keywords = None
		self._tweetprefix = None
		self._tweetsuffix = None
		if IMPTWITTER:
			self._autoreplythreadlives = True
			self._autoreplythread = Thread(target=self._autoreply)
			self._autoreplythread.daemon = True
			self._autoreplythread.name = u'autoreplier'
			self._autoreplythread.start()
		else:
			self._autoreplythreadlives = False
		
		# Start the tweeting thread
		self._autotweeting = False
		self._tweetinginterval = None
		self._tweetingjitter = None
		self._tweetingkeywords = None
		self._tweetingprefix = None
		self._tweetingsuffix = None
		if IMPTWITTER:
			self._tweetingthreadlives = True
			self._tweetingthread = Thread(target=self._autotweet)
			self._tweetingthread.daemon = True
			self._tweetingthread.name = u'autotweeter'
			self._tweetingthread.start()
		else:
			self._tweetingthreadlives = False


	def clear_data(self):
		
		"""Clears the current internal data. NOTE: This does not remove
		existing pickled data!
		"""
		
		# Overwrite data
		self.data = {}


	def generate_text(self, length, seedword=None, verbose=False, \
		maxtries=100):
		
		"""Generates random text based on the provided database.
		
		Arguments
		
		length		-	An integer value indicating the amount of words
						that need to be produced.
		
		Keyword Arguments
		
		seedword		-	A string that indicates what word should be in
						the sentence. If None is passed, or if the word
						is not in the database, a random word will be
						chosen. This value can also be a list of words,
						in which case the list will be processed
						one-by-one until a word is found that is in the
						database.
		
		verbose		-	Boolean that indicates whether this function
						should bother you with excessibe and unnecessary
						messages whenever it can't immeadiately produce
						a text (it will still raise an Exception after
						maxtries attempts).
		
		maxtries		-	Integer indicating how many attempts the function
						is allowed to construct some text (sometimes
						this fails, and I couldn't be bothered to do
						elaborate debugging)
		
		Returns
		
		sentence		-	A string that starts with a capital, and ends
						with a full stop.
		"""
		
		# Raise an Exception when no data exists
		if self.data == {}:
			self._error(u'generate_text', u'No data is available yet. Did you read any data yet?')
		
		# Sometimes, for mysterious reasons, a word duo does not appear as a
		# key in the database. This results in a KeyError, which is highly
		# annoying. Because I couldn't quite find the bug that causes this
		# after a whopping five minutes of looking for it, I decided to go
		# with the lazy approach of using a try and except statements. Sorry.
		error = True
		attempts = 0
		
		# Make a single keyword into a list of them
		if type(seedword) in [str,unicode]:
			seedword = [seedword]

		# Run until a proper sentence is produced
		while error:
			
			try:
				# Get all word duos in the database
				keys = self.data.keys()
				# Shuffle the word duos, so that not the same is
				# found every time
				random.shuffle(keys)
				
				# Choose a random seed to fall back on when seedword does
				# not occur in the keys, or if seedword==None
				seed = random.randint(0, len(keys))
				w1, w2 = keys[seed]
				
				# Try to find a word duo that contains the seed word
				if seedword != None:
					# Loop through all potential seed words
					while len(seedword) > 0:
						# Loop through all keys (these are (w1,w2)
						# tuples of words that occurred together in the
						# text used to generate the database
						for i in xrange(len(keys)):
							# If the seedword is only one word, check
							# if it is part of the key (a word duo)
							# If the seedword is a combination of words,
							# check if they are the same as the key
							if seedword[0] in keys[i] or \
								(tuple(seedword[0].split(u' ')) == \
								keys[i]):
								# Choose the words
								w1, w2 = keys[i]
								# Get rid of the seedwords
								seedword = []
								break
						# Get rid of the first keyword, if it was not
						# found in the word duos
						if len(seedword) > 0:
							seedword.pop(0)
				
				# Empty list to contain the generated words
				words = []
				
				# Loop to get as many words as requested
				for i in xrange(length):
					# Add the current first word
					words.append(w1)
					# Generare a new first and second word, based on the
					# database. Each key is a (w1,w2 tuple that points to
					# a list of words that can follow the (w1, w2) word
					# combination in the studied text. A random word from
					# this list is selected. Note: words can occur more
					# than once in this list, thus more likely word
					# combinations are more likely to be selected here.
					w1, w2 = w2, random.choice(self.data[(w1, w2)])
				
				# Add the final word to the generated words
				words.append(w2)
				
				# Capitalise the first word, capitalise all single 'i's,
				# and attempt to capitalise letters that occur after a
				# full stop.
				for i in xrange(0, len(words)):
					if (i == 0) or (u'.' in words[i-1]) or \
						(words[i] == u'i'):
						words[i] = words[i].capitalize()
				
				# Remove any wrong interpunction from the last word
				if words[-1][-1] in [u',', u';', u';']:
					words[-1] = words[-1][:-1]
				
				# Combine the words into one big sentence
				sentence = u' '.join(words)
					
				# Add a full stop to the end of the sentence
				if sentence[-1] not in [u'.', u'!', u'?']:
					sentence += u'.'
				
				error = False
				
			# If the above code fails
			except:
				# Count one more failed attempt
				attempts += 1
				# Report the error to the console
				if verbose:
					self._message(u'generate_text', u"Ran into a bit of an error while generating text. Will make %d more attempts" % (maxtries-attempts))
				# If too many attempts were made, raise an error to stop
				# making any further attempts
				if attempts >= maxtries:
					self._error(u'generate_text', u"Made %d attempts to generate text, but all failed. " % (attempts))
		
		return sentence
	
	
	def pickle_data(self, filename):
		
		"""Stores a database dict in a pickle file
		
		Arguments
	
		filepath		-	A string that indicates the path of the new
						pickle file
		"""
	
		# Store the database in a pickle file
		with open(filename, u'wb') as f:
			pickle.dump(self.data, f)
		
	
	def read(self, filename, overwrite=False):
		
		"""Reads a text, and adds its stats to the internal data. Use the
		mode keyword to overwrite the existing data, or to add the new
		reading material to the existing data. NOTE: Only text files can be
		read! (This includes .txt files, but can also be .py or other script
		files if you want to be funny and create an auto-programmer.)
		
		Arguments
		
		filename		-	String that indicates the path to a .txt file
						that should be read by the bot.
		
		Keyword Arguments
		
		overwrite		-	Boolean that indicates whether the existing data
						should be overwritten (True) or not (False). The
						default value is False.
		"""
		
		# Clear the current data if required
		if overwrite:
			self.clear_data()
		
		# Check whether the file exists
		if not self._check_file(filename):
			self._error(u'read', u"File does not exist: '%s'" % (filename))
		
		# Read the words from the file as one big string
		with open(filename, u'r') as f:
			# Read the contents of the file
			contents = f.read()
		# Unicodify the contents
		contents = contents.decode(u'utf-8')
		
		# Split the words into a list
		words = contents.split()
		
		# Add the words and their likely following word to the database
		for w1, w2, w3 in self._triples(words):
			# Only use actual words and words with minimal interpunction
			if self._isalphapunct(w1) and self._isalphapunct(w2) and \
				self._isalphapunct(w3):
				# The key is a duo of words
				key = (w1, w2)
				# Check if the key is already part of the database dict
				if key in self.data:
					# If the key is already in the database dict,
					# add the third word to the list
					self.data[key].append(w3)
				else:
					# If the key is not in the database dict yet, first
					# make a new list for it, and then add the new word
					self.data[key] = [w3]
	
	
	def read_pickle_data(self, filename, overwrite=False):
		
		"""Reads a database dict form a pickle file
		
		Arguments
	
		filepath		-	A string that indicates the path of the new
						pickle file
		
		Keyword Arguments
		
		overwrite		-	Boolean that indicates whether the existing data
						should be overwritten (True) or not (False). The
						default value is False.
		"""
	
		# Check whether the file exists
		if not self._check_file(filename, allowedext=[u'.pickle', u'.dat']):
			self._error(u'read_pickle_data', \
				u"File does not exist: '%s'" % (filename))
		
		# Load a database from a pickle file
		with open(filename, u'rb') as f:
			data = pickle.load(f)
		
		# Store the data internally
		if overwrite:
			self.clear_data()
			self.data = copy.deepcopy(data)
		else:
			for key in data:
				# If the key is not in the existing dataset yet, add it,
				# then copy the loaded data into the existing data
				if key not in self.data.keys():
					self.data[key] = copy.deepcopy(data[key])
				# If the key is already in the existing data, add the
				# loaded data to the existing list
				else:
					self.data[key].extend(copy.deepcopy(data[key]))
		
		# Get rid of the loaded data
		del data
	
	
	def twitter_autoreply_start(self, targetstring, keywords=None,
			prefix=None, suffix=None, maxconvdepth=None):
		
		"""Starts the internal Thread that replies to all tweets that match
		the target string.
		
		For an explanation of the target string, see the Twitter dev site:
		https://dev.twitter.com/streaming/overview/request-parameters#track
		
		Arguments
		
		targetstring	-	String that the bot should look out for. For
						more specific information, see Twitter's
						developer website (URL mentioned above).
		
		Keyword Arguments
		
		keywords		-	A list of words that the bot should recognise in
						tweets that it finds through its targetstring.
						The bot will attempt to use the keywords it finds
						to start its reply with. If more than one
						keyword occurs in a tweet, the position of each
						word in the keywords list will determine its
						priority. I.e. if both keywords[0] and
						keywords[1] occur in a tweet, an attempt will be
						made to reply with keywords[0] first. If that
						does not exist in the database, the next keyword
						that was found in a tweet will be used (provided
						it occurs in the keywords list).

		prefix		-	A string that will be added at the start of each
						tweet (no ending space required). Pass None if
						you don't want a prefix. Default value is None.

		suffix		-	A string that will be added at the end of each
						tweet (no starting space required). Pass None if
						you don't want a suffix. Default value is None.
		
		maxconvdepth	-	Integer that determines the maximal depth of the
						conversations that this bot is allowed to reply
						to. This is useful if you want your bot to reply
						to specific the Twitter handles of specific
						people. If you are going to do this, please keep
						this value low to prevent the bot from becomming
						spammy. You can also set this keyword to None,
						which is appropriate if you ask the bot to reply
						to a very specific hashtag or your own Twitter
						handle (i.e. a situation in which the bot is
						sollicited to respond). Default value is None.
		"""
		
		# Raise an Exception if the twitter library wasn't imported
		if not IMPTWITTER:
			self._error(u'twitter_autoreply_start', \
				u"The 'twitter' library could not be imported. Check whether it is installed correctly.")
		
		# Update the autoreply parameters
		self._targetstring = targetstring
		self._keywords = keywords
		self._tweetprefix = prefix
		self._tweetsuffix = suffix
		self._maxconvdepth = maxconvdepth
		
		# Signal the _autoreply thread to continue
		self._autoreplying = True
	
	
	def twitter_autoreply_stop(self):
		
		"""Stops the Thread that replies to all tweets that match the target
		string.
		
		For an explanation of the target string, see the Twitter dev site:
		https://dev.twitter.com/streaming/overview/request-parameters#track
		
		Arguments
		
		targetstring	-	String that the bot should look out for. For
						more specific information, see Twitter's
						developer website (URL mentioned above).
		
		Keyword Arguments
		
		keywords		-	A list of words that the bot should recognise in
						tweets that it finds through its targetstring.
						The bot will attempt to use the keywords it finds
						to start its reply with. If more than one
						keyword occurs in a tweet, the position of each
						word in the keywords list will determine its
						priority. I.e. if both keywords[0] and
						keywords[1] occur in a tweet, an attempt will be
						made to reply with keywords[0] first. If that
						does not exist in the database, the next keyword
						that was found in a tweet will be used (provided
						it occurs in the keywords list).
		"""
		
		# Raise an Exception if the twitter library wasn't imported
		if not IMPTWITTER:
			self._error(u'twitter_autoreply_stop', \
				u"The 'twitter' library could not be imported. Check whether it is installed correctly.")
		
		# Update the autoreply parameters
		self._targetstring = None
		self._keywords = None
		self._tweetprefix = None
		self._tweetsuffix = None
		
		# Signal the _autoreply thread to continue
		self._autoreplying = False

	
	def twitter_login(self, cons_key, cons_secret, access_token, \
		access_token_secret):
		
		"""Logs in to Twitter, using the provided access keys. You can get
		these for your own Twitter account at apps.twitter.com
		
		Arguments

		cons_key		-	String of your Consumer Key (API Key)

		cons_secret	-	String of your Consumer Secret (API Secret)

		access_token	-	String of your Access Token

		access_token_secret
					-	String of your Access Token Secret
		"""
		
		# Raise an Exception if the twitter library wasn't imported
		if not IMPTWITTER:
			self._error(u'twitter_login', u"The 'twitter' library could not be imported. Check whether it is installed correctly.")
		
		# Log in to a Twitter account
		self._t = twitter.Twitter(auth=twitter.OAuth(access_token, \
			access_token_secret, cons_key, cons_secret))
		self._ts = twitter.TwitterStream(auth=twitter.OAuth(access_token, \
			access_token_secret, cons_key, cons_secret))
		self._loggedin = True
		
		# Get the bot's own user credentials
		self._credentials = self._t.account.verify_credentials()
	
	
	def twitter_tweeting_start(self, days=1, hours=0, minutes=0, jitter=0, \
		keywords=None, prefix=None, suffix=None):
		
		"""Periodically posts a new tweet with generated text. You can
		specify the interval between tweets in days, hours, or minutes, or
		by using a combination of all. (Not setting anything will result in
		the default value of a 1 day interval.) You can also add optional
		jitter, which makes your bot a bit less predictable.
		
		Keyword arguments
		
		days			-	Numeric value (int or float) that indicates the
						amount of days between each tweet.
		
		hours		-	Numeric value (int or float) that indicates the
						amount of hours between each tweet.
		
		minutes		-	Numeric value (int or float) that indicates the
						amount of minutes between each tweet.
		
		jitter		-	Integer or float that indicates the jitter (in
						minutes!) that is applied to your tweet. The
						jitter is uniform, and on both ends of the delay
						value. For example, a jitter of 30 minutes on a
						tweet interval of 12 hours, will result inactual
						intervals between 11.5 and 12.5 hours.

		prefix		-	A string that will be added at the start of each
						tweet (no ending space required). Pass None if
						you don't want a prefix. Default value is None.

		suffix		-	A string that will be added at the end of each
						tweet (no starting space required). Pass None if
						you don't want a suffix. Default value is None.

		keywords		-	A list of words from which one is randomly
						selected and used to attempt to start a tweet
						with. If None is passed, the bot will free-style.
		"""
		
		# Raise an Exception if the twitter library wasn't imported
		if not IMPTWITTER:
			self._error(u'twitter_tweeting_start', \
				u"The 'twitter' library could not be imported. Check whether it is installed correctly.")
		
		# Clean up the values
		if not(days > 0) or (days == None):
			days = 0
		if not(hours > 0) or (hours == None):
			hours = 0
		if not(minutes > 0) or (minutes == None):
			minutes = 0
		# Calculate the tweet interval in minutes
		tweetinterval = (days*24*60) + (hours*60) + minutes
		# If the tweetinterval wasn't set, default to 1 day
		# (Thats 24 hours * 60 minutes per hour = 1440 minutes)
		if tweetinterval == 0:
			tweetinterval = 1440
		
		# Update the autotweeting parameters
		self._tweetinginterval = tweetinterval
		self._tweetingjitter = jitter
		self._tweetingkeywords = keywords
		self._tweetingprefix = prefix
		self._tweetingsuffix = suffix
		
		# Signal the _autotweet thread to continue
		self._autotweeting = True
	
	
	def twitter_tweeting_stop(self):
		
		"""Stops the periodical posting of tweets with generated text.
		"""
		
		# Raise an Exception if the twitter library wasn't imported
		if not IMPTWITTER:
			self._error(u'twitter_tweeting_stop', \
				u"The 'twitter' library could not be imported. Check whether it is installed correctly.")

		# Update the autotweeting parameters
		self._tweetinginterval = None
		self._tweetingjitter = None
		self._tweetingkeywords = None
		self._tweetingprefix = None
		self._tweetingsuffix = None
		
		# Signal the _autotweet thread to continue
		self._autotweeting = False

	
	def _autoreply(self):
		
		"""Continuously monitors Twitter Stream and replies when a tweet
		appears that matches self._targetstring. It will include
		self._tweetprefix and self._tweetsuffix in the tweets, provided they
		are not None.
		"""
		
		# Run indefinitively
		while self._autoreplythreadlives:

			# Wait a bit before rechecking whether autoreplying should be
			# started. It's highly unlikely the bot will miss something if
			# it is a second late, and checking continuously is a waste of
			# resource.
			time.sleep(1)

			# Only start when the bot logs in to twitter, and when a
			# target string is available
			if self._loggedin and self._targetstring != None:
	
				# Acquire the TwitterStream lock
				self._tslock.acquire(True)
	
				# Create a new iterator from the TwitterStream
				iterator = self._ts.statuses.filter(track=self._targetstring)
				
				# Release the TwitterStream lock
				self._tslock.release()
	
				# Only check for tweets when autoreplying
				while self._autoreplying:
					
					# Get a new Tweet (this will block until a new tweet
					# becomes available)
					tweet = iterator.next()
					
					# Store a copy of the latest incoming tweet, for
					# debugging purposes
					self._lasttweetin = copy.deepcopy(tweet)
					
					# Only proceed if autoreplying is still required (there
					# can be a delay before the iterator produces a new, and
					# by that time autoreplying might already be stopped)
					if not self._autoreplying:
						# Skip one cycle, which will likely also make the
						# the while self._autoreplying loop stop
						continue

					# Report to console
					self._message(u'_autoreply', u"I've found a new tweet!")
					try:
						self._message(u'_autoreply', u'%s (@%s): %s' % \
							(tweet[u'user'][u'name'], \
							tweet[u'user'][u'screen_name'], tweet[u'text']))
					except:
						self._message(u'_autoreply', \
							u'Failed to report on new Tweet :(')
					
					# Don't reply to this bot's own tweets
					if tweet[u'user'][u'id_str'] == self._credentials[u'id_str']:
						# Skip one cycle, which will bring us to the
						# next tweet
						self._message(u'_autoreply', \
							u"This tweet was my own, so I won't reply!")
						continue
					
					# Don't reply to retweets
					if u'retweeted_status' in tweet.keys():
						# Skip one cycle, which will bring us to the
						# next tweet
						self._message(u'_autoreply', \
							u"This was a retweet, so I won't reply!")
						continue

					# Don't reply to tweets that are in the nono-list
					if tweet[u'id_str'] in self._nonotweets:
						# Skip one cycle, which will bring us to the
						# next tweet
						self._message(u'_autoreply', \
							u"This tweet was in the nono-list, so I won't reply!")
						continue

					# Skip tweets that are too deep into a conversation
					if self._maxconvdepth != None:
						# Get the ID of the tweet that the current tweet
						# was a reply to
						orid = tweet[u'in_reply_to_status_id_str']
						# Keep digging through the tweets until the the
						# top-level tweet is found, or until we pass the
						# maximum conversation depth
						counter = 0
						while orid != None and orid not in self._nonotweets:
							# If the current in-reply-to-ID is not None,
							# the current tweet was a reply. Increase
							# the reply counter by one.
							ortweet = self._t.statuses.show(id=orid)
							orid = ortweet[u'in_reply_to_status_id_str']
							counter += 1
							# Stop counting when the current value
							# exceeds the maximum allowed depth
							if counter >= self._maxconvdepth:
								# Add the current tweets ID to the list
								# of tweets that this bot should not
								# reply to. (Keeping track prevents
								# excessive use of the Twitter API by
								# continuously asking for the
								# in-reply-to-ID of tweets)
								self._nonotweets.append(orid)
						# Don't reply if this tweet is a reply in a tweet
						# conversation of more than self._maxconvdepth tweets,
						# or if the tweet's ID is in this bot's list of
						# tweets that it shouldn't reply to
						if counter >= self._maxconvdepth or \
							orid in self._nonotweets:
							self._message(u'_autoreply', \
								u"This tweet is part of a conversation, and I don't reply to conversations with over %d tweets." % (self._maxconvdepth))
							continue
	
					# Separate the words in the tweet
					tw = tweet[u'text'].split()
					# Clean up the words in the tweet
					for i in range(len(tw)):
						# Remove clutter
						tw[i] = tw[i].replace(u'@',u''). \
							replace(u'#',u'').replace(u'.',u''). \
							replace(u',',u'').replace(u';',u''). \
							replace(u':',u'').replace(u'!',u''). \
							replace(u'?',u'').replace(u"'",u'')

					# Make a list of potential seed words in the tweet
					seedword = []
					if self._keywords != None:
						for kw in self._keywords:
							# Check if the keyword is in the list of
							# words from the tweet
							if kw in tw:
								seedword.append(kw)
					# If there are no potential seeds in the tweet, None
					# will lead to a random word being chosen
					if len(seedword) == 0:
						seedword = None
					# Report back on the chosen keyword
					self._message(u'_autoreply', u"I found seedwords: '%s'." % (seedword))

					# Construct a prefix for this tweet, which should
					# include the handle ('@example') of the sender
					if self._tweetprefix == None:
						prefix = u'@%s' % (tweet[u'user'][u'screen_name'])
					else:
						prefix = u'@%s %s' % (tweet[u'user'][u'screen_name'], \
							self._tweetprefix)

					# Construct a new tweet
					response = self._construct_tweet(seedword=None, \
						prefix=prefix, suffix=self._tweetsuffix)

					# Acquire the twitter lock
					self._tlock.acquire(True)
					# Reply to the incoming tweet
					try:
						# Post a new tweet
						resp = self._t.statuses.update(status=response,
							in_reply_to_status_id=tweet[u'id_str'],
							in_reply_to_user_id=tweet[u'user'][u'id_str'],
							in_reply_to_screen_name=tweet[u'user'][u'screen_name']
							)
						# Report to the console
						self._message(u'_autoreply', u'Posted reply: %s' % (response))
						# Store a copy of the latest outgoing tweet, for
						# debugging purposes
						self._lasttweetout = copy.deepcopy(resp)
					except:
						try:
							self._error(u'_autoreply', u"Failed to post a reply: '%s'" % (sys.last_value))
						except:
							self._error(u'_autoreply', u"Failed to post a reply: '%s'" % (u'unknown error'))
					# Release the twitter lock
					self._tlock.release()
	
	
	def _autotweet(self):
		
		"""Automatically tweets on a periodical basis.
		"""

		# Run indefinitively
		while self._tweetingthreadlives:

			# Wait a bit before rechecking whether tweeting should be
			# started. It's highly unlikely the bot will miss something if
			# it is a second late, and checking continuously is a waste of
			# resources.
			time.sleep(1)

			# Only start when the bot logs in to twitter, and when tweeting
			# is supposed to happen
			while self._loggedin and self._autotweeting:
				
				# Choose a random keyword
				if self._tweetingkeywords != None:
					if type(self._tweetingkeywords) in \
						[str, unicode]:
						kw = self._tweetingkeywords
					else:
						kw = random.choice(self._tweetingkeywords)

				# Construct a new tweet
				newtweet = self._construct_tweet(seedword=kw, \
					prefix=self._tweetingprefix, \
					suffix=self._tweetingsuffix)

				# Acquire the twitter lock
				self._tlock.acquire(True)
				# Reply to the incoming tweet
				try:
					# Post a new tweet
					tweet = self._t.statuses.update(status=newtweet)
					# Report to the console
					self._message(u'_autotweet', \
						u'Posted tweet: %s' % (newtweet))
					# Store a copy of the latest outgoing tweet, for
					# debugging purposes
					self._lasttweetout = copy.deepcopy(tweet)
				except:
					try:
						self._error(u'_autotweet', u"Failed to post a reply: '%s'" % (sys.last_value))
					except:
						self._error(u'_autotweet', u"Failed to post a reply: '%s'" % (u'unknown error'))
				# Release the twitter lock
				self._tlock.release()
				
				# Determine the next tweeting interval in minutes
				jitter = random.randint(-self._tweetingjitter, \
					self._tweetingjitter)
				interval = self._tweetinginterval + jitter
				
				# Sleep for the interval (in seconds, hence * 60)
				self._message(u'_autotweet', \
					u'Next tweet in %d minutes.' % (interval))
				time.sleep(interval*60)


	def _check_file(self, filename, allowedext=None):
		
		"""Checks whether a file exists, and has a certain extension.
		
		Arguments
		
		filename		-	String that indicates the path to a .txt file
						that should be read by the bot.
		
		Keyword Arguments
		
		allowedext	-	List of allowed extensions, or None to allow all
						extensions. Default value is None.
		
		Returns
		
		ok			-	Boolean that indicates whether the file exists,
						andhas an allowed extension (True), or does not
						(False)
		"""
		
		# Check whether the file exists
		ok = os.path.isfile(filename)
		
		# Check whether the extension is allowed
		if allowedext != None:
			name, ext = os.path.splitext(filename)
			if ext not in allowedext:
				ok = False
		
		return ok
	
	
	def _construct_tweet(self, seedword=None, prefix=None, suffix=None):
		
		"""Constructs a text for a tweet, based on the current Markov chain.
		The text will be of a length of 140 characters or less, and will
		contain a maximum of 20 words (excluding the prefix and suffix)
		
		Keyword Arguments
		
		seedword		-	A string that indicates what word should be in
						the sentence. If None is passed, or if the word
						is not in the database, a random word will be
						chosen. This value can also be a list of words,
						in which case the list will be processed
						one-by-one until a word is found that is in the
						database. Default value is None.
		
		prefix		-	A string that will be added at the start of each
						tweet (no ending space required). Pass None if
						you don't want a prefix. Default value is None.

		suffix		-	A string that will be added at the end of each
						tweet (no starting space required). Pass None if
						you don't want a suffix. Default value is None.
		
		Returns
		
		tweet		-	A string with a maximum length of 140 characters.
		"""

		sl = 20
		response = u''
		while response == u'' or len(response) > 140:
			# Generate some random response text
			response = self.generate_text(sl, seedword=seedword,
				verbose=False, maxtries=100)
			# Add the prefix
			if prefix != None:
				response = u'%s %s' % (prefix, response)
			# Add the suffix
			if suffix != None:
				response = u'%s %s' % (response, suffix)
			# Reduce the amount of words if the response is too long
			if len(response) > 140:
				sl -= 1
		
		return response
	
	
	def _error(self, methodname, msg):
		
		"""Raises an Exception on behalf of the method involved.
		
		Arguments
		
		methodname	-	String indicating the name of the method that is
						throwing the error.
		
		message		-	String with the error message.
		"""
		
		raise Exception(u"ERROR in Markovbot.%s: %s" % (methodname, msg))


	def _isalphapunct(self, string):
		
		"""Returns True if all characters in the passed string are
		alphabetic or interpunction, and there is at least one character in
		the string.
		
		Allowed interpunction is . , ; : ' " ! ?
		
		Arguments
		
		string	-		String that needs to be checked.
		
		Returns
		
		ok			-	Boolean that indicates whether the string
						contains only letters and allowed interpunction
						(True) or not (False).
		"""
		
		if string.replace(u'.',u'').replace(u',',u'').replace(u';',u''). \
			replace(u':',u'').replace(u'!',u'').replace(u'?',u''). \
			replace(u"'",u'').isalpha():
			return True
		else:
			return False
	
	
	def _message(self, methodname, msg):
		
		"""Prints a message on behalf of the method involved. Friendly
		verion of self._error
		
		Arguments
		
		methodname	-	String indicating the name of the method that is
						throwing the error.
		
		message		-	String with the error message.
		"""
		
		print(u"MSG from Markovbot.%s: %s" % (methodname, msg))


	def _triples(self, words):
	
		"""Generate triplets from the word list
		This is inspired by Shabda Raaj's blog on Markov text generation:
		http://agiliq.com/blog/2009/06/generating-pseudo-random-text-with-markov-chains-u/
		
		Moves over the words, and returns three consecutive words at a time.
		On each call, the function moves one word to the right. For example,
		"What a lovely day" would result in (What, a, lovely) on the first
		call, and in (a, lovely, day) on the next call.
		
		Arguments
		
		words		-	List of strings.
		
		Yields
		
		(w1, w2, w3)	-	Tuple of three consecutive words
		"""
		
		# We can only do this trick if there are more than three words left
		if len(words) < 3:
			return
		
		for i in range(len(words) - 2):
			yield (words[i], words[i+1], words[i+2])
		
