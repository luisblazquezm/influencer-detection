#!/usr/bin/env python
# coding: utf-8

"""
SocialBrand Analysis API

Welcome to the Analysis API for SocialBrand Project. The purpose of this API is to get the data extracted and collected in the ingesta part
(mainly formed by tweets) and analyze it in different ways to achieve the final results the user will contemplate in the projects´s interphace.

What it gets: BISITENode data structured splitted into various dataframes:*

> Profiles info

> Tweets info

> Followers info

> Followees info

What it returns: list of dictionaries with the following format:

         [
             {
                 id: graph_id1
                 data:[
                     ...
                 ]
             },
             {
                 id: graph_id2
                 data:[
                     ...
                 ]
             },
             ...
             {
                 id: graph_idn
                 data:[
                     ...
                 ]
             }
         ]

 *See Preprocessing for more INFO

Here are added the neccesary modules for this API´s
"""
import ingest_extraction as extraction
import flask
import joblib
import pickle
import numpy as np
import pandas as pd
import re
import nltk
import sys
import logging
import json
import requests

from flask_swagger_ui import get_swaggerui_blueprint
from datetime import datetime
from flask import Flask, request, jsonify
from datetime import datetime as dt
from collections import Counter
from nltk.stem import WordNetLemmatizer
from nltk.corpus import stopwords

sys.path.append("..")
from metrics.utils import Utils as PropertiesLoader  # In subfolder ../metrics
from abc import abstractmethod

nltk.download('stopwords')
nltk.download('punkt')

# Syntaxis and lemmatization constants
STOP_WORDS = set(stopwords.words('english'))
WORDNET_LEMMATIZER = WordNetLemmatizer()
nltk.download('wordnet')

############### CONSTANTS ###############

sentiment_predictions = None
CONFIG_MODELS_SECTION = "MACHINE_LEARNING_MODELS_PATHS"
CONFIG_IDS_SECTION = "ANALYSIS_IDS"
CONFIG_NAMES_SECTION = "ANALYSIS_NAMES"


################################################ ANALYSIS PARENT CLASS ################################################

class BISITEAnalysis:
    """
    This class allows to create subclasses to handle every specific algorithm or analysis for the graphs.
    The analysis instructions and results are returned in inherited subclasses of the current.

    Args:
        _graph_id (int): identifier of the graph´s analysis
        _name (str): name of the analysis

    Attributes:
        _logger (:obj:`Logger`): logging module handler for debugging and printing
        _graph_id (int): identifier of the graph´s analysis
        _name (str): name of the analysis
    """

    def __init__(self, _graph_id, _name):
        self._logger = logging.getLogger(self.__class__.__name__)
        self._graph_id = _graph_id  # ID of the graphic that requests the analysis
        self._name = _name  # Name of the analysis (used for the API_Handler class)

    def _get_name(self):
        """
        Returns the name or tag of the analysis applied.

        Returns:
            string: name of the analysis done in the subclass
        """
        return self._name

    def _get_graph_id(self):
        """
        Returns the id of the graph that will collect the result of the analysis.

        Return:
            string: id of the graph correspondent to the analysis done in the subclass
        """
        return self._graph_id

    def serialize(self, analysis_data):
        """
        Fills the final dictionary with the id to identify which graph will
        receive the data and the encapsulated data analyzed

        Args:
            analysis_data (:obj:`dict`): contains the data previously encapsulated and formatted

        Returns:
            :object:`dict`: contains the final result of the analysis in JSON format
        """
        _data = {
            'id': self._graph_id,
            'data': analysis_data
        }

        return _data

    @staticmethod
    def encapsulate_data(**kwargs):
        """
        Fills a dictionary variable with the data collected in every analysis
        in a flexible way (it does not depend on the number of arguments)

        Args:
            **kwargs (:obj:`dict`): contains the key and value of the data collected in the corrispondent analysis.
            For example: :obj.encapsulate_data(key1 = value1, key2 = value2, ..., keyn = valuen)


        Returns:
            :object:`dict`: contains the result of the analysis accomplished that the API will return in JSON format
        """
        _analysis_data = {}

        for key, value in kwargs.items():
            _analysis_data[key] = value

        return _analysis_data

    @abstractmethod
    def apply_algorithm(self, data):
        """
        Applies the correspondent analysis in the subclass inherited from this one
        THIS METHOD MUST BE OVERRIDED BY THE PROGRAMMER IN EVERY SUBCLASS WITH THE CORRESPONDENT ANALYSIS OR ALGORITHM
        """
        # In case, this method is called from an instance of parent class 'BISITEAnalysis'
        raise Exception("not overriden")


################################################ API CLASS ################################################

class AnalysisAPI:
    """
    This is the main class for analysis the rest of the subclasses will inherit to apply each one its own
    algorithm

    Note: 'graph_results' is the List of dictionaries with the following format our API
    returns:
     [
       {
        id: graph_id1
        data: ...
       },
       {
        id: graph_id2
        data: ...
       },
       ...
     ]

     And the key 'data' will contain the dictionary returned
     in the correspondent analysis
    """

    """############### CONSTANTS ###############"""
    __CONFIG_FILE_SECTION = "ANALYSIS_API"  # Section name of the .ini file where the parameters for Flask API are stored

    """############### GLOBAL VARIABLES ###############"""
    __graph_results = []  # Array where there will be stored the result of each analysis
    __df_dict = None  # Dictionary of dataframes created from the JSON file received from the ingesta API (More INFO in the introduction text of this file)
    __logger = None  # Handler instance of the logging module for printing and debugging
    _algorithms = {}  # Dictionary containing the algorithms that will be applied and whose results will be returned
    _resource_type = None  # Type of resource collected in the ingest request(tweets or profiles)

    """############### INITIALIZATION OF GLOBAL VARIABLES ###############"""
    __logger = logging.getLogger('AnalysisAPI')  # Initialization of the logging handler
    __IP = PropertiesLoader.get_from_ini(__CONFIG_FILE_SECTION, 'ip')  # Get the IP for the API from .ini file
    __PORT = int(
        PropertiesLoader.get_from_ini(__CONFIG_FILE_SECTION, 'port'))  # Get the port for the API from .ini file
    __api_hdlr = Flask(PropertiesLoader.get_from_ini(__CONFIG_FILE_SECTION,
                                                     'flask_api_name'))  # Get the name of the API from .ini file

    def __init__(self):
        AnalysisAPI.__logger.error("Initialization of API")
        swagger_blueprint = get_swaggerui_blueprint(
            '/doc',
            '/doc/swagger.json',
            config={
                'app_name': PropertiesLoader.get_from_ini(self.__CONFIG_FILE_SECTION, 'flask_api_name')
            }
        )
        self.__api_hdlr.register_blueprint(swagger_blueprint, url_prefix='/doc')
        self.__api_hdlr.run(host=self.__IP, port=self.__PORT)  #  Run the application

    @staticmethod
    @__api_hdlr.route('/doc/swagger.json', methods=['GET'])
    def read_swagger_doc():
        file = None
        data = None
        try:
            file = open('swagger.json', 'r')
            data = file.read()
        except:
            flask.abort(404)
        finally:
            file.close()
        return data

    @staticmethod
    @__api_hdlr.route("/analyze", methods=['POST'])
    def socialBrand_query():
        """
        Method that will serve as the entry point of the API

        Note: the JSON file that will receive the API can be given to changes. But
        , by default, it will have the following format:
                {
                    "data_to_analyze": [
                            ...
                    ]
                }

        'data_to_analyze' parameter will contain the tree of BISITENodes collected in the ingesta
        """

        raw_data = request.json  # Get the body of the POST message in JSON format
        AnalysisAPI.__logger.debug("POST captured")

        if request.method == 'POST':
            AnalysisAPI.__logger.debug("POST message received. Ready to desencapsulate")
            analysis_data_list = raw_data['data_to_analyze']  # Get BISITENodes structure

            # TODO: Uncomment this
            data_str = json.dumps(analysis_data_list)
            # data_str = analysis_data_list

            AnalysisAPI._create_dataframe(data_str)  # Gets dictionary of dataframes filled with data from POST received
            AnalysisAPI._instance_algs()  # Iterate over the algorithms that will be applied to initialize them. Depending on the data received (tweets or profiles)
            AnalysisAPI._handle_request_from_post()  # Apply the algorithms initialized on the data received on the post

            return AnalysisAPI._get_response_results()  #  Returns the data analyzed for each graph
        else:
            AnalysisAPI.__logger.error(f"request method received not a post: {request.method}")
            flask.abort(500)

    @staticmethod
    def _create_dataframe(__data):
        """
        Creates a dictionary of dataframes from the BISITENodes´ data extracted from the
        ingesta calling functions from 'ingest_extraction_v2' file

        Args:
            __data (:obj:`list` of :obj:`dict`): contains the list of dictionaries (BISITENodes structure)
                                                 that results from calling the Ingesta API
        """

        AnalysisAPI.__df_dict, AnalysisAPI._resource_type = extraction.extraction_from_disk(__data)

        """
        try:
            AnalysisAPI.__df_dict, AnalysisAPI._resource_type = extraction.extraction_from_disk(__data)
        except Exception as e:
            AnalysisAPI.__logger.error(f"extraction of BISITENode into dict of dataframes incompleted: {type(__data)}\n"
                                       "-------------------------------------------------------------\n"
                                       f"exception caught: {e}\n"
                                       f"content: {__data}\n")

            flask.abort(500)
        """
    @staticmethod
    def _instance_new_alg(algorithm):
        """
        Initializes a new algorithm (subclass) given , adding it to the dictionary of algorithms
        where the key is the name of the subclass/algorithm and the value is the instance of the subclass
        that applies the algorithm passed as a parameter.

        Args:
            algorithm (:obj:`BISITEAnalysis` inherited subclass): instance of the new subclass to be added to
                                                                  the dictionary of analysis
        """

        AnalysisAPI._algorithms[algorithm._get_name()] = algorithm

    @staticmethod
    def _instance_algs():
        """
        Initializes the analysis the API will make on the data.

        Note: the way to use this API is the following. If a new analysis wants to be applied, the way
        to do it is at it follows.

        First creating a subclass that inherites from 'BISITEAnalysis' parent class
        containing all the default methods to do any analysis possible. Inside 'apply_algorithm' method in
        the subclass, the correspondent analysis will be done. This method will return a serialized data with
        an specific format (described in the description of this class)

        Afterwards, the instance of this subclass will be added to the dictionary that collects the subclasses
        of the algorithms and analysis that will be applied. For example:

                class new_analysis1(BISITEAnalysis):
                    ....

                (Inside this method)
                ...
                    AnalysisAPI._instance_new_alg(algorithm = new_analysis1())
                ...

        *IMPORTANT*: for further reasons, if one or more of analysis don´t want to be applied,
        just comment the line where it instanced

        """

        if AnalysisAPI._resource_type == 'tweets':

            AnalysisAPI.__logger.info("starting analysis for search by keywords")

            for analysis in TweetsAnalysis.__subclasses__():
                AnalysisAPI._instance_new_alg(algorithm=analysis())

        else:

            AnalysisAPI.__logger.info("starting analysis for search by profiles")

            for analysis in ProfilesAnalysis.__subclasses__():
                AnalysisAPI._instance_new_alg(algorithm=analysis())

    @staticmethod
    def _append_to_result(data_result):
        """
        Adds the result from one of the analysis (format depends on the analysis given).

        Note: See /docs/"Graph Scheme" for more INFO
        """

        AnalysisAPI.__logger.debug(f"GRAPH RESULT: {data_result}")
        AnalysisAPI.__graph_results.append(data_result)

    @staticmethod
    def _handle_request_from_post():
        """
        Handles the data extracted and formatted in the dictionary of dataframes iterating over the
        previously initialized subclasses and applying their correspondent analysis on the data. And
        adding the results to the array of dictionaries the API will return
        """

        for key in AnalysisAPI._algorithms:
            analysis_result = AnalysisAPI._algorithms[key].apply_algorithm(AnalysisAPI.__df_dict)

            if not analysis_result['data']:
                AnalysisAPI.__logger.debug(f"data is void for {key} analysis")
                continue
            else:
                AnalysisAPI._append_to_result(analysis_result)

    @staticmethod
    def _get_response_results():
        """
        Returns the array of results returned in each of the analysis applied.

        Returns:
            :obj:`list` of :obj:`dict` : list of results for every graph in JSON format (see description of this class)
        """

        AnalysisAPI.__logger.debug("ANALYSIS FINISHED: results succesfully sent")
        return jsonify(AnalysisAPI.__graph_results)  # Important to jsonify() to return the


