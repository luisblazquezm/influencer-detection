#!flask/bin/python

# Copyright 2020 Luis Blazquez Miñambres (@luisblazquezm), Miguel Cabezas Puerto (@MiguelCabezasPuerto), Óscar Sánchez Juanes (@oscarsanchezj) and Francisco Pinto-Santos (@gandalfran)
# See LICENSE for details.


from flask_caching import Cache
from flask_limiter import Limiter	
from flask_limiter.util import get_remote_address


limiter = Limiter(	
	key_func=get_remote_address,	
	default_limits=["1000 per hour"]	
)

cache = Cache(
	config={
		'CACHE_TYPE': 'simple',
		'CACHE_DEFAULT_TIMEOUT': 60
	}
)