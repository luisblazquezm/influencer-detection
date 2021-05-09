#!flask/bin/python

# Copyright 2020 Luis Blazquez Miñambres (@luisblazquezm), Miguel Cabezas Puerto (@MiguelCabezasPuerto), Óscar Sánchez Juanes (@oscarsanchezj) and Francisco Pinto-Santos (@gandalfran)
# See LICENSE for details.

import re
import numpy as np

# Load the library with the CountVectorizer method
from sklearn.feature_extraction.text import CountVectorizer
# Load the LDA model from sk-learn
from sklearn.decomposition import LatentDirichletAllocation as LDA
from typing import List, Dict, Any

NUM_TOPICS = 5 # Number of topics to extract from text
NUM_WORDS = 10 # Number of words to extract from each topic

class InfluenceDetection:

    def __init__(self):
        super(influencerDetection, self).__init__(
            _graph_id=PropertiesLoader.get_from_ini(CONFIG_IDS_SECTION, self.__class__.__name__),
            _name=PropertiesLoader.get_from_ini(CONFIG_NAMES_SECTION, self.__class__.__name__)
        )

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