################################################ SOCIAL NETWORKS ################################################


class TwitterAnalysis(BISITEAnalysis):

    def __init__(self, _graph_id, _name):
        super(TwitterAnalysis, self).__init__(_graph_id=_graph_id,
                                              _name=_name)

    def apply_algorithm(self, data):
        raise Exception(
            "not overriden")  # In case, this method is called from an instance of parent class 'BISITEAnalysis'


class StandByAnalysis(BISITEAnalysis):
    """
    Analysis subclasses that are deprecated or in standby will inherite from this class
    """

    def __init__(self, _graph_id, _name):
        super(StandByAnalysis, self).__init__(_graph_id=_graph_id,
                                              _name=_name)

    def apply_algorithm(self, data):
        raise Exception(
            "not overriden")  # In case, this method is called from an instance of parent class 'BISITEAnalysis'


################################################ TWITTER OBJECTS ################################################


class TweetsAnalysis(TwitterAnalysis):

    def __init__(self, _graph_id, _name):
        super(TweetsAnalysis, self).__init__(_graph_id=_graph_id,
                                             _name=_name)

    @abstractmethod
    def apply_algorithm(data):
        raise Exception(
            "not overriden")  # In case, this method is called from an instance of parent class 'BISITEAnalysis'


class ProfilesAnalysis(TwitterAnalysis):

    def __init__(self, _graph_id, _name):
        super(ProfilesAnalysis, self).__init__(_graph_id=_graph_id,
                                               _name=_name)

    @abstractmethod
    def apply_algorithm(data):
        raise Exception(
            "not overriden")  # In case, this method is called from an instance of parent class 'BISITEAnalysis'


# Here are described the subclasses that inherit from 'BISITEAnalysis' class. These subclasses correspond to the analysis and algorithms made and prepared to do for the SocialBrand project, most of them orientated to analyze the interaction and sentiment, statistics, metrics or influence through social media data.

# Some of the analysis taken are listed here:
#
# > Statistics (Likes, Favorites, RTs, ...)
#
# > Frequency of terms in texts (tweets, comments, posts, ...)
#
# > Sentiment Analysis (people´s opinion)
#
# > Followers variation
#
# > Public and customer target
#
# > Influencers´ search
#
# > Scope of tweets and range of audience

# All the subclasses have a method 'apply_algorithm' where the individual analysis for each subclass will be given. On the other hand, it takes the same structure for all the subclasses. This structure is formed as it follows:
#
#
#         Args:
#             __df_dict: dictionary of dataframes. In this analysis the dataframe that will be used is containing
#                        the dataframe containing the profiles and the tweets
#                        from the profile of a brand --- df = df['tweets_profile'] & df['main_profiles']
#
#         Return:
#             dictionary: each one on its format. For more information on what returns each subclass, consult
#             /docs/Graphs Scheme file
#

# ### *Sentiment*

# In[5]:


class sentimentAnalysis(TwitterAnalysis):
    """
    This subclass is the one other subclass will inherit when their analysis is related
    to sentiment analysis as it gives by default the necessary methods to load the vectorizer
    and classifier needed to do the predictions on the data.

    Args:
        __classifier_path (str): path to the vectorizer for tokenizing the text
        __vectorizer_path (str): path to the classification model (Scikit-Learn or Tensorflow or Keras)
        _vectorizer (:obj:`sklearn.feature_extraction.text`): instance of the vectorizer used
        _classifier (:obj:`sklearn`): instance of scikit-learn classifier

    Attributes:
        name (str): name of the analysis
        vectorizer_path (str): path to the vectorizer for tokenizing the text
        classifier_path (str): path to the classification model (Scikit-Learn or Tensorflow or Keras)
        graph_id (int): identifier of the graph´s analysis
    """

    _sentiment_predictions_on_tweets = None

    def __init__(self, name, vectorizer_path, classifier_path, graph_id):
        self.__classifier_path = classifier_path
        self.__vectorizer_path = vectorizer_path
        self._vectorizer = None
        self._classifier = None
        super(sentimentAnalysis, self).__init__(_graph_id=graph_id,
                                                _name=name)

    def load_model(self):
        """
        Loads from pickle or joblib file the vectorizer and classifier
        used for classification and prediction of the texts given (sentiment, gender, ...)
        """

        try:
            self._vectorizer = joblib.load(self.__vectorizer_path)
        except Exception as e:
            self._logger.error(f"error loading prediction vectorizer\n"
                               "-------------------------------------------------------------\n"
                               f"exception caught: {e}\n")
            raise

        try:
            self._classifier = joblib.load(self.__classifier_path)
        except Exception as e:
            self._logger.error(f"error loading prediction classifier\n"
                               "-------------------------------------------------------------\n"
                               f"exception caught: {e}\n")
            raise

    @staticmethod
    def _target2sentiment(target):
        """
        Turns a target given (0, 1 or 2) into its correspondent sentiment (negative, neutral or positive)

        Args:
            target (int): the number of the target of the correspondent sentiment
        Return:
            string: sentiment given as string
        """

        return {
            0: 'Negative',
            1: 'Neutral',
            2: 'Positive'
        }[target]

    def apply_sentiment_to_tweets(self, __df_dict):

        # Get tweets rows from dataframe of tweets in dictionary of dataframes
        df_tweets = __df_dict['tweets']['tweets_data']

        # We get a subdataframe with only the data in column 'Text'
        df_attr = df_tweets[['Text']]

        # Load the classifier, the vectorizer or both if any of them is not loaded
        if self._classifier or self._vectorizer is None:
            self.load_model()

        # Preprocess the texts given (clean them)
        # 'clean_text' method is in ingest_extraction_v2 file
        text_list = [extraction.clean_text(d) for d in df_attr['Text']]

        # Vectorize the data before predicting it
        sentences = self._vectorizer.transform(text_list)

        # Predict with the vectorized data
        predicted = self._classifier.predict(sentences)
        sentimentAnalysis._sentiment_predictions_on_tweets = np.array(
            predicted)  # GLOBAL VARIABLE sentiment_predictions

    @abstractmethod
    def apply_algorithm(data):
        raise Exception(
            "not overriden")  # In case, this method is called from an instance of parent class 'BISITEAnalysis'


