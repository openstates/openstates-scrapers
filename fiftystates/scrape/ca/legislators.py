from fiftystates.scrape import NoDataForPeriod
from fiftystates.scrape.legislators import LegislatorScraper, Legislator
from fiftystates.scrape.ca import metadata
from fiftystates.scrape.ca.models import CALegislator

from sqlalchemy.orm import sessionmaker, relation, backref
from sqlalchemy import create_engine


class CALegislatorScraper(LegislatorScraper):
    state = 'ca'

    def __init__(self, metadata, host='localhost', user='', pw='',
                 db='capublic', **kwargs):
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

    def scrape(self, chamber, term):
        self.validate_term(term)

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

            full_name = legislator.legislator_name.decode('utf8')
            first_name = legislator.first_name.decode('utf8') or ''
            last_name = legislator.last_name.decode('utf8') or ''
            middle_name = legislator.middle_initial.decode('utf8') or ''
            suffixes = legislator.name_suffix.decode('utf8') or ''

            leg = Legislator(term, chamber, district, full_name,
                             first_name=first_name, last_name=last_name,
                             middle_name=middle_name, party=party,
                             suffixes=suffixes)
            self.save_legislator(leg)
