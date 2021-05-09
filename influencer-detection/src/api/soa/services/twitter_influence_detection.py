#!flask/bin/python

# Copyright 2021 Luis Blazquez Miñambres (@luisblazquezm)
# See LICENSE for details.

import datetime
import string

from soa.models.twitter_model import TwitterExtraction
from soa.models.sentiment_model import SentimentAnalyzer
from soa import config

class TwitterExtractionForInfluenceDetection:

    def extract(self, 
                query:str, 
                count_news:int=config.DEFAULT_NUM_NEWS_EXTRACTED, 
                count_tweets:int=config.DEFAULT_NUM_TWEETS_EXTRACTED, 
                lang:str=config.DEFAULT_TWEETS_LANGUAGE, 
                from_date:str=(datetime.datetime.now() - datetime.timedelta(days=365)).strftime('%Y-%m-%d'), 
                to_date:str=datetime.date.today().strftime('%Y-%m-%d'),
                include_both:bool=True) -> dict:
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
            [{'news': ['This a news about covid-19'. '...', ...], 
              'topics': {
                    't1': {
                            'name': 'covid-19, health',
                            'tweets': [
                                {
                                    'url': 'https://www.twitter.com/statuses/...',
                                    'text': 'This is a tweet about covid-19 and health',
                                    'sentiment' 'neutral'
                                },
                                ...
                            ]
                    }
              }
            }, ...]
        """
        final_results = []

        if "," in query:
            query = self.parse_query(query=query, include_both=include_both)

        ## 1. Search tweets containing 'covid' keywords and topics extracted
        topic_results = {}
        twitter_hdlr = TwitterExtraction()
        sentiment_hdlr = SentimentAnalyzer()

        for topic in topics['topics']:

            twitter_search_query_list = [query, topic]

            # Extract from twitter api
            list_tweets = twitter_hdlr.get_tweets_multiple_query(query=twitter_search_query_list, 
                                                                 count=count_tweets,
                                                                 lang=lang,
                                                                 start_date = from_date,
                                                                 end_date = to_date,
                                                                 include_both=include_both)
            ## 4. Sentiment analysis on text
            twitter_results = []
            for tweet in list_tweets:
                twitter_results.append({'url': tweet['url'], 
                                        'text': tweet['text'], 
                                        'sentiment': sentiment_hdlr.analyze(tweet['text'])['sentiment']})

            topic_results[topic] = twitter_results

        """Influence results = {
                'user'
                'profile_url'
                'influence'
                'main_media'
                'sentiment'
        }
        """

        results = {
            'keywords': ,
            'influencers': influence_results
        }

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