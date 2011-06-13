#!/usr/bin/env python
import itertools
import collections

from nltk.corpus import stopwords
from nltk.corpus.reader.plaintext import CategorizedPlaintextCorpusReader
from nltk.classify import NaiveBayesClassifier
import nltk.classify.util
from nltk.collocations import BigramCollocationFinder, TrigramCollocationFinder
from nltk.metrics import BigramAssocMeasures, TrigramAssocMeasures
from nltk.probability import FreqDist, ConditionalFreqDist

stopset = set(stopwords.words('english'))
stopset.add('member')
stopset.add('california')
stopset.add('state')


def most_informative_words(corpus, categories=['dem', 'rep'], count=2500):
    fd = FreqDist()
    cond_fd = ConditionalFreqDist()
    word_counts = {}

    for cat in categories:
        for word in corpus.words(categories=[cat]):
            word = word.lower().strip(".!?:,/ ")
            if not word.isalpha() or word in stopset:
                continue
            fd.inc(word)
            cond_fd[cat].inc(word)

        word_counts[cat] = cond_fd[cat].N()

    total_word_count = sum(word_counts.values())

    word_scores = collections.defaultdict(int)
    for word, freq in fd.iteritems():
        for cat in categories:
            cat_word_score = BigramAssocMeasures.chi_sq(
                cond_fd[cat][word],
                (freq, word_counts[cat]),
                total_word_count)
            word_scores[word] += cat_word_score

    informative_words = sorted(word_scores.iteritems(),
                               key=lambda (w, s): s,
                               reverse=True)[:count]
    return set([w for w, s in informative_words])


def word_feats(words):
    feats = {}
    for word in words:
        word = word.lower().strip(".!?:,/ ")
        if word in best_words:
            feats[word] = True
    return feats


def bigram_feats(words):
    filtered_words = []
    for word in words:
        word = word.lower().strip(".!?:,/ ")
        if word in best_words:
            filtered_words.append(word)

    bigram_finder = BigramCollocationFinder.from_words(filtered_words)
    bigrams = bigram_finder.nbest(BigramAssocMeasures.chi_sq, 200)
    return dict([(ngram, True) for ngram in itertools.chain(filtered_words,
                                                            bigrams)])


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('directory',
                        help="the bill directory")
    parser.add_argument('--bigrams', action='store_true', dest='bigrams',
                        default=False, help='use bigrams')
    args = parser.parse_args()

    if args.bigrams:
        featurizer = bigram_feats
    else:
        featurizer = word_feats

    corpus = CategorizedPlaintextCorpusReader(
        root=args.directory,
        fileids=".*/.*\.txt",
        cat_pattern=r'(dem|rep)/')

    best_words = most_informative_words(corpus)

    dem_ids = corpus.fileids(categories=['dem'])
    rep_ids = corpus.fileids(categories=['rep'])

    dem_feats = [(featurizer(corpus.words(fileids=[f])), 'dem')
                 for f in dem_ids]
    rep_feats = [(featurizer(corpus.words(fileids=[f])), 'rep')
                 for f in rep_ids]

    dem_cutoff = len(dem_feats) * 5 / 6
    rep_cutoff = len(rep_feats) * 5 / 6

    train_feats = dem_feats[:dem_cutoff] + rep_feats[:rep_cutoff]
    test_feats = dem_feats[dem_cutoff:] + rep_feats[rep_cutoff:]
    print 'training on %d instances, testing on %d instances' % (
        len(train_feats), len(test_feats))

    classifier = NaiveBayesClassifier.train(train_feats)
    print 'accuracy:', nltk.classify.util.accuracy(classifier, test_feats)

    classifier.show_most_informative_features(10)
