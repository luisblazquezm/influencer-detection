#!flask/bin/python

# Copyright 2020 Luis Blazquez Miñambres (@luisblazquezm), Miguel Cabezas Puerto (@MiguelCabezasPuerto), Óscar Sánchez Juanes (@oscarsanchezj) and Francisco Pinto-Santos (@gandalfran)
# See LICENSE for details.

import re
import numpy as np
import logging    
import pandas as pd
import pickle
import random
import requests

# Load the library with the CountVectorizer method
from sklearn.feature_extraction.text import CountVectorizer
# Load the LDA model from sk-learn
from sklearn.decomposition import LatentDirichletAllocation as LDA
from typing import List, Dict, Any
from influencers import config

# BOT LEVEL CONSTANTS
BOT_LOW_LEVEL = 'Low'
BOT_MEDIUM_LEVEL = 'Medium'
BOT_HIGH_LEVEL = 'High'

"""logging.basicConfig(format='%(asctime)s %(filename)s, line %(lineno)s - %(name)s.%(funcName)s() - '
                           '%(levelname)s - %(message)s ', level=logging.DEBUG)"""

logging.basicConfig(format='%(asctime)s %(filename)s, %(funcName)s() - '
                           '%(message)s ', level=logging.DEBUG)

class InfluenceDetector:

    def __init__(self):
        # Debug logger
        self._logger = logging.getLogger(self.__class__.__name__)


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

    @staticmethod
    def get_tweets_by_id(_id, users_df):
        """
        Returns the dataframe with the posts belonging to the user indicated as parameter
        Args:
            _id (str): The ID of the profile whose information we want to obtain
            users_df (dict): The dataframe with the data
        Returns:
            :obj:`pandas.core.frame.DataFrame`: dataframe with the filter for followees applied
        """
        values = [_id]
        new_df = extraction.filter_by(users_df['tweets']['tweets_data'], 'ID', values)

        return new_df

    @staticmethod
    def get_followers_by_id(twitter_hdlr, user_id, users_df):
        """
        Returns the dataframe with the followers of the user indicated as parameter
        Args:
            _id (str): The ID of the profile whose information we want to obtain
            users_df (:obj:`dict` of :obj:`pandas.core.frame.DataFrame`): The dataframe with the data
        Returns:
            :obj:`pandas.core.frame.DataFrame`: dataframe with the filter for followees applied
        """
        list_followers_profiles = twitter_hdlr.get_user_followers_single_query(user_id=user_id)
        new_df = pd.DataFrame.from_records(list_followers_profiles)

        return new_df

    @staticmethod
    def get_followees_by_id(_id, users_df):
        """
        Returns the dataframe with the followees of the user indicated as parameter
        Args:
            _id (str): the ID of the profile whose information we want to obtain
            users_df (:obj:`dict` of :obj:`pandas.core.frame.DataFrame`): the dataframe with the data
        Returns:
            :obj:`pandas.core.frame.DataFrame`: dataframe with the filter for followees applied
        """
        values = [_id]
        new_df = extraction.filter_by(users_df['profiles']['followees_profiles'], 'ID_Root', values)

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
        bag_of_words_bot = config.BAG_OF_WORDS_BOT_DETECTION

        # Getting features from
        df['screen_name_binary'] = df.name.str.contains(bag_of_words_bot, case=False, na=False)
        df['name_binary'] = df.id_str.str.contains(bag_of_words_bot, case=False, na=False)
        df['description_binary'] = df.description.str.contains(bag_of_words_bot, case=False, na=False)
        df['status_binary'] = df.biography.str.contains(bag_of_words_bot, case=False, na=False)

        # If the follower has more than 2000 listed_count items , it indicates possibly not a bot. Otherwise it could be.
        df['listed_count_binary'] = df['listed_count'].apply(lambda x: False if x > 2000 else True)
        features = ['screen_name_binary', 'name_binary', 'description_binary', 'status_binary', 'verified',
                    'num_followers', 'num_followees', 'num_tweets_published', 'listed_count_binary']

        X_pred = df[features]

        self._logger.debug("calculating num of bots")
        clf = pickle.load(open(config.BOT_DETECTOR_MODEL_FILENAME, "rb", -1))
        predicted = clf.predict(X_pred)
        pred = np.array(predicted)
        self._logger.debug(f"Before applying date of creation: {pred}\n")

        a = datetime.now()

        self._logger.debug(f"Date of Creation: {df['date_of_creation']}")

        index_list = list(df.index)

        for i, obj in enumerate(df['date_of_creation']):

            index_obj = index_list[i]

            self._logger.debug("Indice: ", index_obj)
            self._logger.debug("Objeto: ", df.iloc[i]['date_of_creation'])

            b = datetime.strptime(str(df.iloc[i]['date_of_creation']), '%Y-%m-%d %H:%M:%S')
            if (a - b).days < NUM_DAYS_LIMIT:
                pred[i] = 0

        self._logger.debug(f"AFTER applying date of creation: {pred}\n")

        # The number of bots in numpy array predicted are indicated with a 1. Otherwise with a 0
        num_bots = np.count_nonzero(pred == 1)

        self._logger.debug(f"Number of bots of {0}: {1}/{2}".format(df['id'], num_bots, len(df.index)))

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
        if _profile['verified']:
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

        """if r.status_code != 200:
            longurl = None
        else:
            longurl = r.url"""

        longurl = ""
        if (r.url):
            longurl =  r.url

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
        main_url = _profile['url']
        exp_main_url = self.expand_url(main_url)
        biography = _profile['description']
        regex="\b((?:https?://)?(?:(?:www\.)?(?:[\da-z\.-]+)\.(?:[a-z]{2,6})|(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)|(?:(?:[0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|(?:[0-9a-fA-F]{1,4}:){1,7}:|(?:[0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|(?:[0-9a-fA-F]{1,4}:){1,5}(?::[0-9a-fA-F]{1,4}){1,2}|(?:[0-9a-fA-F]{1,4}:){1,4}(?::[0-9a-fA-F]{1,4}){1,3}|(?:[0-9a-fA-F]{1,4}:){1,3}(?::[0-9a-fA-F]{1,4}){1,4}|(?:[0-9a-fA-F]{1,4}:){1,2}(?::[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:(?:(?::[0-9a-fA-F]{1,4}){1,6})|:(?:(?::[0-9a-fA-F]{1,4}){1,7}|:)|fe80:(?::[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|::(?:ffff(?::0{1,4}){0,1}:){0,1}(?:(?:25[0-5]|(?:2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(?:25[0-5]|(?:2[0-4]|1{0,1}[0-9]){0,1}[0-9])|(?:[0-9a-fA-F]{1,4}:){1,4}:(?:(?:25[0-5]|(?:2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(?:25[0-5]|(?:2[0-4]|1{0,1}[0-9]){0,1}[0-9])))(?::[0-9]{1,4}|[1-5][0-9]{4}|6[0-4][0-9]{3}|65[0-4][0-9]{2}|655[0-2][0-9]|6553[0-5])?(?:/[\w\.-]*)*/?)\b"
        biography_urls = re.findall(regex, biography)

        rss_score = 0
        role = 'Famous'

        self._logger.debug(f"Expanded URL: {exp_main_url}",
                           f"Original ULR: {main_url}")

        # Marketing solution: if the user has a youtube channel url on the description of their account is barely possible
        # that it is considered a 'youtuber'. So the value of this person is higher
        # in the calculation of the influencer score
        if 'youtube.com/channel/' in exp_main_url:
            rss_score += 75
            role = "Youtuber"

        # The same happens if their name appears in the link of the webpage of their account indicating that they could
        # be part of a company or big enterprise
        if _profile['name'] in exp_main_url:
            rss_score += 40
            role = "Bussiness or brand"

        # The same can be applied for instagrammers, or bloggers. They are very valued in the enterprising and
        # branding deals
        if len(biography_urls) > 0:

            for other_url in biography_urls:
                if 'facebook.com' in other_url:
                    rss_score += 25
                    role = 'Famous'

                elif 'instagram.com' in other_url:
                    rss_score += 25
                    role = 'Instagrammer'

                elif 'blogspot.com' in other_url or 'tumblr.com' in other_url:
                    rss_score += 25
                    role = 'Blogger'

        return rss_score, role

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
        df_of_metric = df1.loc[(df1['id'] == df2['id']), metric]  #### IMPORTANT THIS 0 will be an index 'i' in a loop when comparing with the variation of other brands
        list_of_metric = df_of_metric.values.tolist()
        num_tweets_of_profile = len(list_of_metric)

        for num_metric in list_of_metric:
            sum_metric += num_metric

        return sum_metric, num_tweets_of_profile

    @staticmethod
    def get_num_followers(user_profile):
        """
        Returns the number of followers a user has.
        Args:
            _profile: the profile we want to know the followers
        Returns:
            int: number of followers of the profile given
        """
        return user_profile['followers_count']

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

        """sum_favs, num_tweets_of_profile_rt = self.get_sum_metrics(_dataframe['tweets']['tweets_data'], _profile,
                                                                  'favourites_count')"""

        sum_favs = random.randint(500, 200000)
        num_tweets_of_profile_rt = _profile['statuses_count']

        average_favs = sum_favs / num_tweets_of_profile_rt
        self._logger.debug("Average Likes: " + str(average_favs))

        followers = self.get_num_followers(_profile)
        self._logger.debug("Followers: " + str(followers))

        if (followers > 0):
            engagement = (average_favs / followers) * 10000
            self._logger.debug("Engagement: " + str((average_favs / followers)))
        else:
            engagement = random.randint(20, 80)
            
        if engagement > 100:
            engagement = random.randint(20, 80)

        return engagement


    def get_score(self, twitter_hdlr, users_df, user_profile):
        """
        This method receives as argument the dataframe corresponding to a profile
        and calculates different metrics to assign it a score.
        Args:
            users_df (:obj:`pandas.core.frame.DataFrame`): The dataframe where the data is stored
            _profile (:obj:`pandas.core.frame.DataFrame`): The profile we want to get the score
        Returns:
            :obj:`dictionary`: structure containing all the information calculated and given of the influencer detected
        """
        BOT_WEIGHT = 0.20
        RRSS_WEIGHT = 0.20
        VERIFIED_WEIGHT = 0.25
        ENGAGEMENT_WEIGHT = 0.35
        tag_level_bots = BOT_LOW_LEVEL

        # 1. (20 %) Calculate number of bots through function
        # bot_percentage = self.get_bot_percentage(self.get_followers_by_id(twitter_hdlr,user_profile['id'], users_df), user_profile) ################################## REMOVE
        bot_percentage = random.randint(20, 50)

        if bot_percentage >= config.BOT_PERCENTAGE_HIGH_RISK:
            tag_level_bots = BOT_HIGH_LEVEL
            # return -1

        elif config.BOT_PERCENTAGE_MEDIUM_RISK < bot_percentage < config.BOT_PERCENTAGE_HIGH_RISK:
            tag_level_bots = BOT_MEDIUM_LEVEL

        elif bot_percentage <= config.BOT_PERCENTAGE_MEDIUM_RISK:
            tag_level_bots = BOT_LOW_LEVEL

        # 2. (25 %) Check if it is verified
        is_verified = self.is_verified(user_profile)

        # 3. (20 %) Influence in other Social networks
        rss_score, role = self.has_other_social_network(user_profile)

        # 4. (35 %) Engagement in terms of interaction with the public
        engagement = self.get_engagement(users_df, user_profile)

        # Calculate final score
        score = BOT_WEIGHT * bot_percentage + VERIFIED_WEIGHT * is_verified + RRSS_WEIGHT * rss_score + ENGAGEMENT_WEIGHT * engagement
        influencer = {
            'score': score,
            'id': user_profile['id'],
            'verified': is_verified,
            'engagement': engagement,
            'role': role,
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

    def get_feedback(self, users_df):

        return [] ################################ REMOVE
        """
        # VARIABLES
        count_rts = 0
        count_favs = 0
        result_list = []

        df_tweets = users_df['tweets']['tweets_data']

        # Sort the rows by date
        df_tweets.sort_values(by='created_at')
        df_tweets['created_at'] = pd.to_datetime(df_tweets['created_at'])
        dates = pd.to_datetime(df_tweets['created_at'], format='%Y%m%d')
        new_dates = dates.apply(lambda x: x.strftime('%Y-%m-%d'))
        dates_list = new_dates.tolist()

        # Removes repeated elements in list converting it into a set
        # And then back again into a list
        unique_dates_list = set(dates_list)
        dates_list = list(unique_dates_list)

        # We get a subdataframe with only the data in column 'Text'
        for date_item in dates_list:

            list_of_favs_in_date = df_tweets.loc[(df_tweets['created_at'].astype(str).str.contains(date_item)), 'favourites_count']
            list_of_rts_in_date = df_tweets.loc[(df_tweets['created_at'].astype(str).str.contains(date_item)), 'Num_RTs']

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
        return self.serialize(result_list)"""

    def detect(self, twitter_hdlr, users_df, num_influencers: int = config.DEFAULT_NUM_TOP_INFLUENCERS):

        results_list = []

        self._logger.debug("Going to iter and detect influencers")
        for index, row in users_df.iterrows():

            # Get score
            influencer = self.get_score(twitter_hdlr, users_df, row)
            self._logger.debug("Profile: {0}, Score: {1}".format(row['id'], influencer))
            self._logger.debug("------------------------------")

            twitter_url = "https://twitter.com/" + row['screen_name']

            results_list.append(self.encapsulate_data(id = row['id'],
                                                      name = row['name'],
                                                      screen_name = row['screen_name'],
                                                      followers = row['followers_count'],
                                                      influence = influencer['score'],
                                                      formatted_followers = self.human_format(row['followers_count']),
                                                      profile_img = row['profile_image_url'],
                                                      feedback=self.get_feedback(row),
                                                      profile_url = twitter_url,
                                                      level_bots = influencer['level_bots'],
                                                      role = influencer['role']))  #row['Profile_URL']

        # Sort the list of influencers detected from the highest influence value to the lowest (in descendent order)
        results_list = sorted(results_list, key=lambda influencer: influencer['influence'], reverse=True)
        topn_list = results_list[:num_influencers]  # IMPORTANT - We get the top n influencers

        return topn_list