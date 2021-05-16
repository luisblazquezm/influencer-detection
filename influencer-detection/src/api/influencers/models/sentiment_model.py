#!flask/bin/python

# Copyright 2020 Luis Blazquez Miñambres (@luisblazquezm), Miguel Cabezas Puerto (@MiguelCabezasPuerto), Óscar Sánchez Juanes (@oscarsanchezj) and Francisco Pinto-Santos (@gandalfran)
# See LICENSE for details.

import re
import logging    

from influencers import config
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from typing import Dict

"""logging.basicConfig(format='%(asctime)s %(filename)s, line %(lineno)s - %(name)s.%(funcName)s() - '
                           '%(levelname)s - %(message)s ', level=logging.DEBUG)"""


logging.basicConfig(format='%(asctime)s %(filename)s, %(funcName)s() - '
                           '%(message)s ', level=logging.DEBUG)


class SentimentAnalyzer:

    def __init__(self):
        self._analyser = SentimentIntensityAnalyzer()

    def clean_analyzer(self, text: str):
        """
        Remove unnecessary characters from text (such as special characters, emojis, etc)
        so that it only contains words and spaces between them.

        Args:
            text (:obj:`str`): This is the string that contains the tweet received from Twitter

        Returns:
            :obj:`str`: postcleaning text string (only words and spaces)
        """

        # IMPORTANT: in Spanish sentiment analysis is important to keep ortographic accents
        # In English the NFD deletes these elements by their UNICODE identifier or weight
        # tweet = re.sub(
        #    r"([^n\u0300-\u036f]|n(?!\u0303(?![\u0300-\u036f])))[\u0300-\u036f]+", r"\1",
        #    normalize("NFD", tweet), 0, re.I
        # )
        # print(text)
        # NFC
        text = normalize('NFC', text)

        # Remove emojis
        emoji_pattern = re.compile("["
                                   u"\U0001F600-\U0001F64F"  # emoticons
                                   u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                                   u"\U0001F680-\U0001F6FF"  # transport & map symbols
                                   u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                                   "]+", flags=re.UNICODE)
        text = emoji_pattern.sub(r'', text)  # no emoji

        # Remove links
        text = re.sub(r'http\S+', '', text)
        text = re.sub(r'www.[^ ]+', '', text)

        # Remove numbers
        text = re.sub(r'RT', '', text)

        # Remove RTs
        text = re.sub(r'RT', '', text)

        # Remove @ and #
        text = re.sub(r'(?:@|$|#|&)\S+', '', text)

        # Remove alphanumeric characters ( "" , '' , ? , ¿ , etc )
        text = re.sub(r'[^\w]', ' ', text)  # Words that do not start with a letter
        text = re.sub(r'[!"#$%&()*+,-./:;<=>?@[\]^_`{|}~]', '', text)  # Punctuation, commas, bars, etc

        # Remove new lines
        text = text.replace('\n', '')

        # Remove whitespaces
        " ".join(text.split())
        text = re.sub(r"^\s+", '', text)

        # Remove double whitespaces
        text = re.sub(' +', ' ', text)

        # Turn into lowercase
        text = text.lower()

        # Remove numbers
        text = ''.join([i for i in text if not i.isdigit()])

        return text

    def analyze(self, text: str, clean_text: bool = False) -> Dict:
        """Sentiment analyzer of text
        
        Arguments:
            text (:obj:`str`):sentence to analyze
        
        Keyword Arguments:
            clean_text (:obj:`bool`, optional): flag indicating if the text must be cleaned or not (default: {False})
        
        Returns:
            :obj:`str`: sentiment result of the analyzer
        """
        sentiment_result = ""

        if clean_text:
            text = self.clean(text)

        # src: https://medium.com/analytics-vidhya/simplifying-social-media-sentiment-analysis-using-vader-in-python-f9e6ec6fc52f
        # polarity_scores method of SentimentIntensityAnalyzer 
        # object gives a sentiment dictionary. 
        # which contains pos, neg, neu, and compound scores. 
        score_dict = self._analyser.polarity_scores(text)

        #print("Overall sentiment dictionary is : ", score_dict) 
        #print("sentence was rated as ", score_dict['neg']*100, "% Negative") 
        #print("sentence was rated as ", score_dict['neu']*100, "% Neutral") 
        #print("sentence was rated as ", score_dict['pos']*100, "% Positive") 
      
        # decide sentiment as positive, negative and neutral 
        if score_dict['compound'] >= 0.05 : 
            sentiment_result = "Positive"
        elif score_dict['compound'] <= - 0.05 : 
            sentiment_result = "Negative"
        else: 
            sentiment_result = "Neutral"

        return {"sentiment": sentiment_result}