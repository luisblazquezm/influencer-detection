#!flask/bin/python

# Copyright 2020 Luis Blazquez Miñambres (@luisblazquezm), Miguel Cabezas Puerto (@MiguelCabezasPuerto), Óscar Sánchez Juanes (@oscarsanchezj) and Francisco Pinto-Santos (@gandalfran)
# See LICENSE for details.

import datetime
from flask_restx import Resource
import json

from influencers import config
from influencers.run import api
from influencers.core import cache, limiter
from influencers.api.influencers_models import influencers_model
from influencers.api.influencers_parsers import influencer_argument_parser
from influencers.services.twitter_influence_detection import TwitterExtractionForInfluenceDetection
from influencers.utils import handle400error, handle404error, handle500error


influencer_ns = api.namespace('twitter', description='Identifies influencers in Twitter')


@influencer_ns.route('/detect')
class GetInfluence(Resource):

    @limiter.limit('1000/hour') 
    @cache.cached(timeout=84600, query_string=True)
    @api.expect(influencer_argument_parser)
    @api.response(404, 'Data not found')
    @api.response(500, 'Unhandled errors')
    @api.response(400, 'Invalid parameters')
    @api.marshal_with(influencers_model, code=200, description='OK', as_list=True)
    def get(self):
        """
        Extracts the latest news about coronavirus. Then performs a classification analysis with NLP to obtain the most mentioned topics in \
        relation with coronavirus. Then looks for tweets related with COVID and the obtained topics and performs a sentiment analysis. Finally \
        ensambes all information in a JSON that is served.
        """

        # Retrieve arguments
        try:
            args = influencer_argument_parser.parse_args()

            query = args['q']
            if query is None:
                return handle400error(influencer_ns, "The 'q' argument is required. Please, check the swagger documentation at /v1")

            count_tweets = args['count_tweets']
            if count_tweets is None:
                count_tweets = config.DEFAULT_NUM_TWEETS_EXTRACTED
            else:
                count_tweets = int(count_tweets)

            num_top_influencers = args['num_top_influencers']
            if num_top_influencers is None:
                num_top_influencers = config.DEFAULT_NUM_TOP_INFLUENCERS

            lang = args['lang']
            if lang is None:
                lang = config.DEFAULT_TWEETS_LANGUAGE

            from_date = args['from_date']
            if from_date is None:
                from_date = datetime.datetime.now().strftime('%Y-%m-%d')

            to_date = args['to_date']
            if to_date is None:
                to_date = datetime.datetime.now().strftime('%Y-%m-%d')

        except:
            return handle400error(influencer_ns, 'The provided arguments are not correct. Please, check the swagger documentation at /v1')

        # Check arguments
        
        if not query:
            return handle400error(influencer_ns, 'The provided query is empty')

        if count_tweets <= 0:
            return handle400error(influencer_ns, 'The provided number of tweets to extract is 0 or below 0.')

        if count_tweets <= 0:
            return handle400error(influencer_ns, 'The provided number of influencers to extract is 0 or below 0.')

        if len(lang) > 5: # 5 is the maximum length of a ISO language code
            return handle400error(influencer_ns, 'The provided language is not an ISO code')

        try:
            to_date_dt = datetime.datetime.strptime(to_date, '%Y-%m-%d')
        except:
            return handle400error(influencer_ns, 'The provided date in to_date argument is not properly formatted in ISO (YYYY-mm-dd).')

        try:
            from_date_dt = datetime.datetime.strptime(from_date, '%Y-%m-%d')
        except:
            return handle400error(influencer_ns, 'The provided date in from_date argument is not properly formatted in ISO (YYYY-mm-dd).')

        if from_date_dt > to_date_dt:
            return handle400error(influencer_ns, 'The date interval provided in from_date and to_date arguments is not consistent.')

        # retrieve covid cases
        results = []
        #try:
        extractor = TwitterExtractionForInfluenceDetection()
        results = extractor.extract(query=query, 
                                    count_tweets=count_tweets,
                                    num_top_influencers=num_top_influencers,
                                    lang=lang,
                                    from_date=from_date_dt,
                                    to_date=to_date_dt)
        #except Exception as e:
            #return handle500error(influencer_ns)

        # if there are no tweets found about the topic given, return 4040 error
        if not results:
            return handle404error(influencer_ns, 'No results were found for the given parameters.')

        return results
            
