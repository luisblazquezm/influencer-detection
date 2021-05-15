#!flask/bin/python

# Copyright 2021 Luis Blazquez Miñambres (@luisblazquezm)
# See LICENSE for details.

from flask_restx import Api

api = Api(version='1.0',
		  title='Influencer Detection Project',
		  description="**PORBI Influencer Detection project's Flask RESTX API**")