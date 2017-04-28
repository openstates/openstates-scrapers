import re
import json
import datetime

import scrapelib
import lxml.html
from pupa.scrape import Scraper, Bill, VoteEvent

from . import ksapi


class KSBillScraper(Scraper):
    def scrape(self, chamber=None, session=None):
        if session is None:
            session = self.latest_session()
            self.info('no session specified, using %s', session)

        chambers = [chamber] if chamber is not None else ['upper', 'lower']

        for chamber in chambers:
            yield from self.scrape_chamber(chamber, session)

    def scrape_chamber(self, chamber, session):
        chamber_name = 'Senate' if chamber == 'upper' else 'House'
        chamber_letter = chamber_name[0]
        # perhaps we should save this data so we can make one request for both?
        bill_request = self.get(ksapi.url + 'bill_status/').text
        bill_request_json = json.loads(bill_request)
        bills = bill_request_json['content']
        for bill_data in bills:

            bill_id = bill_data['BILLNO']

            # filter other chambers
            if not bill_id.startswith(chamber_letter):
                continue

            if 'CR' in bill_id:
                btype = 'concurrent resolution'
            elif 'R' in bill_id:
                btype = 'resolution'
            elif 'B' in bill_id:
                btype = 'bill'

            title = bill_data['SHORTTITLE'] or bill_data['LONGTITLE']

            # main
            bill = Bill(
                bill_id,
                session,
                title,
                chamber=chamber,
                classification=btype,
            )
            bill.extras = {'status': bill_data['STATUS']}

            bill.add_source(ksapi.url + 'bill_status/' + bill_id.lower())

            if (bill_data['LONGTITLE'] and
                    bill_data['LONGTITLE'] != bill.title):
                bill.add_title(bill_data['LONGTITLE'])

            for sponsor in bill_data['SPONSOR_NAMES']:
                stype = ('primary' if len(bill_data['SPONSOR_NAMES']) == 1
                         else 'cosponsor')
                if sponsor:
                    bill.add_sponsorship(
                        name=sponsor,
                        entity_type='person',
                        primary=stype == 'primary',
                        classification=stype,
                    )

            # history is backwards
            for event in reversed(bill_data['HISTORY']):
                actor = ('upper' if event['chamber'] == 'Senate'
                         else 'lower')

                date = datetime.datetime.strptime(event['occurred_datetime'], "%Y-%m-%dT%H:%M:%S")
                # append committee names if present
                if 'committee_names' in event:
                    action = (event['status'] + ' ' +
                              ' and '.join(event['committee_names']))
                else:
                    action = event['status']

                if event['action_code'] not in ksapi.action_codes:
                    self.warning('unknown action code on %s: %s %s' %
                                 (bill_id, event['action_code'],
                                  event['status']))
                    atype = None
                else:
                    atype = ksapi.action_codes[event['action_code']]
                bill.add_action(
                    action, date.strftime('%Y-%m-%d'), chamber=actor, classification=atype)

            try:
                yield from self.scrape_html(bill, session)
            except scrapelib.HTTPError as e:
                self.warning('unable to fetch HTML for bill {0}'.format(
                    bill['bill_id']))

            yield bill

    def scrape_html(self, bill, session):
        meta = next(
            each for each in self.jurisdiction.legislative_sessions
            if each['identifier'] == session
        )
        slug = meta['_scraped_name']
        # we have to go to the HTML for the versions & votes
        base_url = 'http://www.kslegislature.org/li/%s/measures/' % slug
        if 'resolution' in bill.classification:
            base_url = 'http://www.kslegislature.org/li/%s/year1/measures/' % slug

        url = base_url + bill.identifier.lower() + '/'
        doc = lxml.html.fromstring(self.get(url).text)
        doc.make_links_absolute(url)

        bill.add_source(url)

        # versions & notes
        version_rows = doc.xpath('//tbody[starts-with(@id, "version-tab")]/tr')
        for row in version_rows:
            # version, docs, sn, fn
            tds = row.getchildren()
            title = tds[0].text_content().strip()
            doc_url = get_doc_link(tds[1])
            if doc_url:
                bill.add_version_link(title, doc_url, media_type='application/pdf')
            if len(tds) > 2:
                sn_url = get_doc_link(tds[2])
                if sn_url:
                    bill.add_document_link(
                        title + ' - Supplementary Note', sn_url, on_duplicate='ignore')
            if len(tds) > 3:
                if sn_url:
                    bill.add_document_link(title + ' - Fiscal Note', sn_url, on_duplicate='ignore')

        all_links = doc.xpath(
            "//table[@class='bottom']/tbody[@class='tab-content-sub']/tr/td/a/@href"
        )
        vote_members_urls = []
        for i in all_links:
            if "vote_view" in i:
                vote_members_urls.append(str(i))
        if len(vote_members_urls) > 0:
            for link in vote_members_urls:
                yield from self.parse_vote(bill, link)

        history_rows = doc.xpath('//tbody[starts-with(@id, "history-tab")]/tr')
        for row in history_rows:
            row_text = row.xpath('.//td[3]')[0].text_content()
            # amendments & reports
            amendment = get_doc_link(row.xpath('.//td[4]')[0])
            if amendment:
                if 'Motion to Amend' in row_text:
                    _, offered_by = row_text.split('Motion to Amend -')
                    amendment_name = 'Amendment ' + offered_by.strip()
                elif 'Conference committee report now available' in row_text:
                    amendment_name = 'Conference Committee Report'
                else:
                    amendment_name = row_text.strip()
                bill.add_document_link(amendment_name, amendment, on_duplicate='ignore')

    def parse_vote(self, bill, link):
        member_doc = lxml.html.fromstring(self.get(link).text)
        motion = member_doc.xpath("//div[@id='main_content']/h4/text()")
        opinions = member_doc.xpath("//div[@id='main_content']/h3/text()")
        if len(opinions) > 0:
            temp = opinions[0].split()
            vote_chamber = temp[0]
            vote_date = datetime.datetime.strptime(temp[-1], '%m/%d/%Y')
            vote_status = " ".join(temp[2:-2])
            vote_status = vote_status if vote_status.strip() else motion[0]
            vote_chamber = 'upper' if vote_chamber == 'Senate' else 'lower'

            for i in opinions:
                try:
                    count = int(i[i.find("(") + 1:i.find(")")])
                except:
                    pass
                if "yea" in i.lower():
                    yes_count = count
                elif "nay" in i.lower():
                    no_count = count
                elif "present" in i.lower():
                    p_count = count
                elif "absent" in i.lower():
                    a_count = count
            vote = VoteEvent(
                bill=bill,
                start_date=vote_date.strftime('%Y-%m-%d'),
                chamber=vote_chamber,
                motion_text=vote_status,
                result='pass' if yes_count > no_count else 'fail',
                classification='passage',
            )

            vote.set_count('yes', yes_count)
            vote.set_count('no', no_count)
            vote.set_count('abstain', p_count)
            vote.set_count('absent', a_count)

            vote.add_source(link)

            a_links = member_doc.xpath("//div[@id='main_content']/a/text()")
            for i in range(1, len(a_links)):
                if i <= yes_count:
                    vote.vote('yes', re.sub(',', '', a_links[i]).split()[0])
                elif no_count != 0 and i > yes_count and i <= yes_count + no_count:
                    vote.vote('no', re.sub(',', '', a_links[i]).split()[0])
                else:
                    vote.vote('other', re.sub(',', '', a_links[i]).split()[0])
            yield vote
        else:
            self.warning("No Votes for: %s", link)


def get_doc_link(elem):
    # try ODT then PDF
    link = elem.xpath('.//a[contains(@href, ".odt")]/@href')
    if link:
        return link[0]
    link = elem.xpath('.//a[contains(@href, ".pdf")]/@href')
    if link:
        return link[0]
