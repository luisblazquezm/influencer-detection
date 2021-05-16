#!flask/bin/python

# Copyright 2020 Luis Blazquez Miñambres (@luisblazquezm)
# See LICENSE for details.


from flask_restx import fields
from influencers.run import api

feedback_model = api.model("Feedback Influencer information by date", {
    'rts': fields.String(example='20000000', description='Number of retweets in influencers´ tweets in one day.'),
    'favs': fields.String(example='20000000', description='Number of favs in influencers´ tweets in one day.'),
    'interaction': fields.String(example='0,98', description='Interaction of the followers with the influencer profile over 1.'),
    'date': fields.String(example='2020-11-30, 12:00:00', description='Date of the feedback retrieved.')
}, description='Feedback and support information of the influencer detected.')

influencer_data_model = api.model("Influencer information", {
    'id': fields.String(example='15078394', description='Id of the influencer on twitter.'),
    'name': fields.String(example='PewDiePie', description='Name of the influencer.'),
    'screen_name': fields.String(example='@pewdiepie', description='Name of the influencer on twitter.'),
    'followers': fields.String(example='100000000', description='Number of followers the influencer has on Twitter.'),
    'influence': fields.String(example='0.78', description='Influence of the user extracted over 1.'),
    'formatted_followers': fields.String(example='100M', description='Formatted number of followers'),
    'profile_img': fields.String(example='https://twitter.com/pewdiepie/photo', description='Image of the user profile in Twitter.'),
    'profile_url': fields.String(example='https://twitter.com/pewdiepie', description='Date of the publishing of the news'),
    'level_bots': fields.String(example='High', description='Level of bot followers of the influencer'),
    'role': fields.String(example='youtuber', description='Role of the user in social media'),
    'sentiment': fields.String(example='neutral', description='Average sentiment of the timeline tweets of influencer'),
    'feedback': fields.Nested(feedback_model, description='Influencers extracted', as_list=True)
}, description='Information of Influencer extracted from Twitter.')

influencers_model = api.model('Extraction information', {
	'influencers': fields.Nested(influencer_data_model, description='Influencers extracted', as_list=True)
}, description='Result of Twitter extraction for influencer detection')


