#!flask/bin/python

# Copyright 2021 Luis Blazquez Miñambres (@luisblazquezm)
# See LICENSE for details.

from flask_restx import reqparse

influencer_argument_parser = reqparse.RequestParser()

influencer_argument_parser.add_argument('q',
										location='args',
										type=str,
										required=True,
										default=None,
										help='The list of topics or themes to search tweets from. It must be a list of words separated by commas.')

influencer_argument_parser.add_argument('count_tweets',
										location='args',
										type=int,
										required=False,
										default=None,
										help='Numbers of tweets to retrieve.')

influencer_argument_parser.add_argument('lang',
										location='args',
										type=str,
										required=False,
										default=None,
										help="Language of the tweet to retrieve. The language must be ISO coded. For example, English code would be 'en'.")

influencer_argument_parser.add_argument('from_date',
										location='args',
										type=str,
										required=False,
										default=None,
										help='The start date to retrieve tweets from. The date must be in ISO 8601 format YYYY-mm-dd.')

influencer_argument_parser.add_argument('to_date',
										location='args',
										type=str,
										required=False,
										default=None,
										help='The end date to retrieve tweets from. The date must be in ISO 8601 format YYYY-mm-dd.')