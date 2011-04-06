from billy import db, utils

import numpy
from numpy import linalg


def generate_leg_indexes(state, term, chamber):
    leg_indexes = {}
    elemMatch = {'state': state, 'chamber': chamber,
                 'type': 'member', 'term': term}
    i = 0
    for leg in db.legislators.find({'$or':
                                    [{'roles': {'$elemMatch': elemMatch}},
                                     {('old_roles.%s' % term):
                                      {'$elemMatch': elemMatch}}]}):
        leg_indexes[leg['leg_id']] = i
        i += 1
    return leg_indexes


def generate_adjacency_matrix(state, session, chamber, leg_indexes,
                              primary_sponsor_type='LEAD_AUTHOR'):
    size = len(leg_indexes)
    matrix = numpy.zeros((size, size))

    for bill in db.bills.find({'state': state, 'session': session,
                               'chamber': chamber}):
        try:
            for author in bill['sponsors']:
                if author['type'] == primary_sponsor_type:
                    primary_sponsor_id = leg_indexes[author['leg_id']]
                    break
            else:
                continue
        except KeyError:
            continue
        except IndexError:
            continue

        for sponsor in bill['sponsors'][1:]:
            if sponsor['type'] == primary_sponsor_type:
                continue

            try:
                sponsor_id = leg_indexes[sponsor['leg_id']]
            except KeyError:
                continue

            matrix[primary_sponsor_id, sponsor_id] += 1

    return matrix


def pagerank(matrix, d_factor=0.85):
    """
    Calculate the pagerank vector of a given adjacency matrix (using
    the power method).

    :param matrix: an adjacency matrix
    :param d_factor: the damping factor
    """
    size = len(matrix)
    epsilon = 0.0001
    matrix = matrix.copy()

    # Divide each column by its number of outgoing links
    for i in xrange(0, size):
        col_sum = matrix[:, i].sum()
        if col_sum:
            matrix[:, i] /= col_sum

    e = ((1.0 - d_factor) / size) * numpy.ones((size, size))
    matrix = d_factor * matrix + e

    result = numpy.ones(size) / size
    prev = numpy.ones(size) / size
    iteration = 0

    while True:
        result = numpy.dot(matrix, result)
        result /= result.sum()
        diff = numpy.abs(result - prev).sum()
        print "Iteration %d, change %f" % (iteration, diff)
        if diff < epsilon:
            break
        prev = result
        iteration += 1

    return result


def legislator_pagerank(state, session, chamber, d_factor=0.85):
    term = utils.term_for_session(state, session)
    leg_indexes = generate_leg_indexes(state, term, chamber)
    adjacency_matrix = generate_adjacency_matrix(state, session,
                                                 chamber, leg_indexes)
    result = pagerank(adjacency_matrix, d_factor)

    for leg_id in leg_indexes.keys():
        leg_indexes[leg_id] = result[leg_indexes[leg_id]]

    return leg_indexes


if __name__ == '__main__':
    import sys
    import csv
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('state')
    parser.add_argument('session')
    parser.add_argument('chamber')
    args = parser.parse_args()

    pr = legislator_pagerank(args.state, args.session, args.chamber)
    out = csv.writer(sys.stdout)

    for (leg_id, value) in pr.iteritems():
        leg = db.legislators.find_one({'_id': leg_id})
        out.writerow((leg_id, leg['full_name'], value))
