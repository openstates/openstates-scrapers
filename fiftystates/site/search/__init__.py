import re

from fiftystates.backend import db

import nltk


def keywordize(str):
    """
    Splits a string into words, removes common stopwords, stems and removes
    duplicates.
    """
    sents = nltk.tokenize.sent_tokenize(str)

    words = []
    for sent in sents:
        words.extend(nltk.tokenize.word_tokenize(sent))

    stemmer = nltk.stem.porter.PorterStemmer()
    stop_words = nltk.corpus.stopwords.words()
    words = [stemmer.stem(word.lower()) for word in words if
             (word.isalpha() or word.isdigit()) and
             word.lower() not in stop_words]
    words = set(words)

    return words


def bill_query(str, params, fields=None, all=True, limit=None, skip=None,
               sort=None):
    keywords = list(keywordize(str))

    filter = {}

    if all:
        filter['keywords'] = {'$all': keywords}
    else:
        filter['keywords'] = {'$in': keywords}

    for key in ('state', 'session', 'chamber'):
        value = params.get(key)
        if value:
            filter[key] = value

    cursor = db.bills.find(filter, fields)

    if limit:
        cursor.limit(limit)

    if skip:
        cursor.skip(skip)

    if sort:
        cursor.sort(sort)

    return list(cursor)
