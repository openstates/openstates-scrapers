from __future__ import with_statement
import os

try:
    import json
except ImportError:
    import simplejson as json

from fiftystates.scrape import Scraper, FiftystatesObject, JSONDateEncoder


class BillScraper(Scraper):

    scraper_type = 'bills'

    def _get_schema(self):
        schema_path = os.path.join(os.path.split(__file__)[0],
                                   '../../schemas/bill.json')
        schema = json.load(open(schema_path))
        schema['properties']['session']['enum'] = self.all_sessions()
        return schema

    def scrape(self, chamber, year):
        """
        Grab all the bills for a given chamber and year. Must be
        overridden by subclasses.

        Should raise a :class:`NoDataForPeriod` exception if the year is invalid.
        """
        raise NotImplementedError('BillScrapers must define a scrape method')

    def save_bill(self, bill):
        """
        Save a scraped :class:`~fiftystates.scrape.bills.Bill` object. Only
        call after all data for the given bill has been collected.
        """
        self.log("save_bill %s %s: %s" % (bill['chamber'],
                                          bill['session'],
                                          bill['bill_id']))

        bill['state'] = self.state
        self.validate_json(bill)

        filename = "%s_%s_%s.json" % (bill['session'], bill['chamber'],
                                      bill['bill_id'])
        filename = filename.encode('ascii', 'replace')
        with open(os.path.join(self.output_dir, "bills", filename), 'w') as f:
            json.dump(bill, f, cls=JSONDateEncoder)


class Bill(FiftystatesObject):
    """
    This represents a state bill or resolution.
    It is just a dict with some required fields and a few
    convenience methods. Any key/value pairs stored in it besides the
    required fields will be saved and stored in the backend database
    for later use.
    """

    def __init__(self, session, chamber, bill_id, title, **kwargs):
        """
        Create a new :obj:`Bill`.

        :param session: the session in which the bill was introduced.
        :param chamber: the chamber in which the bill was introduced:
          either 'upper' or 'lower'
        :param bill_id: an identifier assigned by the state to this bill
          (should be unique within the context of this chamber/session)
          e.g.: 'HB 1', 'S. 102', 'H.R. 18'
        :param title: a title or short description of this bill provided by
          the state

        Any additional keyword arguments will be associated with this
        bill and stored in the database.
        """
        super(Bill, self).__init__('bill', **kwargs)
        self['session'] = session
        self['chamber'] = chamber
        self['bill_id'] = bill_id
        self['title'] = title
        self['sponsors'] = []
        self['votes'] = []
        self['versions'] = []
        self['actions'] = []
        self['documents'] = []
        self['alternate_titles'] = []

        if not 'type' in kwargs or not kwargs['type']:
            self['type'] = ['bill']
        elif isinstance(kwargs['type'], basestring):
            self['type'] = [kwargs['type']]
        else:
            self['type'] = list(kwargs['type'])

    def add_sponsor(self, type, name, **kwargs):
        """
        Associate a sponsor with this bill.

        :param type: the type of sponsorship, e.g. 'primary', 'cosponsor'
        :param name: the name of the sponsor as provided by the state
        """
        if 'chamber' not in kwargs:
            kwargs['chamber'] = self['chamber']

        self['sponsors'].append(dict(type=type, name=name, **kwargs))

    def add_document(self, name, url, **kwargs):
        """
        Add a document or media item that is related to the bill.
        Use this method to add documents such as Fiscal Notes, Analyses,
        Amendments, or public hearing recordings.

        :param name: a name given to the document, e.g.
                     'Fiscal Note for Amendment LCO 6544'
        :param url: link to location of document or file


        If multiple formats of a document are provided, a good rule of
        thumb is to prefer text, followed by html, followed by pdf/word/etc.
        """
        self['documents'].append(dict(name=name, url=url, **kwargs))

    def add_version(self, name, url, **kwargs):
        """
        Add a version of the text of this bill.

        :param name: a name given to this version of the text, e.g.
                     'As Introduced', 'Version 2', 'As amended', 'Enrolled'
        :param url: the location of this version on the state's legislative
                    website.

        If multiple formats are provided, a good rule of thumb is to
        prefer text, followed by html, followed by pdf/word/etc.
        """
        self['versions'].append(dict(name=name, url=url, **kwargs))

    def add_action(self, actor, action, date, **kwargs):
        """
        Add an action that was performed on this bill.

        :param actor: a string representing who performed the action.
          If the action is associated with one of the chambers this
          should be 'upper' or 'lower'. Alternatively, this could be
          the name of a committee, a specific legislator, or an outside
          actor such as 'Governor'.
        :param action: a string representing the action performed, e.g.
                       'Introduced', 'Signed by the Governor', 'Amended'
        :param date: the date/time this action was performed.
        """

        if not 'type' in kwargs or not kwargs['type']:
            kwargs['type'] = ['other']
        elif isinstance(kwargs['type'], basestring):
            kwargs['type'] = [kwargs['type']]
        elif not isinstance(kwargs['type'], list):
            kwargs['type'] = list(kwargs['type'])

        self['actions'].append(dict(actor=actor, action=action,
                                    date=date, **kwargs))

    def add_vote(self, vote):
        """
        Associate a :class:`~fiftystates.scrape.votes.Vote` object with this
        bill.
        """
        self['votes'].append(vote)

    def add_title(self, title):
        """
        Associate an alternate title with this bill.
        """
        self['alternate_titles'].append(title)
