/////////////////////// SERVICES

const path = require('path');
const express = require('express');
const app = express();
const server = require('http').Server(app);
const winston = require('winston');
const { createLogger, format, transports } = require('winston');
const bodyParser = require('body-parser');
const { splat, combine, timestamp, label, printf, simple } = format;

/////////////////////// CONSTANTS

const PORT = 5100;

/////////////////////// CONFIG

const logger = createLogger({
  level: 'debug',
  format: combine(
	label({ label: 'CUSTOM', message: true }),
	format.splat(),
	//timestamp(),
    simple()
  ),
  transports: [
    new winston.transports.Console(),
    new winston.transports.File({ filename: './logs/logfile.log' })
  ]
});

app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: false }));

// Set 'views' folder
app.engine('html',  require('ejs').renderFile);
app.set('views', path.join(__dirname + '/views'));
app.set('view engine', 'html');

app.use(express.static(__dirname + '/node_modules'));  
app.use('/', express.static(path.join(__dirname + '/')));

const search = require('./controllers/searchController');

//////////////////// ROUTES

app.post('/search', search.searchInfluencer);

//////////////////// SERVER APP LAUNCH

server.listen(PORT, function () {
  logger.debug('Express app started on port ' + PORT);
});