# ###  0. General Statistics

# In[6]:


class generalStats(ProfilesAnalysis):
    """
    This subclass collects basic information about one or more profiles such as:

        > The number of tweets
        > Average of number of tweets and favorites
        > Number of followers and followees (verified and not verified)
        > Number of photos and videos

    """

    def __init__(self):
        super(generalStats, self).__init__(
            _graph_id=int(PropertiesLoader.get_from_ini(CONFIG_IDS_SECTION, self.__class__.__name__)),
            _name=PropertiesLoader.get_from_ini(CONFIG_NAMES_SECTION, self.__class__.__name__))

    @staticmethod
    def get_sum_metrics(df1, df2, metric):
        """
        Returns the adding of the number of metrics given (rt, fav or other) in the tweets in dataframe df2 - ['tweets_profiles']
        of the profile´s account given in dataframe df1 - ['main_profiles'].

        Args:
            df1 (:obj:`pandas dataframe`): usually 'main_profiles' dataframe containing all the info about the profiles given in the ingesta (if given)
            df2 (:obj:`pandas dataframe`): usually 'tweets_profiles' dataframe containing all the info about the tweets collected in the ingesta
            metric (str): metric to make the adding to. Possibilities:
                          * 'Num_Favs'
                          * 'Num_RTs'

        Returns:
            int, int: on one hand returns the result of adding the metric given of the tweets collected
        """

        # VARIABLES
        sum_metric = 0

        df_of_metric = df1.loc[(df1['ID'] == df2[
            'ID']), metric]  #### IMPORTANT THIS 0 will be an index 'i' in a loop when comparing with the variation of other brands
        list_of_metric = df_of_metric.values.tolist()
        num_tweets_of_profile = len(list_of_metric)

        for num_metric in list_of_metric:
            if sum_metric == 2949:
                print("BIEEEN")
            sum_metric += num_metric

        return sum_metric, num_tweets_of_profile

    def apply_algorithm(self, __df_dict):


        # VARIABLES
        # TODO This is not [0]. Entry point account profiles dataframe (when the user searches by profiles URL)
        profile_df = __df_dict['profiles']['main_profiles'].iloc[0]
        stats_data = {}  # Dictionary where all the data will be stored
        result_list = []  # List containing the dictionaries in its correspondent format (see Graphs Scheme API in SocialBrandAnalysis/docs)
        df_tweets = None
        count_followers_verified = 0
        count_followees_verified = 0
        other_values_dict = {
            "bullet": {
                "Favs": "https://i.pinimg.com/originals/b7/0d/33/b70d3302fd43909bd45ecf394e1724bf.png",
                "RTs": "https://cdn0.iconfinder.com/data/icons/interface-editing-and-time-1/64/retweet-arrow-twitter-512.png",
                "Followers": "https://png.pngtree.com/svg/20170313/56361fc69e.png",
                "Following": "https://png.pngtree.com/svg/20161030/5635f8cb9e.png",
                "Tweets": "https://cdn4.iconfinder.com/data/icons/color-webshop/512/twitter_bird-512.png",
                "Media": "https://cdn2.iconfinder.com/data/icons/minimal-4/100/play-512.png"
            },
            "tip": {
                "Favs": "Media de favoritos/tweet",
                "RTs": "Media de retweets/tweet",
                "Following": "No verificados: ",
                "Followers": "No verificados: ",
                "Tweets": "Numero total de tweets publicados en la cuenta",
                "Media": "Numero de fotos y videos publicados"
            },
            "tip2": {
                "Following": "Verificados: ",
                "Followers": "Verificados: "
            }
        }

        # Get tweets rows from dataframe of tweets in dictionary of dataframes
        df_tweets = __df_dict['tweets']['tweets_data']

        # Get Number of Tweets
        stats_data['Tweets'] = profile_df[
            'Num_Tweets_Published']  #### IMPORTANT THIS 0 will be an index 'i' in a loop when comparing with the variation of other brands

        # Get Average of Favs per tweet
        sum_favs, num_tweets_of_profile_rt = self.get_sum_metrics(df_tweets, profile_df, 'Num_Favs')
        stats_data['Favs'] = sum_favs / num_tweets_of_profile_rt

        # Get Average of RTs per tweet
        sum_rts, num_tweets_of_profile_fav = self.get_sum_metrics(df_tweets, profile_df, 'Num_RTs')
        stats_data['RTs'] = sum_rts / num_tweets_of_profile_fav

        # If the favs and rts are collected from different number of tweets, there must be a problem there
        if num_tweets_of_profile_fav != num_tweets_of_profile_rt:
            self._logger.error("number of tweets collected for rts and favs is different")
            raise

        # Get Number of Followers
        stats_data['Followers'] = profile_df[
            'Num_Followers']  #### IMPORTANT THIS 0 will be an index 'i' in a loop when comparing with the variation of other brands

        # Get Number of Followers verified
        followers_verified_list = __df_dict['profiles']['followers_profiles'].loc[
            (__df_dict['profiles']['followers_profiles']['ID'] == profile_df['ID']), 'Is_Verified']
        count_followees_verified = np.sum(followers_verified_list)

        # Get Number of Followees
        stats_data['Following'] = profile_df[
            'Num_Followees']  #### IMPORTANT THIS 0 will be an index 'i' in a loop when comparing with the variation of other brands

        # Get Number of Followees verified
        followees_verified_list = __df_dict['profiles']['followees_profiles'].loc[
            (__df_dict['profiles']['followees_profiles']['ID'] == profile_df['ID']), 'Is_Verified']
        count_followees_verified = np.sum(followees_verified_list)

        # Get Average of Number of Multimedia (images and photos)
        stats_data['Media'] = 0  # IMPORTANT!!!!!!!!! This data is not collected yet in the ingesta

        # Store the results with its appropiate format
        for key in stats_data.keys():

            if key == 'Followers':
                result_list.append(self.encapsulate_data(name=key,
                                                         points=stats_data[key],
                                                         bullet = other_values_dict['bullet'][key],
                                                         num_verified=count_followers_verified,
                                                         tip = other_values_dict['tip'][key],
                                                         tip2 = other_values_dict['tip2'][key]))
            elif key == 'Following':
                result_list.append(self.encapsulate_data(name=key,
                                                         points=stats_data[key],
                                                         bullet = other_values_dict['bullet'][key],
                                                         num_verified=count_followees_verified,
                                                         tip = other_values_dict['tip'][key],
                                                         tip2 = other_values_dict['tip2'][key]))
            else:

                result_list.append(self.encapsulate_data(name=key,
                                                         points=stats_data[key],
                                                         bullet = other_values_dict['bullet'][key],
                                                         tip = other_values_dict['tip'][key]))

        return self.serialize(result_list)


####### 1. Most Frequent Terms


