import re
import datetime
import lxml.html

import scrapelib

from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote

def extract_int(text):
    return int(text.replace(u'\xc2', '').strip())

def convert_date(text):
    short_date = re.findall('\d{1,2}-\d{1,2}-\d{2}', text)
    if short_date:
        return datetime.datetime.strptime(short_date[0], '%m-%d-%y')

    try:
        return datetime.datetime.strptime(text, '%A, %B %d, %Y')
    except ValueError:
        return None


class DCBillScraper(BillScraper):
    state = 'dc'

    def scrape_bill(self, bill):
        bill_url = 'http://www.dccouncil.washington.dc.us/lims/legislation.aspx?LegNo=' + bill['bill_id']

        bill.add_source(bill_url)

        with self.urlopen(bill_url) as bill_html:
            doc = lxml.html.fromstring(bill_html)
            doc.make_links_absolute(bill_url)

            # get versions
            for link in doc.xpath('//a[starts-with(@id, "DocumentRepeater")]'):
                bill.add_version(link.text, link.get('href'))

            # sponsors
            introduced_by = doc.get_element_by_id('IntroducedBy').text
            if introduced_by:
                for sponsor in introduced_by.split(', '):
                    bill.add_sponsor('primary', sponsor.strip())

            requested_by = doc.get_element_by_id('RequestedBy').text
            if requested_by:
                bill.add_sponsor('requestor', requested_by.strip())

            cosponsored_by = doc.get_element_by_id('CoSponsoredBy').text
            if cosponsored_by:
                for cosponsor in cosponsored_by.split(','):
                    bill.add_sponsor('cosponsor', cosponsor.strip())

            # actions
            actions = (
                ('Introduction', 'DateIntroduction', 'bill:introduced'),
                ('Committee Action', 'DateCommitteeAction', 'other'),
                ('First Vote', 'DateFirstVote', 'bill:reading:1'),
                ('Final Vote', 'DateFinalVote', 'bill:reading:3'),
                ('Third Vote', 'DateThirdVote', ['bill:reading:3']),
                ('Reconsideration', 'DateReconsideration', 'other'),
                ('Transmitted to Mayor', 'DateTransmittedMayor', 'governor:received'),
                ('Signed by Mayor', 'DateSigned', 'governor:signed'),
                ('Returned by Mayor', 'DateReturned', 'other'),
                ('Veto Override', 'DateOverride', 'bill:veto_override:passed'),
                ('Enacted', 'DateEnactment', 'other'),
                ('Vetoed by Mayor', 'DateVeto', 'governor:vetoed'),
                ('Transmitted to Congress', 'DateTransmittedCongress', 'other'),
                ('Re-transmitted to Congress', 'DateReTransmitted', 'other'),
            )

            subactions = (
                ('WITHDRAWN BY', 'Withdrawn', 'bill:withdrawn'),
                ('TABLED', 'Tabled', 'other'),
                ('DEEMED APPROVED', 'Deemed approved without council action', 'bill:passed'),
                ('DEEMED DISAPPROVED', 'Deemed disapproved without council action', 'bill:failed'),
            )

            for action, elem_id, atype in actions:
                date = doc.get_element_by_id(elem_id).text
                if date:

                    # check if the action starts with a subaction prefix
                    for prefix, sub_action, subatype in subactions:
                        if date.startswith(prefix):
                            date = convert_date(date)
                            if date:
                                bill.add_action('upper', sub_action, date,
                                                type=subatype)
                            break

                    # actions that mean nothing happened
                    else:
                        if date not in ('Not Signed', 'NOT CONSIDERED',
                                      'NOTCONSIDERED'):
                            actor = ('mayor' if action.endswith('by Mayor')
                                     else 'upper')
                            date = convert_date(date)
                            if not isinstance(date, datetime.datetime):
                                self.warning('could not convert %s %s [%s]' %
                                             (action, date, bill['bill_id']))
                            else:
                                bill.add_action(actor, action, date, type=atype)

            # votes
            vote_tds = doc.xpath('//td[starts-with(@id, "VoteTypeRepeater")]')
            for td in vote_tds:
                vote_type = td.text
                vote_type_id = re.search(r"LoadVotingInfo\(this\.id, '(\d)'",
                                         td.get('onclick')).groups()[0]
                # some votes randomly break
                try:
                    self.scrape_vote(bill, vote_type_id, vote_type)
                except scrapelib.HTTPError as e:
                    self.warning(str(e))

        bill['actions'] = sorted(bill['actions'], key=lambda b:b['date'])
        self.save_bill(bill)


    def scrape_vote(self, bill, vote_type_id, vote_type):
        base_url = 'http://www.dccouncil.washington.dc.us/lims/voting.aspx?VoteTypeID=%s&LegID=%s'
        url = base_url % (vote_type_id, bill['bill_id'])

        with self.urlopen(url) as html:
            doc = lxml.html.fromstring(html)

            vote_date = convert_date(doc.get_element_by_id('VoteDate').text)

            # check if voice vote / approved boxes have an 'x'
            voice = (doc.xpath('//span[@id="VoteTypeVoice"]/b/text()')[0] ==
                     'x')
            passed = (doc.xpath('//span[@id="VoteResultApproved"]/b/text()')[0]
                      == 'x')

            yes_count = extract_int(doc.xpath(
                '//span[@id="VoteCount1"]/b/text()')[0])
            no_count = extract_int(doc.xpath(
                '//span[@id="VoteCount2"]/b/text()')[0])
            # every now and then this actually drops below 0 (error in count)
            other_count = max(13 - (yes_count+no_count), 0)

            vote = Vote('upper', vote_date, vote_type, passed, yes_count,
                        no_count, other_count, voice_vote=voice)

            vote.add_source(url)

            # members are only text on page in a <u> tag
            for member_u in doc.xpath('//u'):
                member = member_u.text
                vote_text = member_u.xpath('../../i/text()')[0]
                if 'Yes' in vote_text:
                    vote.yes(member)
                elif 'No' in vote_text:
                    vote.no(member)
                else:
                    vote.other(member)
        bill.add_vote(vote)

    def scrape(self, chamber, session):
        self.validate_session(session)

        # no lower chamber
        if chamber == 'lower':
            return

        url = 'http://www.dccouncil.washington.dc.us/lims/print/list.aspx?FullPage=True&Period=' + session

        with self.urlopen(url) as html:
            doc = lxml.html.fromstring(html)
            rows = doc.xpath('//table/tr')
            # skip first row
            for row in rows[1:]:
                bill_id, title, _ = row.xpath('td/text()')
                title = title.replace(u'\xe2\x80\x99', "'")  # smart apostrophe

                if bill_id.startswith('B'):
                    type = 'bill'
                elif bill_id.startswith('CER'):
                    type = 'resolution'
                elif bill_id.startswith('CA'):
                    type = 'contract'
                elif bill_id.startswith('PR'):
                    type = 'resolution'
                # don't collect these
                elif (bill_id.startswith('GBM') or
                      bill_id.startswith('HFA') or
                      bill_id.startswith('IG')):
                    continue
                else:
                    # will break if type isn't known
                    raise ValueError('unknown bill type: %s' % bill_id)

                bill = Bill(session, 'upper', bill_id, title, type=type)
                self.scrape_bill(bill)
