import os
import json

from billy.scrape import Scraper, SourcedObject, JSONDateEncoder


class LegislatorScraper(Scraper):

    scraper_type = 'legislators'

    def _get_schema(self):
        schema_path = os.path.join(os.path.split(__file__)[0],
                                   '../schemas/person.json')
        schema = json.load(open(schema_path))
        terms = [t['name'] for t in self.metadata['terms']]
        schema['properties']['roles']['items']['properties']['term']['enum'] = terms
        return schema

    def scrape(self, chamber, term):
        """
        Grab all the legislators who served in a given term. Must be
        overridden by subclasses.

        Should raise a :class:`NoDataForPeriod` exception if the year is
        invalid.
        """
        raise NotImplementedError('LegislatorScrapers must define a '
                                  'scrape method')

    def save_person(self, person):
        """
        Save a scraped :class:`~billy.scrape.legislators.Person` object.
        Only call after all data for the given person has been collected.

        Should be used for non-legislator people (e.g. Governor, Lt. Gov).
        To add :class:`~billy.scrape.legislators.Legislator` objects call
        :meth:`save_legislator`.
        """
        self.log("save_person: %s" % person['full_name'])
        self.save_object(person)

    def save_legislator(self, legislator):
        """
        Save a scraped :class:`~billy.scrape.legislators.Legislator`
        object.

        Only call after all data for the given legislator has been collected.
        """
        self.log("save_legislator: %s" % legislator['full_name'])
        self.save_object(legislator)

class Person(SourcedObject):
    def __init__(self, full_name, first_name='', last_name='',
                 middle_name='', **kwargs):
        """
        Create a Person.

        Note: the :class:`~billy.scrape.legislators.Legislator` class
        should be used when dealing with legislators.

        :param full_name: the person's full name
        :param first_name: the first name of this legislator (if specified)
        :param last_name: the last name of this legislator (if specified)
        :param middle_name: a middle name or initial of this legislator
          (if specified)
        """
        super(Person, self).__init__('person', **kwargs)
        self['full_name'] = full_name
        self['first_name'] = first_name
        self['last_name'] = last_name
        self['middle_name'] = middle_name
        self['suffixes'] = kwargs.get('suffixes', '')
        self['roles'] = []

    def add_role(self, role, term, start_date=None, end_date=None,
                 **kwargs):
        """
        If ``start_date`` or ``end_date`` are ``None``, they will default
        to the start/end date of the given term.

        Examples:

        leg.add_role('member', term='2009', chamber='upper',
                     party='Republican', district='10th')
        """
        self['roles'].append(dict(role=role, term=term,
                                  start_date=start_date,
                                  end_date=end_date, **kwargs))

    def get_filename(self):
        role = self['roles'][0]
        filename = "%s_%s.json" % (role['term'], self['full_name'])
        return filename.encode('ascii', 'replace')


class Legislator(Person):
    def __init__(self, term, chamber, district, full_name,
                 first_name='', last_name='', middle_name='',
                 party='', **kwargs):
        """
        Create a Legislator.

        :param term: the term for this legislator
        :param chamber: the chamber in which this legislator served,
          'upper' or 'lower'
        :param district: the district this legislator is representing, as given
           e.g. 'District 2', '7th', 'District C'.
        :param full_name: the full name of this legislator
        :param first_name: the first name of this legislator (if specified)
        :param last_name: the last name of this legislator (if specified)
        :param middle_name: a middle name or initial of this legislator
          (if specified)
        :param party: the party this legislator belongs to (if specified)

        .. note::

            please only provide the first_name, middle_name and last_name
            parameters if they are listed on the official web site; do not
            try to split the legislator's full name into components yourself.
        """
        super(Legislator, self).__init__(full_name, first_name,
                                         last_name, middle_name,
                                         **kwargs)
        #self['type'] = 'legislator'
        self.add_role('member', term, chamber=chamber, district=district,
                      party=party)

    def get_filename(self):
        role = self['roles'][0]
        filename = "%s_%s_%s_%s.json" % (role['term'],
                                         role['chamber'],
                                         role['district'],
                                         self['full_name'])
        return filename.encode('ascii', 'replace')