class mostFrequentTerms(sentimentAnalysis, TweetsAnalysis, ProfilesAnalysis):
    """
    This subclass analyzes and gets the most frequent terms among the tweets collected in the ingesta
    to get a view of the most repeated terms on these texts and take notice on what interests the most to the customers.
    """

    def __init__(self):
        super(mostFrequentTerms, self).__init__(
            graph_id=int(PropertiesLoader.get_from_ini(CONFIG_IDS_SECTION, self.__class__.__name__)),
            name=PropertiesLoader.get_from_ini(CONFIG_NAMES_SECTION, self.__class__.__name__),
            vectorizer_path=PropertiesLoader.get_from_ini(CONFIG_MODELS_SECTION, 'sentiment_vectorizer_path'),
            classifier_path=PropertiesLoader.get_from_ini(CONFIG_MODELS_SECTION, 'sentiment_classifier_path'))

    @staticmethod
    def _normalizer(text):
        """
        This function does nearly the same thing as 'preprocessing_text' function.
        But this one is only used for lemmatization uses, so it could be used just as an example
        to filter the number of words in our document (most positive, most negative, ocurrency, most used)

        Args:
            text (str): This is the non-preprocessed text
        Return:
            :obj:`list` of str: list of words containing only the lemma of those words
        """

        if text is 'NaN':
            return

        only_letters = re.sub("[^a-zA-Z]", " ", text)  # Removes numbers and other unnecessary characters (just text)
        tokens = nltk.word_tokenize(only_letters)[2:]  # Tokenize the text (returns a list of words from the given text)
        lower_case = [l.lower() for l in tokens]  # Turns the words into lower case to keep a general format

        # 'STOP_WORDS' can be found in 'Constants' as part of Syntaxis and lemmatization constants
        filtered_result = list(
            filter(lambda l: l not in STOP_WORDS, lower_case))  # Removes stopwords from the list of tokens
        lemmas = [WORDNET_LEMMATIZER.lemmatize(t) for t in filtered_result]  # Turns the word back to its lemma

        return lemmas

    @staticmethod
    def _get_hashtags(__df_dict):

        # keys = ['x', 'value']  # Don´t remove. Must be necessary later
        hashtag_list = []  # Temporal list containing the hashtags found on tweets

        df_tweets = __df_dict['tweets']['tweets_data']

        # Iterate through the rows of tweets´ dataframe to get the hashtags
        for row in df_tweets['Hashtags']:
            if row is None:
                continue

            hashtag_list.extend(row)

        # Calculate with collections.Counter, the number of ocurrences of every hashtag
        # Returns a list of dictionaries (key=hashtag, value=number of ocurrences)
        frec_words_hashtags = Counter(hashtag_list)

        return frec_words_hashtags

    def apply_algorithm(self, __df_dict):

        # Main variables
        grams_new_list = []
        result_list = []  # Final result array in its correspondent format (see Graphs Scheme API in /docs)
        sentiment_dict = {}
        num_limit_items = 15  # TODO - the limit number of words and hashtags to show can be changed
        j = 0

        # Get tweets rows from dataframe of tweets in dictionary of dataframes
        df_tweets = __df_dict['tweets']['tweets_data']

        # We get a subdataframe with only the data in column 'Text'
        df_attr = df_tweets[['Text']]  # Get the column of dataframe containing the text fo the tweets
        text_list = [extraction.clean_text(d) for d in df_attr['Text']]  # Preprocess and clean all the tweets
        grams_list = [self._normalizer(d) for d in
                      text_list]  # Contains the normalized and preprocessed grammatical words and lemmas

        if sentimentAnalysis._sentiment_predictions_on_tweets is None:
            self.apply_sentiment_to_tweets(__df_dict)

        # Gives you a one-dimensional NumPy array
        sentiment_predictions_labeled = [self._target2sentiment(d) for d in
                                         sentimentAnalysis._sentiment_predictions_on_tweets]

        # Link the results of the sentiment analysis applied to the sentences
        # With the words that appear on them
        # In other words, link the words and hashtags with the sentiment predicted on the sentence where they appear
        for gram_list in grams_list:
            gram_list.extend(df_tweets['Hashtags'][j])  # Add hashtags to the list of words to represent and apply sentiment analysis
            grams_new_list.extend(gram_list)
            for gram_item in gram_list:
                if gram_item not in stopwords.words('english') and len(gram_item) > 3:
                    sentiment_dict[gram_item] = sentiment_predictions_labeled[j]
                else:
                    grams_new_list.remove(gram_item)
            j += 1

        # Counts the number of ocurrences of the words in the whole list 'grams_new_list'
        # Returning a Counter object (a dictionary) as follows:
        #
        #   frec_words_grams = Counter({word1:num_ocurrences_1, word2:num_ocurrences_2, ... wordn:num_ocurrences_n})
        #
        frec_words_grams = Counter(grams_new_list)

        self._logger.debug(f"grammar gotten results is:\n"
                           f"{frec_words_grams}\n")

        words_and_hashtags_frec = frec_words_grams.most_common(num_limit_items)

        self._logger.debug(f"15 most repeated hashtags and words:\n"
                           f"{words_and_hashtags_frec}\n")

        # Store the results
        for tuple_data in words_and_hashtags_frec:
            result_list.append(self.encapsulate_data(x=tuple_data[0],
                                                     value=tuple_data[1],
                                                     category=sentiment_dict[tuple_data[0]]))

        return self.serialize(result_list)


# ### 2. Hashtags


class hashtagsVisualization(StandByAnalysis):
    """
    This subclass collects the hashtags of the tweets requested and counts
    the number of times they appear in the collection of tweets to create
    a wordcloud to get a notion of the kind of interaction between the customers and the brand or person of influence.
    """

    def __init__(self):
        super(hashtagsVisualization, self).__init__(
            _graph_id=int(PropertiesLoader.get_from_ini(CONFIG_IDS_SECTION, self.__class__.__name__)),
            _name=PropertiesLoader.get_from_ini(CONFIG_NAMES_SECTION, self.__class__.__name__))

    def apply_algorithm(self, __df_dict):

        # keys = ['x', 'value']  # Don´t remove. Must be necessary later
        hashtag_list = []  # Temporal list containing the hashtags found on tweets
        result_list = []  # Final result array in its correspondent format (see Graphs Scheme API in /docs)

        df_tweets = __df_dict['tweets']['tweets_data']

        # Iterate through the rows of tweets´ dataframe to get the hashtags
        for row in df_tweets['Hashtags']:
            if row is None:
                continue

            hashtag_list.extend(row)

        # Calculate with collections.Counter, the number of ocurrences of every hashtag
        # Returns a list of dictionaries (key=hashtag, value=number of ocurrences)
        frec_words_hashtags = Counter(hashtag_list)

        # Store the results with its appropiate format
        for key in frec_words_hashtags.keys():
            # result_list.append(dict(zip(keys, item))) # Don´t remove. Must be necessary later
            result_list.append(self.encapsulate_data(x=key,
                                                     value=frec_words_hashtags[key]))

        return self.serialize(result_list)


# ### 3. Sentiment Through Time


class sentimentText(sentimentAnalysis, TweetsAnalysis, ProfilesAnalysis):
    """
    This subclass predicts the sentiment of the tweets collected and categorizes them into
    Positive, Neutral and Negative sentiment to approach customer´s opinion in social network
    from the point of view of the artificial intelligence.
    """

    def __init__(self):
        super(sentimentText, self).__init__(
            graph_id=int(PropertiesLoader.get_from_ini(CONFIG_IDS_SECTION, self.__class__.__name__)),
            name=PropertiesLoader.get_from_ini(CONFIG_NAMES_SECTION, self.__class__.__name__),
            vectorizer_path=PropertiesLoader.get_from_ini(CONFIG_MODELS_SECTION, 'sentiment_vectorizer_path'),
            classifier_path=PropertiesLoader.get_from_ini(CONFIG_MODELS_SECTION, 'sentiment_classifier_path'))

    @staticmethod
    def percentage(part, whole):
        return 100 * float(part) / float(whole)

    @staticmethod
    def maximum(a, b, c):

        if (a >= b) and (a >= c):
            largest = a
            tag = "Positive"

        elif (b >= a) and (b >= c):
            largest = b
            tag = "Neutral"
        else:
            largest = c
            tag = "Negative"

        return largest, tag


    def get_range_sentiment(self, a, b, c):

        value1, tag1 = self.maximum(a, b, c)

        if value1 == a:
            value2, tag2 = self.maximum(0, b, c)
        elif value1 == b:
            value2, tag2 = self.maximum(a, 0, c)
        elif value1 == c:
            value2, tag2 = self.maximum(a, b, 0)


        self._logger.debug(f"Value1: {value1}\n"
                           f"Value2: {value2}\n"
                           f"Tag1: {tag1}\n"
                           f"Tag2: {tag2}\n")

        if tag1 is "Positivo" and tag2 is "Neutral":

            if value1 >= 70 and value2 <= 30:
                return 10, "Muy Positivo"
            elif value1 >= 60 and value2 <= 40:
                return 9, "Muy Positivo"
            elif value1 >= 50 and value2 <= 50:
                return 8, "Positivo"

        elif tag1 is "Positivo" and tag2 is "Negative":

            if value1 >= 70 and value2 <= 30:
                return 7, "Positivo"
            elif value1 >= 60 and value2 <= 40:
                return 6, "Neutral"
            elif value1 >= 50 and value2 <= 50:
                return 5, "Neutral"

        elif tag1 is "Neutral" and tag2 is "Positivo":

            if value1 >= 70 and value2 <= 30:
                return 5, "Neutral"
            elif value1 >= 60 and value2 <= 40:
                return 6, "Neutral"
            elif value1 >= 50 >= value2:
                return 7, "Positivo"

        elif tag1 is "Neutral" and tag2 is "Negative":

            if value1 >= 70 and value2 <= 30:
                return 5, "Neutral"
            elif value1 >= 60 and value2 <= 40:
                return 5, "Neutral"
            elif value1 >= 50 >= value2:
                return 4, "Negativo"

        elif tag1 is "Negative" and tag2 is "Neutral":

            if value1 >= 70 and value2 <= 30:
                return 1, "Muy Negativo"
            elif value1 >= 60 and value2 <= 40:
                return 2, "Muy Negativo"
            elif value1 >= 50 >= value2:
                return 5, "Neutral"

        elif tag1 is "Negative" and tag2 is "Positive":

            if value1 >= 70 and value2 <= 30:
                return 3, "Negativo"
            elif value1 >= 60 and value2 <= 40:
                return 4, "Negativo"
            elif value1 >= 50 >= value2:
                return 5, "Neutral"
        else:

            return 5, "Neutral"

    def apply_algorithm(self, __df_dict):

        # Main variables
        result_list = []  # Final result array
        neg_tag = 0
        neu_tag = 1
        pos_tag = 2

        # Load the classifier and the vectorizer if any of them is not load (path is passed in the initialization
        # of th instance)
        if self._classifier or self._vectorizer is None:
            self.load_model()


        df_tweets = __df_dict['tweets']['tweets_data']

        # Sort the rows by date
        df_tweets.sort_values(by='Created_At')
        df_tweets['Created_At'] = pd.to_datetime(df_tweets['Created_At'])
        dates = pd.to_datetime(df_tweets['Created_At'], format='%Y%m%d')
        new_dates = dates.apply(lambda x: x.strftime('%Y-%m-%d'))
        dates_list = new_dates.tolist()

        # Remove repeated elements turning the list into a set
        # And the set back into a list
        unique_dates_list = set(dates_list)
        dates_list = list(unique_dates_list)

        # We get a subdataframe with only the data in column 'Text'
        for date_item in dates_list:

            # Get list of tweets of each day
            list_of_tweets_in_date = df_tweets.loc[(df_tweets['Created_At'].astype(str).str.contains(date_item)), 'Text']

            self._logger.debug(f"tweets collected on DATE {date_item}:\n"
                               f"{list_of_tweets_in_date}\n")

            # Preprocess the texts given (clean them)
            # 'clean_text' method is in ingest_extraction_v2 file
            text_list = [extraction.clean_text(d) for d in list_of_tweets_in_date]

            # Vectorize the data before predicting it
            sentences = self._vectorizer.transform(text_list)

            # Predict with the vectorized data
            predicted = self._classifier.predict(sentences)
            pred = np.array(predicted)

            # Count the number of ocurrences of each sentiment
            count_negative = np.count_nonzero(pred == neg_tag)
            count_neutral = np.count_nonzero(pred == neu_tag)
            count_positive = np.count_nonzero(pred == pos_tag)
            total_count = len(pred)

            range_percentage_pos = self.percentage(count_positive, total_count)
            range_percentage_neu = self.percentage(count_neutral, total_count)
            range_percentage_neg = self.percentage(count_negative, total_count)

            self._logger.debug(f"Range Pos: {range_percentage_pos}\n"
                               f"Range Neu: {range_percentage_neu}\n"
                               f"Range Neg: {range_percentage_neg}\n"
                               f"Positive: {count_positive}\n"
                               f"Neutral: {count_neutral}\n"
                               f"Negative: {count_negative}\n"
                               f"Total count: {total_count}\n")

            range_value, tag = self.get_range_sentiment(range_percentage_pos, range_percentage_neu, range_percentage_neg)

            d = str(date_item)[:10]

            # Encapsulate the data into correspondent JSON format
            result_list.append(self.encapsulate_data(date=d,
                                                     positive=count_positive,
                                                     neutral=count_neutral,
                                                     negative=count_negative,
                                                     total_tweets=total_count,
                                                     range=range_value,
                                                     range_tag=tag))

        # Return the result serialized
        return self.serialize(result_list)


