const request = require("request");
const async = require("async");
const winston = require('winston');
const querystring = require('querystring');
const { createLogger, format, transports } = require('winston');
const { splat, combine, timestamp, label, printf, simple } = format;

const URL = 'http://localhost:5000/influencers/v1/twitter/detect?';
const MAX_NUM_TWEETS = 20;
const NUM_TOP = 3

const logger = createLogger({
  level: 'debug',
  format: combine(
	label({ label: 'CUSTOM', message: true }),
	//timestamp(),
    simple()
  ),
  transports: [
    new winston.transports.Console(),
    new winston.transports.File({ filename: './logs/logfile.log' })
  ]
});


module.exports = {

	/**
	 * Checks if user exists in the system
	 * @param  {string}   email    email of the user to check
	 * @return {object}            json containing a flag if user with email given exists or not
	 */
	searchInfluencer: (req, res, next) => {
	  logger.debug("Check if query sent is correct: '" + req.body.query + "'");
	  async.waterfall([

			/**
			 * Check keywords from form
			 * @return {string}        access token to reset password
			 */
		    function(done) {
		      var searchTerm = req.body.query;
		      done(null, searchTerm);
		    },

		    /**
		     * Request to API in Python
		     * @param  {string}   token access token to reset password
		     * @return {string}         access token to reset password and the content of user current session to reset password
		     */
		    function(searchTerm, done) {
		    	var queryObject  = querystring.stringify({ 
		    		q:searchTerm, 
		    		count_tweets:MAX_NUM_TWEETS 
		    	});

		    	logger.debug("Requesting data for influencers...");
				logger.debug("Host: " + URL);
		    	logger.debug("Params: " + queryObject );
		    	logger.debug("URL: " + URL + queryObject);

				request(URL + queryObject, function(err, response, body) {
		            if (err){ 
		            	logger.error("Error while doing the request...");
		            	logger.error(err);
		                done(null, null);
		            }

		            //you probably have to extend the current item in the array with the response object
		            var result = JSON.parse(body);

					logger.debug("Successfull request");

		            //each item you send via the callback will be pushed into the result of async.map
		            done(null, result);
			    });
		    },

		  ], function(err, result) {
		    if (err) 
		    	return next(err);
		    if (result){
		    	var data = Array.from(new Set(result.influencers));
		    	return res.render('result', { influencers: data,
		    								  influencersTop: data.slice(0, NUM_TOP),
		    								  influencersOther:  data.slice(NUM_TOP, data.length) });
		    } else {
		    	return res.redirect('/')
		    }
		    
		  });
	}
}