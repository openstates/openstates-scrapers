import re
import inspect

from openstates.utils import LXMLMixin

from .utils import Urls


class AssemblyBillPage(LXMLMixin):
    '''
    Adapted from an very weirdly overengineered solution that existed
    in this file beforehand. Retained in the interest of time, but the
    remnants of this solution needs to be factored out.

    Takes a bill and edits it in-place with the memo, summary, assembly
    floor votes from the assembly page.
    '''

    def __init__(self, scraper, session, bill, details):
        (senate_url, assembly_url, bill_chamber, bill_type, bill_id,
            title, bill_id_parts) = details

        self.bill = bill
        self.bill_id = bill_id
        # This works on the assumption that the metadata term ID is
        # only the start year.
        self.term_start_year = session.split('-')[0]

        self.letter, self.number, self.version = bill_id_parts
        self.shared_url = 'http://assembly.state.ny.us/leg/?default_fld='\
            '&bn={}&term={}'.format(self.bill_id, self.term_start_year)
        self.urls = Urls(scraper=scraper, urls={
            'assembly': assembly_url,
            'senate': senate_url})

    def _scrub_name(self, name):
        junk = [
            r'^Rules\s+',
            '\(2nd Vice Chairperson\)',
            '\(MS\)',
            'Assemblyman',
            'Assemblywoman',
            'Senator']
        for rgx in junk:
            name = re.sub(rgx, '', name, re.I)

        # Collapse whitespace.
        name = re.sub('\s+', ' ', name)
        return name.strip('(), ')

    def build(self):
        '''Run all the build_* functions.
        '''
        for name, member in inspect.getmembers(self):
            if inspect.ismethod(member):
                if name.startswith('_build_'):
                    member()
