# https://stackoverflow.com/questions/57057039/how-to-extract-all-words-in-a-noun-food-category-in-wordnet
# Using the NLTK WordNet dictionary check if the word is noun and a food.
from typing import Literal

import nltk
from nltk.corpus import wordnet as wn

nltk.download("wordnet")


def if_food(word: str) -> Literal[0, 1]:
    syns = wn.synsets(str(word), pos=wn.NOUN)

    for syn in syns:
        if syn and ("food" in syn.lexname()):
            return 1
    return 0
