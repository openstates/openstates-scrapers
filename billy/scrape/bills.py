import os
import json

from billy.scrape import Scraper, SourcedObject, JSONDateEncoder


class BillScraper(Scraper):

    scraper_type = 'bills'

    def _get_schema(self):
        schema_path = os.path.join(os.path.split(__file__)[0],
                                   '../schemas/bill.json')
        schema = json.load(open(schema_path))
        schema['properties']['session']['enum'] = self.all_sessions()
        return schema

    def scrape(self, chamber, session):
        """
        Grab all the bills for a given chamber and session. Must be
        overridden by subclasses.

        Should raise a :class:`NoDataForPeriod` exception if it is
        not possible to scrape bills for the given session.
        """
        raise NotImplementedError('BillScrapers must define a scrape method')

    def save_bill(self, bill):
        """
        Save a scraped :class:`~billy.scrape.bills.Bill` object.

        Should be called after all data for the given bill has been collected.
        """
        self.log("save_bill %s %s: %s" % (bill['chamber'],
                                          bill['session'],
                                          bill['bill_id']))
        self.save_object(bill)


class Bill(SourcedObject):
    """
    Object representing a piece of legislation.

    See :class:`~billy.scrape.SourcedObject` for notes on
    extra attributes/fields.
    """

    def __init__(self, session, chamber, bill_id, title, **kwargs):
        """
        Create a new :obj:`Bill`.

        :param session: the session in which the bill was introduced.
        :param chamber: the chamber in which the bill was introduced:
          either 'upper' or 'lower'
        :param bill_id: an identifier assigned to this bill by the legislature
          (should be unique within the context of this chamber/session)
          e.g.: 'HB 1', 'S. 102', 'H.R. 18'
        :param title: a title or short description of this bill provided by
          the official source

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
        :param name: the name of the sponsor as provided by the official source
        """
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
        :param url: the location of this version on the legislative website.

        If multiple formats are provided, a good rule of thumb is to
        prefer text, followed by html, followed by pdf/word/etc.
        """
        self['versions'].append(dict(name=name, url=url, **kwargs))

    def add_action(self, actor, action, date, type=None, **kwargs):
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
        :param type: a type classification for this action
        """

        if not type:
            type = ['other']
        elif isinstance(type, basestring):
            type = [type]
        elif not isinstance(type, list):
            type = list(type)

        self['actions'].append(dict(actor=actor, action=action,
                                    date=date, type=type,
                                    **kwargs))

    def add_vote(self, vote):
        """
        Associate a :class:`~billy.scrape.votes.Vote` object with this
        bill.
        """
        self['votes'].append(vote)

    def add_title(self, title):
        """
        Associate an alternate title with this bill.
        """
        self['alternate_titles'].append(title)

    def get_filename(self):
        filename = "%s_%s_%s.json" % (self['session'], self['chamber'],
                                      self['bill_id'])
        return filename.encode('ascii', 'replace')
