#!flask/bin/python

# Copyright 2020 Luis Blazquez Miñambres (@luisblazquezm), Miguel Cabezas Puerto (@MiguelCabezasPuerto), Óscar Sánchez Juanes (@oscarsanchezj) and Francisco Pinto-Santos (@gandalfran)
# See LICENSE for details.

import tweepy
import requests
import re

from soa import config
from tweepy import OAuthHandler
import datetime
from typing import List, Dict, Any

class TwitterExtraction:

    def __init__(self):

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
        q=str(query)

        try:
            # src: https://stackoverflow.com/questions/42384305/tweepy-cursor-multiple-or-logic-function-for-query-terms
            # src: https://stackoverflow.com/questions/53161459/how-to-get-the-full-text-of-a-tweet-using-tweepy            
            for status in tweepy.Cursor(self._api.search,
                                        q=q,
                                        until=end_date,
                                        result_type='recent',
                                        include_entities=True,
                                        monitor_rate_limit=True, 
                                        wait_on_rate_limit=True,
                                        lang=lang,
                                        tweet_mode='extended').items(count):
                # Extract information
                tweet_object = {}
                tweet_object['text'] = self.extract_text(status)
                tweet_object['url'] = self.extract_url(status)
                tweet_object['date'] = self.extract_date_of_creation(status)
                tweet_object['geolocation'] = self.extract_geolocation(status)
                tweet_object['coordinates'] = self.extract_coordinates(status)
                tweets.append(tweet_object)

        except tweepy.TweepError as e:
            # if tweepy encounters an error, sleep for fifteen minutes..this will
            # help against API bans.
            print("Whoops! Something went wrong here. \
                    The error code is " + str(e))
            sleep(60 * 15)
            return []

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
            print("Whoops! Something went wrong here. \
                    The error code is " + str(e))
            return

        # Extract information
        if response.status_code == requests.codes.ok:

            # Extract information
            for status in response.json()['statuses']:
                tweet_object = {}
                tweet_object['text'] = self.extract_text(status)
                tweet_object['url'] = self.extract_url(status)
                tweet_object['date'] = self.extract_date_of_creation(status)
                tweet_object['geolocation'] = self.extract_geolocation(status)
                tweet_object['coordinates'] = self.extract_coordinates(status)
                tweets.append(tweet_object)
        else:
            print("Whoops! Something went wrong here. \
                    The error code is " + str(e))
            return

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

    def extract_text(self, obj: dict, clean_text: bool = False) -> str:
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

    def extract_url(self, obj: dict) -> str:
        """Extracts text from tweet object status
        
        Arguments:
            obj (:obj:`dict`): status with information about a tweet from Twitter API
        
        Returns:
            :obj:`str`: url of the tweet
        """
        url = "https://twitter.com/twitter/statuses/" + str(obj.id)
        return url

    def extract_date_of_creation(self, obj: dict) -> str:
        """Extracts date and time from tweet object status
        
        Arguments:
            obj (:obj:`dict`): status with information about a tweet from Twitter API
        
        Returns:
            :obj:`str`: tweet´s publishing date and time
        """
        return obj.created_at.strftime('%Y-%m-%dT%H:%M:%S')

    def extract_geolocation(self, obj: dict) -> str:
        """Extracts country and city information from tweet object status
        
        Arguments:
            obj (:obj:`dict`): status with information about a tweet from Twitter API
        
        Returns:
            :obj:`str`: tweet´s location
        """
        return obj.geo

    def extract_coordinates(self, obj: dict) -> str:
        """Extracts location coordinates from tweet object status
        
        Arguments:
            obj (:obj:`dict`): status with information about a tweet from Twitter API
        
        Returns:
            :obj:`str`: tweet´s coordinates in (lat - long) format
        """
        return obj.coordinates
