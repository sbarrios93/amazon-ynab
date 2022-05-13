# https://stackoverflow.com/questions/57057039/how-to-extract-all-words-in-a-noun-food-category-in-wordnet
# Using the NLTK WordNet dictionary check if the word is noun and a food.
import nltk

nltk.download("wordnet")
from nltk.corpus import wordnet as wn


def if_food(word):

    syns = wn.synsets(str(word), pos=wn.NOUN)

    for syn in syns:
        if "food" in syn.lexname():
            return 1
    return 0