# ### 4. Sentiment Average


class sentimentAverage(sentimentAnalysis, TweetsAnalysis, ProfilesAnalysis):
    """
    This subclass predicts the average of the sentiment predicted from the tweets collected and categorized into
    Positive, Neutral and Negative . This will allow the user to have a more general view of the customers opinion
    on social networks.
    """

    def __init__(self):
        super(sentimentAverage, self).__init__(
            graph_id=int(PropertiesLoader.get_from_ini(CONFIG_IDS_SECTION, self.__class__.__name__)),
            name=PropertiesLoader.get_from_ini(CONFIG_NAMES_SECTION, self.__class__.__name__),
            vectorizer_path=PropertiesLoader.get_from_ini(CONFIG_MODELS_SECTION, 'sentiment_vectorizer_path'),
            classifier_path=PropertiesLoader.get_from_ini(CONFIG_MODELS_SECTION, 'sentiment_classifier_path'))

    def apply_algorithm(self, __df_dict):

        # Main variables
        sentiment_data = {}
        result_list = []
        neg_tag = 0
        neu_tag = 1
        pos_tag = 2

        df_tweets = __df_dict['tweets']['tweets_data']

        # We get a subdataframe with only the data in column 'Text'
        df_attr = df_tweets[['Text']]

        if sentimentAnalysis._sentiment_predictions_on_tweets is None:
            self.apply_sentiment_to_tweets(__df_dict)

        # Count the number of ocurrences of each sentiment
        sentiment_data['Positive'] = np.count_nonzero(
            sentimentAnalysis._sentiment_predictions_on_tweets == pos_tag)
        sentiment_data['Negative'] = np.count_nonzero(
            sentimentAnalysis._sentiment_predictions_on_tweets == neg_tag)
        sentiment_data['Neutral'] = np.count_nonzero(
            sentimentAnalysis._sentiment_predictions_on_tweets == neu_tag)

        # Encapsulate and store it in the appropiate format
        for key in sentiment_data.keys():
            result_list.append(self.encapsulate_data(sentiment_tag=key,
                                                     num_of_sentiment_tweets=sentiment_data[key]))

        # Return the result serialized
        return self.serialize(result_list)


# ### 5. Feedback


class feedback(TweetsAnalysis, ProfilesAnalysis):
    """
    This subclass calculates the support or feedback (this is the number of favorites and rts)
    from the amount of tweets collected and ordered day by day in relation to the theme they are talkin about.
    """

    def __init__(self):
        super(feedback, self).__init__(
            _graph_id=int(PropertiesLoader.get_from_ini(CONFIG_IDS_SECTION, self.__class__.__name__)),
            _name=PropertiesLoader.get_from_ini(CONFIG_NAMES_SECTION, self.__class__.__name__))

    def apply_algorithm(self, __df_dict):

        # VARIABLES
        count_rts = 0
        count_favs = 0
        result_list = []

        df_tweets = __df_dict['tweets']['tweets_data']

        # Sort the rows by date
        df_tweets.sort_values(by='Created_At')
        df_tweets['Created_At'] = pd.to_datetime(df_tweets['Created_At'])
        dates = pd.to_datetime(df_tweets['Created_At'], format='%Y%m%d')
        new_dates = dates.apply(lambda x: x.strftime('%Y-%m-%d'))
        dates_list = new_dates.tolist()

        # Removes repeated elements in list converting it into a set
        # And then back again into a list
        unique_dates_list = set(dates_list)
        dates_list = list(unique_dates_list)

        # We get a subdataframe with only the data in column 'Text'
        for date_item in dates_list:

            list_of_favs_in_date = df_tweets.loc[(df_tweets['Created_At'].astype(str).str.contains(date_item)), 'Num_Favs']
            list_of_rts_in_date = df_tweets.loc[(df_tweets['Created_At'].astype(str).str.contains(date_item)), 'Num_RTs']

            # Calculates all the favorites from the tweets published in the date given in 'date_item'
            if len(list_of_favs_in_date) > 0:
                for d in list_of_favs_in_date:
                    count_favs += d

            # Calculates all the retweets from the tweets published in the date given in 'date_item'
            if len(list_of_rts_in_date) > 0:
                for d in list_of_rts_in_date:
                    count_rts += d

            # Parse date from numpy.datetime64 to datetime
            d = str(date_item)[:10]

            self._logger.debug(f"Favs and RTs in day: {date_item}\n"
                               f"FAVS: {count_favs}\n"
                               f"RTS: {count_rts}\n")

            interaction_perc = ((count_favs + count_rts) / len(list_of_favs_in_date)) / 100

            # This happens because of the way the algorithm is stated.
            # There could be an overwhelmed quantity of favs and rts in comparison with
            # the number of tweets collected
            if interaction_perc > 100:
                interaction_perc = 100

            # Encapsulate
            result_list.append(self.encapsulate_data(date=d,
                                                     rts=count_rts,
                                                     favs=count_favs,
                                                     interaction=interaction_perc))

            # Reset these values again as the value is appended in every iteration (+=)
            count_rts = 0
            count_favs = 0

        # Return the result serialized
        return self.serialize(result_list)


# ### 6. Follower Variation


class followerVariation(StandByAnalysis):
    """
    This subclass returns the number of followers gained and lost every day, as well as the total number of followers
    gained in the actual month between two dates the user gives on the front.
    The purpose of this is to have a tracing of the evolution of the number of followers of one or more
    accounts and analyze the reasons of the variation in a specific period of time.
    """

    def __init__(self):
        super(followerVariation, self).__init__(
            _graph_id=int(PropertiesLoader.get_from_ini(CONFIG_IDS_SECTION, self.__class__.__name__)),
            _name=PropertiesLoader.get_from_ini(CONFIG_NAMES_SECTION, self.__class__.__name__))

    def apply_algorithm(self, __df_dict):
        # Sort the rows by date
        followers_today = __df_dict['profiles']['main_profiles']['Num_Followers'][
            0]  #### IMPORTANT THIS 0 will be an index 'i' in a loop when comparing with the variation of other brands

        # gain_count = -1  # Backend task
        # loss_count = -1  # Backend task

        analysis_data = self.encapsulate_data(gain_count=-1,
                                              loss_count=-1,
                                              date=dt.now().strftime('%Y-%m-%d'),
                                              # Another format for date %Y-%m-%d %H:%M:%S
                                              value=followers_today)

        # Return the result serialized
        return self.serialize(analysis_data)


# ### 7. General Interaction Location


class generalInteraction(StandByAnalysis):
    """
    """

    def __init__(self):
        super(generalInteraction, self).__init__(
            _graph_id=int(PropertiesLoader.get_from_ini(CONFIG_IDS_SECTION, self.__class__.__name__)),
            _name=PropertiesLoader.get_from_ini(CONFIG_NAMES_SECTION, self.__class__.__name__))

    def apply_algorithm(self, __df_dict):
        pass


# ### 8. Comments Interaction Location (Deprecated)


class commentsInteraction(StandByAnalysis):
    """
    """

    def __init__(self):
        super(commentsInteraction, self).__init__(
            _graph_id=int(PropertiesLoader.get_from_ini(CONFIG_IDS_SECTION, self.__class__.__name__)),
            _name=PropertiesLoader.get_from_ini(CONFIG_NAMES_SECTION, self.__class__.__name__))

    def apply_algorithm(self, __df_dict):
        pass


