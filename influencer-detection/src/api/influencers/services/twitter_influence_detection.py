#!flask/bin/python

# Copyright 2021 Luis Blazquez Miñambres (@luisblazquezm)
# See LICENSE for details.

import datetime
import string
import pandas as pd
import logging    

from influencers.models.twitter_model import TwitterExtraction
from influencers.models.sentiment_model import SentimentAnalyzer
from influencers.models.influence_detection_model import InfluenceDetector
from influencers import config

"""logging.basicConfig(format='%(asctime)s %(filename)s, line %(lineno)s - %(name)s.%(funcName)s() - '
                           '%(levelname)s - %(message)s ', level=logging.DEBUG)"""

logging.basicConfig(format='%(asctime)s %(filename)s, %(funcName)s() - '
                           '%(message)s ', level=logging.DEBUG)

class TwitterExtractionForInfluenceDetection:

    def __init__(self):

        # Debug logger
        self._logger = logging.getLogger(self.__class__.__name__)

    def extract(self, 
                query:str, 
                num_top_influencers:int=config.DEFAULT_NUM_TOP_INFLUENCERS, 
                count_tweets:int=config.DEFAULT_NUM_TWEETS_EXTRACTED, 
                lang:str=config.DEFAULT_TWEETS_LANGUAGE, 
                from_date:str=(datetime.datetime.now() - datetime.timedelta(days=365)).strftime('%Y-%m-%d'), 
                to_date:str=datetime.date.today().strftime('%Y-%m-%d')) -> dict:
        """
        Extracts news about a theme given, extracting the main topics of those news and getting tweets talking about that theme and each topic extracted
        to know the sentiment and opinion of the people on Twitter talking about those themes.

        Arguments:
            query (:obj:`str`): Keyword or theme to search news and tweets from.
            count_news (:obj:`int`, optional): Number of news to extract.
            count_tweets (:obj:`int`, optional): Number of tweets to extract.
            lang (:obj:`str`, optional): Language of the tweets and news to retrieve. The language must be ISO coded. For example, English code would be 'en'.
            from_date (:obj:`str`, optional): Date in ISO 8601 format (YYYY-mm-dd) where data retrieval time interval will start.
            to_date (:obj:`str`, optional): Date in ISO 8601 format (YYYY-mm-dd) where data retrieval time interval will stop.
            include_both (:obj:`bool`, optional): flag indicating if the tweets to retrieve will only contain all the keywords in the query or not (default: {False})

        Returns:
            :obj:`list` of :obj:`dict` formatted Twitter Sentiment and Topic Modelling data.

        Examples:
            >>> print(self.extract())
            [{'influencers': {
                    'user': ...
                    'profile_url': ...,
                    'influence': ...,
                    'main_media': ...,
                    'sentiment': ...,
                    'followers': ...
              }
            }, ...]

        Scheme:
            - tweets = get_tweets_with_keyword(k)
            - user_profiles = get_profiles_of_tweets(tweets)
            - influencers = extract_influencers(user_profiles)
            - timeline_tweets = get_timeline_tweets_of_influencers(influencers)
            - sentiment = get_sentiment_from_timeline_tweets(timeline_tweets)
            - result = influencers + sentiment

        """
        final_results = []

        if "," in query:
            query = self.parse_query(query=query, include_both=include_both)

        #### 1. Search tweets containing given keywords
        twitter_hdlr = TwitterExtraction()

        self._logger.debug(f"Extracting tweets for query '{query}'")
        list_tweets = twitter_hdlr.get_tweets_single_query(query=query, 
                                                           count=count_tweets,
                                                           lang=lang,
                                                           start_date = from_date,
                                                           end_date = to_date)

        self._logger.debug(f"The list of tweets retrieved is {len(list_tweets)}")

        #### 2. Get user profiles from tweets 
        list_user_profiles = []
        for tweet in list_tweets:
            list_user_profiles.append(tweet['user'])

        #### 3. Extract influencers from 
        influencer_detector_hdlr = InfluenceDetector()

        self._logger.debug(f"Influence detection for query '{query}'")
        users_df = pd.json_normalize(list_user_profiles)
        influencers_data = influencer_detector_hdlr.detect(twitter_hdlr=twitter_hdlr,
                                                           users_df=users_df,
                                                           num_influencers=num_top_influencers)

        self._logger.debug(f"Result of influence detection")
        self._logger.debug(influencers_data)

        #### 4. Get timeline tweets from user profile and sentiment analysis on text
        sentiment_hdlr = SentimentAnalyzer()
        influencer = {}
        list_timeline_user_tweets = sentiment_results = []
        for user in influencers_data:
            influencer = user
            sentiment_results = []

            # Extracts tweets from potential influencer timeline
            self._logger.debug(f"Extracting timeline tweets of user '{influencer['name']}'")
            list_timeline_user_tweets = twitter_hdlr.get_user_timeline_tweets_single_query(user_id =influencer['id'], 
                                                                                           lang=lang,
                                                                                           start_date = from_date,
                                                                                           end_date = to_date)

            self._logger.debug(f"The list of tweets retrieved in timeline for user '{influencer['name']}' is {len(list_timeline_user_tweets)}")

            # Analyze timeline tweets sentiment
            self._logger.debug(f"Analyzing sentiment from timeline tweets of user '{influencer['name']}'")
            sentiment_results = list(map(lambda tweet:sentiment_hdlr.analyze(tweet['text']), list_timeline_user_tweets))
            sentiment_values = [sentiment['sentiment'] for sentiment in sentiment_results]

            # Get average of sentiment in tweets
            #influencer['sentiment'] = sum(sentiment['sentiment'] for sentiment in sentiment_results) / len(sentiment_results)
            influencer['sentiment'] = max(set(sentiment_values), key = sentiment_values.count)
            self._logger.debug(f"Average of sentiment for user '{influencer['name']}' is '{influencer['sentiment']}'")

            # Append results
            final_results.append(influencer)

        # Encapsulate final results
        results = {
            'influencers': final_results
        }

        self._logger.debug(f"Final results")
        self._logger.debug(results)

        return results

    def parse_query(self, query:str, include_both:bool=True) -> str:
        """Parse query to URL encode format
        
        Arguments:
            query (:obj:`str`): Keyword or theme to search news and tweets from.
            include_both (:obj:`bool`, optional): flag indicating if the tweets to retrieve will only contain all the keywords in the query or not (default: {False})
        
        Returns:
            :obj:`str`: query parsed in format (k1 AND k2 AND ... AND kn)
        """
        multiple_query = ""
        separator = " OR "

        # Search only for tweets including all the keywords passed in query in the same tweet
        # Otherwise, it will search for tweets including any of the keywords in the query
        if include_both:
            separator = " AND "

        query_words_list = query.split(",") 

        # Parse query list of terms into single string query
        for search_term in query_words_list:
            multiple_query = multiple_query + search_term.strip() + separator

        # Remove last 'OR'
        last_characters = - len(separator)
        multiple_query = multiple_query[:last_characters]

        return multiple_query