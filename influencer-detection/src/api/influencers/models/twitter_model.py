#!flask/bin/python

# Copyright 2020 Luis Blazquez Miñambres (@luisblazquezm), Miguel Cabezas Puerto (@MiguelCabezasPuerto), Óscar Sánchez Juanes (@oscarsanchezj) and Francisco Pinto-Santos (@gandalfran)
# See LICENSE for details.

import tweepy
import requests
import re
import json
import datetime
import logging
import time

from influencers import config
from tweepy import OAuthHandler
from typing import List, Dict, Any

"""logging.basicConfig(format='%(asctime)s %(filename)s, line %(lineno)s - %(name)s.%(funcName)s() - '
                           '%(levelname)s - %(message)s ', level=logging.DEBUG)"""

logging.basicConfig(format='%(asctime)s %(filename)s, %(funcName)s() - '
                           '%(message)s ', level=logging.DEBUG)


class TwitterExtraction:

    def __init__(self):

        # Debug logger
        self._logger = logging.getLogger(self.__class__.__name__)

        # Create OAuthHandler object
        auth = tweepy.OAuthHandler(config.CONSUMER_KEY, config.CONSUMER_SECRET)
        
        # Set access token and secret
        auth.set_access_token(config.ACCESS_TOKEN , config.ACCESS_SECRET)
        
        # Create tweepy API object to fetch tweets
        self._api = tweepy.API(auth)


    def get_tweets_single_query(self, 
                                query: str, 
                                count: int = config.DEFAULT_NUM_TWEETS_EXTRACTED,
                                lang: str = config.DEFAULT_TWEETS_LANGUAGE,
                                start_date: str = (datetime.datetime.now() - datetime.timedelta(days=365)).strftime('%Y-%m-%d'),
                                end_date: str = datetime.date.today().strftime('%Y-%m-%d')) -> List[Dict]:
        """Retrieve tweets containing a keyword given in a query
        
        Arguments:
            query (:obj:`str`): keyword to find in tweets
        
        Keyword Arguments:
            count (:obj:`int`, optional): number of tweets to retrieve (default: {DEFAULT_NUM_TWEETS_EXTRACTED})
            lang (:obj:`str`, optional): language ot the tweets (default: {DEFAULT_TWEETS_LANGUAGE})
            start_date (:obj:`str`, optional): beginning date point to retrieve tweets (default: {datetime.date.today().strftime('%Y-%m-%d')})
            end_date (:obj:`str`, optional): end date point to retrieve tweets (default: {datetime.date.today().strftime('%Y-%m-%d')})
        
        Returns:
            :obj:`list` of :obj:`dict`: list of dictionaries containing information about the tweets retrieved
        """

        # Empty list to store parsed tweets
        tweets = []
       
        # Call twitter api to fetch tweets
        q = str(query)

        try:
            # src: https://stackoverflow.com/questions/42384305/tweepy-cursor-multiple-or-logic-function-for-query-terms
            # src: https://stackoverflow.com/questions/53161459/how-to-get-the-full-text-of-a-tweet-using-tweepy            
            for status in tweepy.Cursor(self._api.search,
                                        q=q,
                                        until=end_date,
                                        #result_type='recent',
                                        include_entities=True,
                                        monitor_rate_limit=True, 
                                        wait_on_rate_limit=True,
                                        lang=lang,
                                        tweet_mode='extended').items(count):
                # Extract information
                tweet_object = {}
                tweet_object['text'] = self.__extract_text(status)
                tweet_object['url'] = self.__extract_url(status)
                tweet_object['date'] = self.__extract_date_of_creation(status)
                tweet_object['user'] = self.__extract_user(status)
                tweets.append(tweet_object)

        except tweepy.TweepError as e:
            # if tweepy encounters an error, time.sleep for fifteen minutes..this will
            # help against API bans.
            self._logger.error(f"Something happened extracting tweets: {e}")
            time.sleep(60 * 2)
            return tweets

        return tweets

    def get_tweets_multiple_query(self,
                                  query: List[str], 
                                  count: int = config.DEFAULT_NUM_TWEETS_EXTRACTED,
                                  lang: str = config.DEFAULT_TWEETS_LANGUAGE,
                                  start_date: str = (datetime.datetime.now() - datetime.timedelta(days=365)).strftime('%Y-%m-%d'),
                                  end_date: str = datetime.date.today().strftime('%Y-%m-%d'),
                                  include_both: bool = False) -> List[Dict]:
        """Retrieve tweets containing a keyword given in a query
        
        Arguments:
            query (:obj:`list` of :obj:`str`): list to find in tweets
        
        Keyword Arguments:
            count (:obj:`int`, optional): number of tweets to retrieve (default: {DEFAULT_NUM_TWEETS_EXTRACTED})
            lang (:obj:`str`, optional): language ot the tweets (default: {DEFAULT_TWEETS_LANGUAGE})
            start_date (:obj:`str`, optional): beginning date point to retrieve tweets (default: {datetime.date.today().strftime('%Y-%m-%d')})
            end_date (:obj:`str`, optional): end date point to retrieve tweets (default: {datetime.date.today().strftime('%Y-%m-%d')})
            include_both (:obj:`bool`, optional): flag indicating if the tweets to retrieve will only contain all the keywords in the query or not (default: {False})
        
        Returns:
            :obj:`list` of :obj:`dict`: list of dictionaries containing information about the tweets retrieved
        """
        multiple_query = ""
        separator = " OR "

        # Search only for tweets including all the keywords passed in query in the same tweet
        # Otherwise, it will search for tweets including any of the keywords in the query
        if include_both:
            separator = " AND "

        # Parse query list of terms into single string query
        for search_term in query:
            multiple_query = multiple_query + search_term + separator

        # Remove last 'OR'
        last_characters = - len(separator)
        multiple_query = multiple_query[:last_characters]

        return self.get_tweets_single_query(query = multiple_query,
                                            count = count,
                                            lang = lang,
                                            start_date = start_date,
                                            end_date = end_date)

    def get_tweets_with_bearer_token(self, 
                                     query: str, 
                                     count: int = config.DEFAULT_NUM_TWEETS_EXTRACTED,
                                     lang: str = config.DEFAULT_TWEETS_LANGUAGE,
                                     start_date: str = (datetime.datetime.now() - datetime.timedelta(days=365)).strftime('%Y-%m-%d'),
                                     end_date: str = datetime.date.today().strftime('%Y-%m-%d')) -> List[Dict]:
        """Retrieve tweets containing a keyword given in a query BUT using Bearer Token Auth from
        Twitter API to retrieve more tweets and more info
        
        Arguments:
            query (:obj:`str`): list to find in tweets
        
        Keyword Arguments:
            count (:obj:`int`, optional): number of tweets to retrieve (default: {DEFAULT_NUM_TWEETS_EXTRACTED})
            lang (:obj:`str`, optional): language ot the tweets (default: {DEFAULT_TWEETS_LANGUAGE})
            start_date (:obj:`str`, optional): beginning date point to retrieve tweets (default: {datetime.date.today().strftime('%Y-%m-%d')})
            end_date (:obj:`str`, optional): end date point to retrieve tweets (default: {datetime.date.today().strftime('%Y-%m-%d')})
        
        Returns:
            :obj:`list` of :obj:`dict`: list of dictionaries containing information about the tweets retrieved
        """
        tweets = []

        bearer_header = {
            'Accept-Encoding': 'gzip',
            'Authorization': 'Bearer {}'.format(config.BEARER_TOKEN),
            'oauth_consumer_key': config.CONSUMER_KEY 
        }

        # Send request with bearer token
        uri = config.SEARCH_TWEETS_URI + "?q=" + str(query) 
        uri = uri + "?count=" + str(count)
        uri = uri + "?lang=" + str(lang)
        uri = uri + "?until=" + str(end_date)
        uri = uri + "&result_type=popular"

        try:
            response = requests.get(uri, headers=bearer_header)
        except Exception as e:
            self._logger.error(f"Something happened extracting tweets with bearer token: {e}")
            time.sleep(60 * 5)
            return []

        # Extract information
        if response.status_code == requests.codes.ok:

            # Extract information
            for status in response.json()['statuses']:
                tweet_object = {}
                tweet_object['text'] = self.__extract_text(status)
                tweet_object['url'] = self.__extract_url(status)
                tweet_object['date'] = self.__extract_date_of_creation(status)
                tweets.append(tweet_object)
        else:
            self._logger.error(f"Something happened extracting tweets (Bearer Token): {e}")
            time.sleep(60 * 2)
            return tweets

        return tweets

    def get_tweets_multiple_with_bearer_token(self,
                                              query: list, 
                                              count: int = config.DEFAULT_NUM_TWEETS_EXTRACTED,
                                              lang: str = config.DEFAULT_TWEETS_LANGUAGE,
                                              start_date: str = (datetime.datetime.now() - datetime.timedelta(days=365)).strftime('%Y-%m-%d'),
                                              end_date: str = datetime.date.today().strftime('%Y-%m-%d'),
                                              include_both: bool = False) -> List[Dict]:
        """Retrieve tweets containing a keyword given in a query BUT using Bearer Token Auth from
        Twitter API to retrieve more tweets and more info
        
        Arguments:
            query (:obj:`list` of :obj:`str`): list to find in tweets
        
        Keyword Arguments:
            count (:obj:`int`, optional): number of tweets to retrieve (default: {DEFAULT_NUM_TWEETS_EXTRACTED})
            lang (:obj:`str`, optional): language ot the tweets (default: {DEFAULT_TWEETS_LANGUAGE})
            start_date (:obj:`str`, optional): beginning date point to retrieve tweets (default: {datetime.date.today().strftime('%Y-%m-%d')})
            end_date (:obj:`str`, optional): end date point to retrieve tweets (default: {datetime.date.today().strftime('%Y-%m-%d')})
            include_both (:obj:`bool`, optional): flag indicating if the tweets to retrieve will only contain all the keywords in the query or not (default: {False})
        
        Returns:
            :obj:`list` of :obj:`dict`: list of dictionaries containing information about the tweets retrieved
        """

        multiple_query = ""
        separator = " OR "

        # Search only for tweets including all the keywords passed in query in the same tweet
        # Otherwise, it will search for tweets including any of the keywords in the query
        if include_both:
            separator = " AND "

        # Parse query list of terms into single string query
        for search_term in query:
            multiple_query = multiple_query + search_term + separator

        # Remove last 'OR'
        last_characters = - len(separator)
        multiple_query = multiple_query[:last_characters]

        return self.get_tweets_with_bearer_token(q = multiple_query,
                                                 count = count,
                                                 lang = lang,
                                                 start_date = start_date,
                                                 end_date = end_date)


    def get_user_followers_single_query(self, 
                                        user_id: str, 
                                        count: int = config.DEFAULT_NUM_FOLLOWERS_EXTRACTED,
                                        lang: str = config.DEFAULT_TWEETS_LANGUAGE,
                                        start_date: str = (datetime.datetime.now() - datetime.timedelta(days=365)).strftime('%Y-%m-%d'),
                                        end_date: str = datetime.date.today().strftime('%Y-%m-%d')) -> List[Dict]:

        # Empty list to store parsed tweets
        followers = []

        time.sleep(20)

        try:
            # src: https://stackoverflow.com/questions/42384305/tweepy-cursor-multiple-or-logic-function-for-query-terms
            # src: https://stackoverflow.com/questions/53161459/how-to-get-the-full-text-of-a-tweet-using-tweepy            
            for user in tweepy.Cursor(self._api.followers, 
                                      user_id=user_id,
                                      count=config.NUM_FOLLOWERS_TO_EXTRACT_WITH_RATE_LIMIT).items(config.NUM_FOLLOWERS_TO_EXTRACT_WITH_RATE_LIMIT):

                # Extract information
                follower_object = {}
                follower_object['name'] = self.__extract_profile_name(user)
                follower_object['screen_name'] = self.__extract_profile_screen_name(user)
                follower_object['id_str'] = self.__extract_profile_id_str(user)
                follower_object['listed_count'] = self.__extract_profile_listed_count(user)
                follower_object['biography'] = self.__extract_profile_description(user)
                follower_object['description'] = self.__extract_profile_description(user)
                follower_object['num_tweets_published'] = self.__extract_profile_num_tweets_published(user)
                follower_object['verified'] = self.__extract_profile_verified(user)
                follower_object['num_followers'] = self.__extract_profile_num_followers(user)
                follower_object['num_followees'] = self.__extract_profile_num_followees(user)
                follower_object['date_of_creation'] = self.__extract_profile_date_of_creation(user)

                followers.append(follower_object)

        except tweepy.TweepError as e:
            # if tweepy encounters an error, time.sleep for fifteen minutes..this will
            # help against API bans.
            self._logger.error(f"Something happened extracting tweets: {e}")
            time.sleep(60 * 2)
            return followers

        return followers

        


    def get_user_timeline_tweets_single_query(self, 
                                              user_id : str, 
                                              count: int = config.DEFAULT_NUM_TIMELINE_TWEETS_EXTRACTED,
                                              lang: str = config.DEFAULT_TWEETS_LANGUAGE,
                                              start_date: str = (datetime.datetime.now() - datetime.timedelta(days=7)).strftime('%Y-%m-%d'),
                                              end_date: str = datetime.date.today().strftime('%Y-%m-%d'),
                                              include_retweets: bool = False) -> List[Dict]:
        """Retrieve tweets containing a keyword given in a query
        
        Arguments:
            query (:obj:`str`): keyword to find in tweets
        
        Keyword Arguments:
            count (:obj:`int`, optional): number of tweets to retrieve (default: {DEFAULT_NUM_TWEETS_EXTRACTED})
            lang (:obj:`str`, optional): language ot the tweets (default: {DEFAULT_TWEETS_LANGUAGE})
            start_date (:obj:`str`, optional): beginning date point to retrieve tweets (default: {datetime.date.today().strftime('%Y-%m-%d')})
            end_date (:obj:`str`, optional): end date point to retrieve tweets (default: {datetime.date.today().strftime('%Y-%m-%d')})
        
        Returns:
            :obj:`list` of :obj:`dict`: list of dictionaries containing information about the tweets retrieved
        """

        # Empty list to store parsed tweets
        tweets = []

        time.sleep(20)
    
        try:
            for status in tweepy.Cursor(self._api.user_timeline,
                                        include_rts=include_retweets,
                                        count=count, 
                                        trim_user=True,
                                        user_id=user_id ,
                                        tweet_mode="extended").items(count):
                # Extract information
                tweet_object = {}
                tweet_object['text'] = self.__extract_text(status)
                tweet_object['url'] = self.__extract_url(status)
                tweet_object['date'] = self.__extract_date_of_creation(status)
                tweet_object['retweet_count'] = self.__extract_num_rt(status)
                tweet_object['favorite_count'] = self.__extract_num_fav(status) 
                tweets.append(tweet_object)

        except tweepy.TweepError as e:
            # if tweepy encounters an error, time.sleep for fifteen minutes..this will
            # help against API bans.
            self._logger.error(f"Something happened extracting tweets from timeline: {e}")
            time.sleep(60 * 2)
            return tweets

        return tweets

    def get_user_timeline_tweets_multiple_query(self, 
                                                users: List[Dict], 
                                                count: int = config.DEFAULT_NUM_TWEETS_EXTRACTED,
                                                lang: str = config.DEFAULT_TWEETS_LANGUAGE,
                                                start_date: str = (datetime.datetime.now() - datetime.timedelta(days=365)).strftime('%Y-%m-%d'),
                                                end_date: str = datetime.date.today().strftime('%Y-%m-%d')) -> List[Dict]:

        return list(map(lambda user:self.get_user_timeline_tweets_single_query(self, 
                                                                               user_screen_name=user, 
                                                                               count=count,
                                                                               lang=lang,
                                                                               start_date=start_date,
                                                                               end_date=start_date), users))

    def __extract_text(self, obj: dict, clean_text: bool = False) -> str:
        """Extracts text from tweet object status
        
        Arguments:
            obj (:obj:`dict`): status with information about a tweet from Twitter API
        
        Keyword Arguments:
            clean_text (:obj:`bool`, optional): flag indicating if the text of the tweet must be processed or not (default: {False})
        
        Returns:
            :obj:`str`: text of the tweet
        """
        text = obj.full_text.encode('utf-8').decode('utf-8')
        if clean_text:
            text = re.sub("[^A-Za-z]", "", text) # Clean tweet
        return text

    def __extract_url(self, obj: dict) -> str:
        """Extracts text from tweet object status
        
        Arguments:
            obj (:obj:`dict`): status with information about a tweet from Twitter API
        
        Returns:
            :obj:`str`: url of the tweet
        """
        url = "https://twitter.com/twitter/statuses/" + str(obj.id)
        return url

    def __extract_date_of_creation(self, obj: dict) -> str:
        """Extracts date and time from tweet object status
        
        Arguments:
            obj (:obj:`dict`): status with information about a tweet from Twitter API
        
        Returns:
            :obj:`str`: tweet´s publishing date and time
        """
        return obj.created_at.strftime('%Y-%m-%dT%H:%M:%S')

    def __extract_num_rt(self, obj: dict) -> str:
        """Extracts date and time from tweet object status
        
        Arguments:
            obj (:obj:`dict`): status with information about a tweet from Twitter API
        
        Returns:
            :obj:`str`: tweet´s publishing date and time
        """
        return obj.retweet_count

    def __extract_num_fav(self, obj: dict) -> str:
        """Extracts date and time from tweet object status
        
        Arguments:
            obj (:obj:`dict`): status with information about a tweet from Twitter API
        
        Returns:
            :obj:`str`: tweet´s publishing date and time
        """
        return obj.favorite_count

    def __extract_user(self, obj: dict) -> dict:
        """Extracts country and city information from tweet object status
        
        Arguments:
            obj (:obj:`dict`): status with information about a tweet from Twitter API
        
        Returns:
            :obj:`str`: tweet´s location
        """
        new_obj = obj.user._json

        # Get image
        if (obj.user.profile_image_url):
            new_obj['profile_image_url'] = obj.user.profile_image_url
        elif (obj.user.profile_image_url_https):
            new_obj['profile_image_url'] = obj.user.profile_image_url_https
        else:
            new_obj['profile_image_url'] = config.DEFAULT_TWITTER_PROFILE_PICTURE

        return new_obj

    def __extract_profile_name(self, obj: dict) -> str:
        """
        
        Arguments:
            obj (:obj:`dict`): status with information about a tweet from Twitter API
        
        Returns:
            :obj:`str`: 
        """
        return obj.name

    def __extract_profile_id_str(self, obj: dict) -> str:
        """
        
        Arguments:
            obj (:obj:`dict`): status with information about a tweet from Twitter API
        
        Returns:
            :obj:`str`: 
        """
        return obj.id_str


    def __extract_profile_screen_name(self, obj: dict) -> str:
        """
        
        Arguments:
            obj (:obj:`dict`): status with information about a tweet from Twitter API
        
        Returns:
            :obj:`str`: 
        """
        return obj.screen_name

    def __extract_profile_description(self, obj: dict) -> str:
        """
        
        Arguments:
            obj (:obj:`dict`): status with information about a tweet from Twitter API
        
        Returns:
            :obj:`str`: 
        """
        return obj.description

    def __extract_profile_listed_count(self, obj: dict) -> int:
        """
        
        Arguments:
            obj (:obj:`dict`): status with information about a tweet from Twitter API
        
        Returns:
            :obj:`str`: 
        """
        return obj.listed_count

    def __extract_profile_num_tweets_published(self, obj: dict) -> int:
        """
        
        Arguments:
            obj (:obj:`dict`): status with information about a tweet from Twitter API
        
        Returns:
            :obj:`str`: 
        """
        return obj.statuses_count

    def __extract_profile_verified(self, obj: dict) -> bool:
        """
        
        Arguments:
            obj (:obj:`dict`): status with information about a tweet from Twitter API
        
        Returns:
            :obj:`str`: 
        """
        return obj.verified

    def __extract_profile_num_followers(self, obj: dict) -> str:
        """
        
        Arguments:
            obj (:obj:`dict`): status with information about a tweet from Twitter API
        
        Returns:
            :obj:`str`: 
        """
        return obj.followers_count

    def __extract_profile_num_followees(self, obj: dict) -> str:
        """
        
        Arguments:
            obj (:obj:`dict`): status with information about a tweet from Twitter API
        
        Returns:
            :obj:`str`: 
        """
        return obj.friends_count

    def __extract_profile_date_of_creation(self, obj: dict) -> str:
        """
        
        Arguments:
            obj (:obj:`dict`): status with information about a tweet from Twitter API
        
        Returns:
            :obj:`str`: 
        """
        return obj.created_at