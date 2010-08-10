from fiftystates.scrape import NoDataForPeriod
from fiftystates.scrape.legislators import LegislatorScraper, Legislator
from fiftystates.scrape.ca import metadata
from fiftystates.scrape.ca.models import CALegislator

from sqlalchemy.orm import sessionmaker, relation, backref
from sqlalchemy import create_engine


class CALegislatorScraper(LegislatorScraper):
    state = 'ca'

    def __init__(self, host='localhost', user='', pw='', db='capublic',
                 **kwargs):
        super(CALegislatorScraper, self).__init__(metadata, **kwargs)
        if user and pw:
            conn_str = 'mysql://%s:%s@' % (user, pw)
        else:
            conn_str = 'mysql://'
        conn_str = '%s%s/%s?charset=utf8&unix_socket=/tmp/mysql.sock' % (
            conn_str, host, db)
        self.engine = create_engine(conn_str)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()

    def scrape(self, chamber, year):
        term = "%s%d" % (year, int(year) + 1)
        found = False
        for t in metadata['terms']:
            if t['name'] == term:
                found = True
                break
        if not found:
            raise NoDataForPeriod(year)

        if chamber == 'upper':
            house_type = 'S'
        else:
            house_type = 'A'

        legislators = self.session.query(CALegislator).filter_by(
            session_year=term).filter_by(
            house_type=house_type)

        for legislator in legislators:
            if legislator.legislator_name.endswith('Vacancy'):
                continue

            district = legislator.district[2:].lstrip('0')
            party = legislator.party

            if party == 'DEM':
                party = 'Democrat'
            elif party == 'REP':
                party = 'Republican'

            leg = Legislator(term, chamber, district,
                             legislator.legislator_name,
                             first_name=legislator.first_name or '',
                             last_name=legislator.last_name or '',
                             middle_name=legislator.middle_initial or '',
                             party=party,
                             suffixes=legislator.name_suffix)
            self.save_legislator(leg)