# ### 9.  Gender Statistics


class genderPrediction(StandByAnalysis):
    """
    This subclass predicts the genre of the public of a brand based on their profile´s biography/description
    using a model previously trained to resolve these tasks.
    """

    def __init__(self):
        super(genderPrediction, self).__init__(
            graph_id=int(PropertiesLoader.get_from_ini(CONFIG_IDS_SECTION, self.__class__.__name__)),
            name=PropertiesLoader.get_from_ini(CONFIG_NAMES_SECTION, self.__class__.__name__),
            vectorizer_path=PropertiesLoader.get_from_ini(CONFIG_MODELS_SECTION, 'gender_vectorizer_path'),
            classifier_path=PropertiesLoader.get_from_ini(CONFIG_MODELS_SECTION, 'gender_classifier_path'))

    @staticmethod
    def __preprocess_gender_data(vectorizer, text_list):

        # VARIABLES
        description_list = []

        for description in text_list:
            description = re.sub("[^a-zA-Z]", " ", description)
            description = description.lower()
            description = nltk.word_tokenize(description)
            # description = [ word for word in description if not word in set(stopwords.words("english"))]
            lemma = WordNetLemmatizer()
            description = [lemma.lemmatize(word) for word in description]
            description = " ".join(description)
            description_list.append(description)

        return vectorizer.fit_transform(description_list)

    def apply_algorithm(self, __df_dict):

        # VARIABLES
        genre_data = {}
        text_list = []
        analysis_data = {}

        # Tags
        male_tag = 0
        female_tag = 1

        # We get a subdataframe with only the data in column 'Text'
        df_attr = __df_dict['profiles']['followers_profiles'][['Biography']]

        if self._classifier or self._vectorizer is None:
            self.load_model()

        # Preprocess the texts given (clean them)
        # 'clean_text' method is in ingest_extraction_v2 file
        for index, row in df_attr['Biography'].iteritems():
            text_list.append(extraction.clean_text(row['text']))

        # Get total number of users
        number_users_total = len(text_list)

        # Remove user profiles without biography
        text_list = filter(None, text_list)  # fastest

        # Vectorize data
        sentences = self._vectorizer.transform(text_list)

        # Predict with the vectorized data
        predicted = self._classifier.predict(sentences)
        genre_predictions = np.array(predicted)  # GLOBAL VARIABLE sentiment_predictions

        # Count the number of ocurrences of each sentiment
        genre_data['Male'] = np.count_nonzero(genre_predictions == male_tag)
        genre_data['Female'] = np.count_nonzero(genre_predictions == female_tag)

        # Get number of users without biography
        number_users_with_bio = genre_data['Male'] + genre_data['Female']

        # Encapsulate and store it in the appropiate format
        # for key in sentiment_data.keys():
        analysis_data = self.encapsulate_data(male=genre_data['Male'],
                                              female=genre_data['Female'],
                                              undefined=(number_users_total - number_users_with_bio))

        # Return the result serialized
        return self.serialize(analysis_data)


# ### 10. Influencers


