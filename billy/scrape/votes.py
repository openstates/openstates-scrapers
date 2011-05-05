import os
import itertools
import json

from billy.scrape import Scraper, SourcedObject, JSONDateEncoder


class VoteScraper(Scraper):

    scraper_type = 'votes'

    def __init__(self, *args, **kwargs):
        super(VoteScraper, self).__init__(*args, **kwargs)

    def _get_schema(self):
        schema_path = os.path.join(os.path.split(__file__)[0],
                                   '../schemas/vote.json')
        schema = json.load(open(schema_path))
        schema['properties']['session']['enum'] = self.all_sessions()
        return schema

    def scrape(self, chamber, session):
        """
        Grab all votes for a given chamber and session.  Must be overridden
        by subclasses.

        Should raise a :class:`NoDataForPeriod` exception if it is not
        possible to scrape votes for the provided session.
        """
        raise NotImplementedError('VoteScrapers must define a scrape method')

    def save_vote(self, vote):
        """
        Save a scraped :class:`~billy.scrape.votes.Vote` object.

        Should be called after all data for the given vote is collected.
        """
        self.log("save_vote %s %s: %s '%s'" % (vote['session'],
                                               vote['chamber'],
                                               vote['bill_id'],
                                               vote['motion']))
        self.save_object(vote)


class Vote(SourcedObject):

    sequence = itertools.count()

    def __init__(self, chamber, date, motion, passed,
                 yes_count, no_count, other_count, type='other', **kwargs):
        """
        Create a new :obj:`Vote`.

        :param chamber: the chamber in which the vote was taken,
          'upper' or 'lower'
        :param date: the date/time when the vote was taken
        :param motion: a string representing the motion that was being voted on
        :param passed: did the vote pass, True or False
        :param yes_count: the number of 'yes' votes
        :param no_count: the number of 'no' votes
        :param other_count: the number of abstentions, 'present' votes,
          or anything else not covered by 'yes' or 'no'.
        :param type: vote type classification

        Any additional keyword arguments will be associated with this
        vote and stored in the database.

        Examples: ::

          Vote('upper', '', '12/7/08', 'Final passage',
               True, 30, 8, 3)
          Vote('lower', 'Finance Committee', '3/4/03 03:40:22',
               'Recommend passage', 12, 1, 0)
        """
        super(Vote, self).__init__('vote', **kwargs)
        self['chamber'] = chamber
        self['date'] = date
        self['motion'] = motion
        self['passed'] = passed
        self['yes_count'] = yes_count
        self['no_count'] = no_count
        self['other_count'] = other_count
        self['type'] = type
        self['yes_votes'] = []
        self['no_votes'] = []
        self['other_votes'] = []

    def yes(self, legislator):
        """
        Indicate that a legislator (given as a string of their name) voted
        'yes'.

        Examples: ::

           vote.yes('Smith')
           vote.yes('Alan Hoerth')
        """
        self['yes_votes'].append(legislator)

    def no(self, legislator):
        """
        Indicate that a legislator (given as a string of their name) voted
        'no'.
        """
        self['no_votes'].append(legislator)

    def other(self, legislator):
        """
        Indicate that a legislator (given as a string of their name) abstained,
        voted 'present', or made any other vote not covered by 'yes' or 'no'.
        """
        self['other_votes'].append(legislator)

    def validate(self):
        if self['yes_votes'] or self['no_votes'] or self['other_votes']:
            # If we have *any* specific votes, then validate the counts
            # for all types.
            assert len(self['yes_votes']) == self['yes_count']
            assert len(self['no_votes']) == self['no_count']
            assert len(self['other_votes']) == self['other_count']

    def get_filename(self):
        filename = '%s_%s_%s_seq%s.json' % (self['session'],
                                            self['chamber'],
                                            self['bill_id'],
                                            self.sequence.next())
        return filename
