import re
import datetime
import urlparse

import lxml
from scrapelib import HTTPError
from billy.scrape import NoDataForPeriod
from billy.scrape.committees import CommitteeScraper, Committee

from . import utils

base_url = 'http://www.azleg.gov/'


class AZCommitteeScraper(CommitteeScraper):
    jurisdiction = 'az'

    def get_session_for_term(self, term):
        # ideally this should be either first or second regular session
        # and probably first and second when applicable
        for t in self.metadata['terms']:
            if t['name'] == term:
                session = t['sessions'][-1]
                if re.search('regular', session):
                    return session
                else:
                    return t['sessions'][0]

    def get_session_id(self, session):
        return self.metadata['session_details'][session]['session_id']

    def scrape(self, chamber, term):
        self.validate_term(term)
        session = self.get_session_for_term(term)
        try:
            session_id = self.get_session_id(session)
        except KeyError:
            raise NoDataForPeriod

        url = 'http://www.azleg.gov/StandingCom.asp'
        html = self.get(url).text
        doc = lxml.html.fromstring(html)

        chamber_name = dict(
            upper="Senate",
            lower="House of Representatives")[chamber]
        xpath = '//strong[contains(text(), "%s")]/../../following-sibling::tr/td'
        tds = doc.xpath(xpath % chamber_name)
        for td in tds:
            name = td.text_content().strip()
            source_url = td.xpath('a/@href')[0]
            query = urlparse.urlparse(source_url).query
            params = dict(urlparse.parse_qsl(query))
            c_id = params['Committee_ID']
            session_id = params['Session_ID']

            c = Committee(chamber, name, session=session, az_committee_id=c_id)

            c.add_source(source_url)
            #for some reason they don't always have any info on the committees'
            try:
                self.scrape_com_info(session, session_id, c_id, c)
            except HTTPError:
                pass

            if not c['members']:
                msg = 'No members found: not saving {committee}.'
                self.logger.warning(msg.format(**c))
                continue
            self.save_committee(c)

    def scrape_com_info(self, session, session_id, committee_id, committee):
        url = base_url + 'CommitteeInfo.asp?Committee_ID=%s&Session_ID=%s' % (committee_id,
                                                                    session_id)

        page = self.get(url).text
        committee.add_source(url)
        root = lxml.html.fromstring(page)
        p = '//table/tr/td[1]/a/ancestor::tr[1]'
        rows = root.xpath(p)
        #need to skip the first row cause its a link to the home page
        for row in rows[1:]:
            name = row[0].text_content().strip()
            role = row[1].text_content().strip()
            committee.add_member(name, role)

    def scrape_index(self, chamber, session, session_id, committee_type):
        url = base_url + 'xml/committees.asp?session=%s&type=%s' % (session_id,
                                                                 committee_type)
        page = self.get(url)
        root = etree.fromstring(page.content, etree.XMLParser(recover=True))

        body = '//body[@Body="%s"]/committee' % {'upper': 'S',
                                                 'lower': 'H'}[chamber]
        # TODO need to and make sure to add sub committees
        for com in root.xpath(body):
            c_id, name, short_name, sub = com.values()
            c = Committee(chamber, name, short_name=short_name,
                          session=session, az_committee_id=c_id)
            c.add_source(url)
            self.scrape_com_info(session, session_id, c_id, c)
            if c['members']:
                self.save_committee(c)
            else:
                msg = 'No members found: not saving {committee}.'
                self.logger.warning(msg.format(**c))