class influencerDetection(ProfilesAnalysis):
    """
    This subclass allows to detect influencers based on a series of parameters and metrics
    such as:
        > Location
        > Account Verification
        > Number of followers
        > Association with other brands
    """

    def __init__(self):
        super(influencerDetection, self).__init__(
            _graph_id=PropertiesLoader.get_from_ini(CONFIG_IDS_SECTION, self.__class__.__name__),
            _name=PropertiesLoader.get_from_ini(CONFIG_NAMES_SECTION, self.__class__.__name__))

    @staticmethod
    def get_tweets_by_id(_id, _df_dict):
        """
        Returns the dataframe with the posts belonging to the user indicated as parameter

        Args:
            _id (str): The ID of the profile whose information we want to obtain
            _df_dict (dict): The dataframe with the data

        Returns:
            :obj:`pandas.core.frame.DataFrame`: dataframe with the filter for followees applied
        """
        values = [_id]
        new_df = extraction.filter_by(_df_dict['tweets']['tweets_data'], 'ID', values)

        return new_df

    @staticmethod
    def get_followers_by_id(_id, _df_dict):
        """
        Returns the dataframe with the  followers of the user indicated as parameter

        Args:
            _id (str): The ID of the profile whose information we want to obtain
            _df_dict (:obj:`dict` of :obj:`pandas.core.frame.DataFrame`): The dataframe with the data

        Returns:
            :obj:`pandas.core.frame.DataFrame`: dataframe with the filter for followees applied
        """
        values = [_id]
        new_df = extraction.filter_by(_df_dict['profiles']['followers_profiles'], 'ID_Root', values)

        return new_df

    @staticmethod
    def get_followees_by_id(_id, _df_dict):
        """
        Returns the dataframe with the followees of the user indicated as parameter

        Args:
            _id (str): the ID of the profile whose information we want to obtain
            _df_dict (:obj:`dict` of :obj:`pandas.core.frame.DataFrame`): the dataframe with the data

        Returns:
            :obj:`pandas.core.frame.DataFrame`: dataframe with the filter for followees applied
        """
        values = [_id]
        new_df = extraction.filter_by(_df_dict['profiles']['followees_profiles'], 'ID_Root', values)

        return new_df

    ########################### STEP 1 ###########################

    def get_bot_percentage(self, _dataframe_followers, _profile):
        """
        This function receives a profile and a dataframe with the followers of the profile
        and returns an estimate of the percentage of bots.

        Args:
            _dataframe_followers (:obj:`pandas.core.frame.DataFrame`): The dataframe where the followers data is stored
            _profile (:obj:`pandas.core.frame.DataFrame`): the row of original dataframe containing the profile
                                                           we want to calculate the bot percentage

        Returns:
            int: percentage of bot presence in the followers of the profile given
        """

        num_bots = self.get_num_bots(_dataframe_followers)
        num_followers = self.get_num_followers(_profile)
        bot_percentage = (num_bots / num_followers) * 100

        return bot_percentage

    # https://www.kaggle.com/charvijain27/detecting-twitter-bot-data#training_data_2_csv_UTF.csv

    def get_num_bots(self, df):
        """
        Gets the features 'Num_Followers', 'Num_Followees', 'Listed_Count', 'Average_Favorite_Count', 'Num_Tweets_Published'and 'Is_Verified'
        to predict if the followers of an account in the dataframe are bots or not. And returns the number
        of bots detected in the prediction

        Note: to do the prediction is necessary to have the DecisionTreeClassification model made with

        Args:
            df (:obj:`pandas.core.frame.DataFrame`): original dataframe containing the follower´s profiles data --- df = df['followers_profile']
        Return:
            int: number of bots encountered among the followers of the profile given
        """
        # Important, this is the limit number of days of the creation of an account
        # If an account is predicted as a bot account but this account was created NUM_DAYS_LIMIT ago
        # then these account can not be considered a bot account, as it can be a real person´s account
        # that has recently created but the model´s variables prediction takes it as
        NUM_DAYS_LIMIT = 10

        # Get list of words appearing in screen names that could indicate those users are bots
        bag_of_words_bot = PropertiesLoader.get_from_ini("CONSTANTS", "bag_of_words_bot")

        # Getting features from
        df['screen_name_binary'] = df.Name.str.contains(bag_of_words_bot, case=False, na=False)
        df['name_binary'] = df.ID_Str.str.contains(bag_of_words_bot, case=False, na=False)
        df['description_binary'] = df.Description_Text.str.contains(bag_of_words_bot, case=False, na=False)
        df['status_binary'] = df.Biography.str.contains(bag_of_words_bot, case=False, na=False)

        # If the follower has more than 2000 listed_count items , it indicates possibly not a bot. Otherwise it could be.
        df['listed_count_binary'] = df['Listed_Count'].apply(lambda x: False if x > 2000 else True)
        features = ['screen_name_binary', 'name_binary', 'description_binary', 'status_binary', 'Is_Verified',
                    'Num_Followers', 'Num_Followees', 'Num_Tweets_Published', 'listed_count_binary']

        X_pred = df[features]

        filename = "../sentiment_analysis_saved_models/saved_models/en_model_sklearn_DecisionTree_88.pickle"

        self._logger.debug("calculating num of bots")
        clf = pickle.load(open(filename, "rb", -1))
        predicted = clf.predict(X_pred)
        pred = np.array(predicted)
        self._logger.debug(f"Before applying date of creation: {pred}\n")

        a = datetime.now()

        self._logger.debug(f"Date of Creation: {df['Date_Of_Creation']}")

        index_list = list(df.index)

        for i, obj in enumerate(df['Date_Of_Creation']):

            index_obj = index_list[i]

            self._logger.debug("Indice: ", index_obj)
            self._logger.debug("Objeto: ", df.iloc[i]['Date_Of_Creation'])

            b = datetime.strptime(str(df.iloc[i]['Date_Of_Creation']), '%Y-%m-%d %H:%M:%S')
            if (a - b).days < NUM_DAYS_LIMIT:
                pred[i] = 0

        self._logger.debug(f"AFTER applying date of creation: {pred}\n")

        # The number of bots in numpy array predicted are indicated with a 1. Otherwise with a 0
        num_bots = np.count_nonzero(pred == 1)

        self._logger.debug(f"Number of bots of {0}: {1}/{2}".format(df['ID'], num_bots, len(df.index)))

        return num_bots

    ########################### STEP 2 ###########################

    @staticmethod
    def is_verified(_profile):
        """
        Verifies if the profile is verified on Twitter or not

        Args:
            _profile (:obj:`pandas.core.frame.DataFrame`): The profile to analyze

        Returns:
            int: 100 if the profile is verified, 0 if it isn't
        """
        if _profile['Is_Verified']:
            return 100
        else:
            return 0

    ########################### STEP 3 ###########################

    @staticmethod
    def expand_url(_url):
        """
        Gets the complete url from shorten url

        Args:
            _url (str): the url to expand

        Returns:
            str: expanded complete url from shorten url given
        """

        try:
            r = requests.get(_url)
        except requests.exceptions.RequestException:
            return _url, None

        if r.status_code != 200:
            longurl = None
        else:
            longurl = r.url

        return longurl

    def has_other_social_network(self, _profile):
        """
        This function returns two variables.
        The first one is a score between 0 and 100 depending on the social networks that the user manages.
        The second is the role assigned to you based on the most important social network you use.

        **IMPORTANT: see '/docs/Deteccion de Influencers en las RRSS.doc' for more info

        Args:
            _profile (:obj:`pandas.core.frame.DataFrame`): the profile to analyze

        Returns:
            int: marketing and social score of the social network of the influencer
            str: role of the influencer on the social networks
        """
        main_url = _profile['Profile_URL']
        exp_main_url = self.expand_url(main_url)
        biography = _profile['Biography']
        biography_urls = biography['urls']

        rss_score = 0
        rol = 'Famoso'

        self._logger.debug(f"Expanded URL: {exp_main_url}",
                           f"Original ULR: {main_url}")

        # Marketing solution: if the user has a youtube channel url on the description of their account is barely possible
        # that it is considered a 'youtuber'. So the value of this person is higher
        # in the calculation of the influencer score
        if 'youtube.com/channel/' in exp_main_url:
            rss_score += 75
            rol = "Youtuber"

        # The same happens if their name appears in the link of the webpage of their account indicating that they could
        # be part of a company or big enterprise
        if _profile['ID'] in exp_main_url:
            rss_score += 40
            rol = "Empresario o corporación"

        # The same can be applied for instagrammers, or bloggers. They are very valued in the enterprising and
        # branding deals
        if biography_urls != -1:

            for other_url in biography_urls:
                if 'facebook.com' in other_url:
                    rss_score += 25
                    rol = 'Famoso'

                elif 'instagram.com' in other_url:
                    rss_score += 25
                    rol = 'Instagrammer'

                elif 'blogspot.com' in other_url or 'tumblr.com' in other_url:
                    rss_score += 25
                    rol = 'Blogger'

        return rss_score, rol

    ########################### STEP 4 ###########################

    @staticmethod
    def get_posts(_profile_tweets, _from, _to):
        """
        Extracts from the "_from" to the "_to" posts from the "_profile_tweets" provided as an argument.
        Example: get_posts("exampleuser", 4, 10) returns from the 4th newest post to the 10th newest post

        Args:
            _profile_tweets (:obj:`list` of str): the profile tweets we want to extract.
            _from (int): number of the first newest post.
            _to (int): number of the last newest post.

        Returns:
            :obj:`list` of str: list containing the tweets from index '_from' value to index '_to' value
        """

        if _from > _to:
            return -1

        if _from - 1 > len(_profile_tweets):
            new_from = 0
        else:
            new_from = _from - 1

        if _to - 1 > len(_profile_tweets):
            new_to = len(_profile_tweets) - 1
        else:
            new_to = _to - 1

        return _profile_tweets.reset_index(drop=True).loc[new_from:new_to]

    @staticmethod
    def get_sum_metrics(df1, df2, metric):
        """
        Returns the adding of the number of metrics given (rt, fav or other) in the tweets in dataframe df2 - ['tweets_profiles']
        of the profile´s account given in dataframe df1 - ['main_profiles'].

        Args:
            df1 (:obj:`pandas.core.frame.DataFrame`): usually 'main_profiles' dataframe containing all the info about the profiles given in the ingesta (if given)
            df2 (:obj:`pandas.core.frame.DataFrame`): usually 'tweets_profiles' dataframe containing all the info about the tweets collected in the ingesta
            metric (str): metric to make the adding to. Possibilities:
                          * 'Num_Favs'
                          * 'Num_RTs'

        Returns:
            int: the result of adding the metric given of the tweets collected
            int: the total number of tweets
        """

        sum_metric = 0
        df_of_metric = df1.loc[(df1['ID'] == df2[
            'ID']), metric]  #### IMPORTANT THIS 0 will be an index 'i' in a loop when comparing with the variation of other brands
        list_of_metric = df_of_metric.values.tolist()
        num_tweets_of_profile = len(list_of_metric)

        for num_metric in list_of_metric:
            sum_metric += num_metric

        return sum_metric, num_tweets_of_profile

    @staticmethod
    def get_num_followers(_profile):
        """
        Returns the number of followers a user has.

        Args:
            _profile: the profile we want to know the followers

        Returns:
            int: number of followers of the profile given
        """
        return _profile['Num_Followers']

    def get_engagement(self, _dataframe, _profile):
        """
        This method calculates the influencer engagement using the form:
            engagement = [average_likes_in_posts_4_to_10] / followers

        Args:
            _dataframe (:obj:`pandas.core.frame.DataFrame`) : the profile we want to calculate the engagement
            _profile (:obj:`pandas.core.frame.DataFrame`) : the dataframe where the info is stored

        Returns:
            int: engagement of the profile on Twitter and interaction with their followers
        """
        # post_list = self.get_posts(self.get_tweets_by_id(_profile['ID'], _dataframe), 4,10)
        # if str(type(post_list)) != "<class 'pandas.core.frame.DataFrame'>":
        #    return -1

        sum_favs, num_tweets_of_profile_rt = self.get_sum_metrics(_dataframe['tweets']['tweets_data'], _profile,
                                                                  'Num_Favs')

        average_favs = sum_favs / num_tweets_of_profile_rt
        self._logger.debug("Media Likes: " + str(average_favs))

        followers = self.get_num_followers(_profile)
        self._logger.debug("Seguidores: " + str(followers))

        engagement = (average_favs / followers) * 10000
        self._logger.debug("Engagement: " + str((average_favs / followers)))

        return engagement


    def get_score(self, _dataframe, _profile):
        """
        This method receives as argument the dataframe corresponding to a profile
        and calculates different metrics to assign it a score.

        Args:
            _dataframe (:obj:`pandas.core.frame.DataFrame`): The dataframe where the data is stored
            _profile (:obj:`pandas.core.frame.DataFrame`): The profile we want to get the score

        Returns:
            :obj:`dictionary`: structure containing all the information calculated and given of the influencer detected
        """
        w_bot = 0.20
        w_rrss = 0.20
        w_verified = 0.25
        w_engagement = 0.35
        tag_level_bots = "Bajo"

        # 1. (20 %) Calculate number of bots through function
        bot_percentage = self.get_bot_percentage(self.get_followers_by_id(_profile['ID'], _dataframe), _profile)

        if bot_percentage >= 40:
            tag_level_bots = "Alto"
            # return -1

        elif 20 < bot_percentage < 40:
            tag_level_bots = "Medio"

        elif bot_percentage <= 20:
            tag_level_bots = "Bajo"

        # 2. (25 %) Check if it is verified
        is_verified = self.is_verified(_profile)

        # 3. (20 %) Influence in other Social networks
        rss_score, rol = self.has_other_social_network(_profile)

        # 4. (35 %) Engagement in terms of interaction with the public
        engagement = self.get_engagement(_dataframe, _profile)

        # Calculate final score
        score = w_bot * bot_percentage + w_verified * is_verified + w_rrss * rss_score + w_engagement * engagement
        influencer = {'score': score,
                      'id': _profile['ID'],
                      'verified': is_verified,
                      'engagement': engagement,
                      'rol': rol,
                      'level_bots': tag_level_bots
                      }
        return influencer

    @staticmethod
    def human_format(num):
        magnitude = 0
        while abs(num) >= 1000:
            magnitude += 1
            num /= 1000.0
        # Add more suffixes if you need them
        return '%.2f%s' % (num, ['', 'K', 'M', 'G', 'T', 'P'][magnitude])

    def apply_algorithm(self, __df_dict):

        # VARIABLES
        results_list = []

        self._logger.debug("Going to iter and detect influencers")
        for index, row in __df_dict['profiles']['main_profiles'].iterrows():
            self._logger.debug()
            influencer = self.get_score(__df_dict, row)
            self._logger.debug("Profile: {0}, Score: {1}".format(row['ID'], influencer))
            self._logger.debug("------------------------------")

            twitter_url = "https://twitter.com/" + row['ID']

            results_list.append(self.encapsulate_data(name = row['ID'],
                                                      followers = row['Num_Followers'],
                                                      influence = influencer['score'],
                                                      formatted_followers = self.human_format(row['Num_Followers']),
                                                      href = row['Profile_Image_URL'],
                                                      twitter_account = twitter_url,
                                                      level_bots = influencer['level_bots'],
                                                      role = influencer['rol']))  #row['Profile_URL']

        # Sort the list of influencers detected from the highest influence value to the lowest (in descendent order)
        results_list = sorted(results_list, key=lambda i: i['influence'], reverse=True)
        top5_list = results_list[:5]  # IMPORTANT - We get the top 5 influencers

        return self.serialize(top5_list)


# ### 11. Table of Influencers
class tableInfuencersData(StandByAnalysis):
    """
    This subclass sorts the influencers found in the analysis with a lot more information and organizes them
    in a table with more information about them.
    """

    def __init__(self):
        super(tableInfuencersData, self).__init__(
            _graph_id=int(PropertiesLoader.get_from_ini(CONFIG_IDS_SECTION, self.__class__.__name__)),
            _name=PropertiesLoader.get_from_ini(CONFIG_NAMES_SECTION, self.__class__.__name__))

    def apply_algorithm(self, __df_dict):
        pass


# ### 12. Individual Influencer Profile


# ### 13. Scope

# TODO TweetsAnalysis,
class scope(ProfilesAnalysis):
    """
    This subclass calculates the number of followers who have seen a brand´s post.
    As it is impossible to determine the number of people who have phisically seen
    a post with technical tools, we have concluded that one possibility is to add
    the number of retweets, favourites and comments of that post and divide it
    by the number of followers of the brand´s account.

    To sum up:

        scope = ( num_views/num_of_followers ) * 100

    where num_views is:

        num_views = rts + favs + comments
    """

    def __init__(self):
        super(scope, self).__init__(
            _graph_id=int(PropertiesLoader.get_from_ini(CONFIG_IDS_SECTION, self.__class__.__name__)),
            _name=PropertiesLoader.get_from_ini(CONFIG_NAMES_SECTION, self.__class__.__name__))

    @staticmethod
    def _dict_list_update(list1, list2):

        for item_list1 in list1:
            if item_list1 not in list2:
                list2.append(item_list1)

        return list2

    @staticmethod
    def get_num_followers(username, __df_dict):

        return __df_dict['profiles']['main_profiles'].loc[(__df_dict['profiles']['main_profiles']['ID']
                                                                       == username), 'Num_Followers'].tolist()

    def apply_algorithm(self, __df_dict):

        # VARIABLES
        results_list = []

        # Get tweets from keywords or profiles. Depending on which one is not empty
        df_tweets = __df_dict['tweets']['tweets_data']

        for index, tweet in df_tweets.iterrows():

            user_name = tweet['ID']
            rts_list = tweet['List_Users_Giving_RTs']
            favs_list = tweet['List_Users_Giving_Favorites']

            self._logger.debug(f"Rts: {len(rts_list)}\n"
                               f"Favs: {len(favs_list)}\n")

            # First of all, eliminate the duplicates in the two lists (three, in case comments could be collected)
            # These are the people who give a retweet or favourite to the same post , gives retweet, favourite and comments and viceversa
            # These people must be counted as one view in our algorithm

            # Joins both lists and eliminates duplicated items
            # In this case, count people who have both given rt and fav as only 1 view
            people_who_saw_tweet_1 = self._dict_list_update(rts_list, favs_list)

            # Get the number of views
            num_views = tweet['Num_RTs'] + tweet['Num_Favs'] #len(people_who_saw_tweet_1) # TODO - Change it back to len(people...)

            # Get the number of followers
            row_followers = self.get_num_followers(user_name, __df_dict)
            num_followers = row_followers[0]

            # Calculate the scope
            scope_value = (num_views / num_followers) * 1000  #(num_views / num_followers) * 100000

            self._logger.debug(f"the number of people who have seen the tweet of {user_name} is {num_views} with {num_followers} followers: scope = {scope_value}")

            # Store the results with its appropiate format
            results_list.append(self.encapsulate_data(category = user_name,
                                                      value1 = scope_value,
                                                      value2 = (100 - scope_value),
                                                      bullet = "https://cdn4.iconfinder.com/data/icons/color-webshop/512/twitter_bird-512.png"))

        return self.serialize(results_list)


# ### 14. Time Interaction


class timeInteraction(sentimentAnalysis, TweetsAnalysis, ProfilesAnalysis):

    def __init__(self):
        super(timeInteraction, self).__init__(graph_id=int(PropertiesLoader.get_from_ini(CONFIG_IDS_SECTION, self.__class__.__name__)),
                                              name=PropertiesLoader.get_from_ini(CONFIG_NAMES_SECTION, self.__class__.__name__),
                                              vectorizer_path=PropertiesLoader.get_from_ini(CONFIG_MODELS_SECTION, 'sentiment_vectorizer_path'),
                                              classifier_path=PropertiesLoader.get_from_ini(CONFIG_MODELS_SECTION, 'sentiment_classifier_path'))

    @staticmethod
    def get_hour(_datetime):
        """
        This method receives a datetime object resulting from ingesting with Tweepy and returns only the time field.

        Args:
            _datetime (str): the datetime object. Format example: "2010-06-14 19:09:20"

        Returns:
            str: the hours and minutes of the given datetime object. Format example: "19:09"
        """

        datetime = _datetime.split(" ")
        return datetime[1][:5]

    def get_tweets_by_hour(self, _tweet_list):
        """
        This method receives a dataframe of tweets and separates them according to the time of day at which it has been published.
        It will return an array of dictionaries. Each dictionary will have two keys, "hour" and "count".

        Args:
            _tweet_list (`list`: of str): List of tweets´ dates

        Returns:
            :obj:`list` of str: list of string in format "hours:minutes" encountered on the tweets
        """

        times_list = []

        # 2. Iterate over times
        for tweet_time in _tweet_list:
            self._logger.debug(f"tweet detected in hour {tweet_time}\n")
            hour = self.get_hour(str(tweet_time))
            times_list.append(hour)

        return times_list

    def create_time_array(self, times_list):
        """
        This method creates the array of dictionaries to store the hours and tweets
        """
        time_array = []

        times_list.sort()
        min_limit = int(times_list[0][:2])
        max_limit = int(times_list[-1][:2])

        for h in range(min_limit, max_limit):

            for m in range(0, 60):

                if m < 10:
                    minutes = "0" + str(m)
                else:
                    minutes = str(m)

                if h < 10:
                    hour = "0" + str(h) + ":" + minutes
                else:
                    hour = str(h) + ":" + minutes

                if hour in times_list:
                    pass
                else:
                    time_array.append(hour)

        return time_array



    def apply_algorithm(self, __df_dict):

        # VARIABLES
        results_list = []
        pos_tag = 2
        neu_tag = 1
        neg_tag = 0
        date_format_string = "Thu Oct 03 2019 {hour}:00 GMT+0200 (hora de verano de Europa central)"

        # Get the tweets data
        df_tweets = __df_dict['tweets']['tweets_data']

        if self._classifier or self._vectorizer is None:
            self.load_model()

        if sentimentAnalysis._sentiment_predictions_on_tweets is None:
            self.apply_sentiment_to_tweets(__df_dict)

        sentimentAnalysis._sentiment_predictions_on_tweets[sentimentAnalysis._sentiment_predictions_on_tweets == 0] = -1
        sentimentAnalysis._sentiment_predictions_on_tweets[sentimentAnalysis._sentiment_predictions_on_tweets == 2] = 1

        # Get dates of tweets splitted and listed in hours
        times_list = self.get_tweets_by_hour(df_tweets['Created_At'].tolist())

        self._logger.debug(f"List of times collected:\n"
                           f"{times_list}")

        myset = set(times_list)
        times_new_list = list(myset)

        time_array = self.create_time_array(times_new_list)

        for item_hour in time_array:

            complete_date = date_format_string.replace("{hour}", item_hour)

            results_list.append(self.encapsulate_data(date_time=str(complete_date),
                                                      hour=item_hour,
                                                      positive=0,
                                                      neutral=0,
                                                      negative=0,
                                                      total_tweets=0))

        # We get a subdataframe with only the data in
        # column 'Text'
        for date_item in times_new_list:

            # Get list of tweets of each day
            df_time_date = df_tweets[df_tweets['Created_At'].astype(str).str.contains(date_item)]
            list_of_tweets_in_date = df_time_date['Text'].tolist()

            # Preprocess the texts given (clean them)
            # 'clean_text' method is in ingest_extraction_v2 file
            text_list = [extraction.clean_text(d) for d in list_of_tweets_in_date]

            # Vectorize the data before predicting it
            sentences = self._vectorizer.transform(text_list)

            # Predict with the vectorized data
            predicted = self._classifier.predict(sentences)
            pred = np.array(predicted)

            # Count the number of ocurrences of each sentiment
            count_negative = np.count_nonzero(pred == neg_tag)
            count_neutral = np.count_nonzero(pred == neu_tag)
            count_positive = np.count_nonzero(pred == pos_tag)
            total_count = len(pred)

            complete_date = date_format_string.replace("{hour}", date_item)

            # Encapsulate the data into correspondent JSON format
            results_list.append(self.encapsulate_data(date_time = str(complete_date),
                                                      hour = date_item,
                                                      positive = count_positive,
                                                      neutral = count_neutral,
                                                      negative = count_negative,
                                                      total_tweets = total_count))

        sorted_hour_results_list = sorted(results_list, key=lambda i: i['date_time'])

        # Return the result serialized
        return self.serialize(sorted_hour_results_list)

# ### Main function API



if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s %(filename)s, line %(lineno)s - %(name)s.%(funcName)s() - '
                               '%(levelname)s - %(message)s ', level=logging.DEBUG)
    AnalysisAPI()



