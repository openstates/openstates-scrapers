import datetime
import lxml.html
import os
import re
from collections import defaultdict

import scrapelib

from billy.scrape.utils import convert_pdf
from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote

motion_classifiers = {
    '(Assembly|Senate)( substitute)? amendment': 'amendment',
    'Report (passage|concurrence)': 'passage',
    'Report (adoption|introduction and adoption) of Senate( Substitute)? Amendment': 'amendment',
    'Report Assembly( Substitute)? Amendment': 'amendment',
    'Read a third time': 'passage',
    'Adopted': 'passage'
}

action_classifiers = {
    '(Senate|Assembly)( substitute)? amendment .* offered': 'amendment:introduced',
    '(Senate|Assembly)( substitute)? amendment .* rejected': 'amendment:failed',
    '(Senate|Assembly)( substitute)? amendment .* adopted': 'amendment:passed',
    '(Senate|Assembly)( substitute)? amendment .* laid on table': 'amendment:tabled',
    '(Senate|Assembly)( substitute)? amendment .* withdrawn': 'amendment:withdrawn',
    'Report (passage|concurrence).* recommended': 'committee:passed:favorable',
    'Report approved by the Governor': 'governor:signed',
    '.+ (withdrawn|added) as a co(author|sponsor)': 'other',
    'R(ead (first time )?and r)?eferred to committee': 'committee:referred',
    'Read a third time and (passed|concurred)': 'bill:passed',
    'Adopted': 'bill:passed',
    'Presented to the Governor': 'governor:received',
    'Introduced by': 'bill:introduced',
    'Read a second time': 'bill:reading:2',
}


class WIBillScraper(BillScraper):
    jurisdiction = 'wi'

    def scrape_subjects(self, year, site_id):
        last_url = None
        next_url = 'http://docs.legis.wisconsin.gov/%s/related/subject_index/index/' % year

        # if you visit this page in your browser it is infinite-scrolled
        # but if you disable javascript you'll see the 'Down' links
        # that we use to scrape the data

        self.subjects = defaultdict(list)

        while last_url != next_url:
            html = self.get(next_url).text
            doc = lxml.html.fromstring(html)
            doc.make_links_absolute(next_url)

            last_url = next_url
            # get the 'Down' url
            next_url = doc.xpath('//a[text()="Down"]/@href')[0]

            # slug is upper case in links for special sessions
            if site_id != 'reg':
                site_id = site_id.upper()
            a_path = '/document/session/%s/%s/' % (year, site_id)

            # find all bill links to bills in this session
            for bill_a in doc.xpath('//a[contains(@href, "%s")]' % a_path):
                bill_id = bill_a.text_content().split()[-1]

                # subject is in the immediately preceding span
                preceding_subject = bill_a.xpath(
                    './preceding::div[contains(@class,"qsSubject")]/text()')
                # there wasn't a subject get the one from end of the prior page
                if not preceding_subject:
                    preceding_subject = last_subject[0]
                else:
                    preceding_subject = preceding_subject[-1]
                preceding_subject = preceding_subject.replace(u'\xe2\x80\x94',
                                                              '')
                self.subjects[bill_id].append(preceding_subject)

            # last subject on the page, in case we get a bill_id on next page
            last_subject_div = doc.xpath(
                '//div[contains(@class,"qsSubject")]/text()')
            if last_subject_div:
                last_subject = last_subject_div[0]


    def scrape(self, chamber, session):
        # get year
        for t in self.metadata['terms']:
            if session in t['sessions']:
                year = t['name'][0:4]
                break

        site_id = self.metadata['session_details'][session].get('site_id',
                                                                'reg')
        chamber_slug = {'upper': 'sen', 'lower': 'asm'}[chamber]

        self.scrape_subjects(year, site_id)

        types = ('bill', 'joint_resolution', 'resolution')

        for type in types:
            url = 'http://docs.legis.wisconsin.gov/%s/proposals/%s/%s/%s' % (
                year, site_id, chamber_slug, type)

            self.scrape_bill_list(chamber, session, url)

    def scrape_bill_list(self, chamber, session, url):
        if 'joint_resolution' in url:
            bill_type = 'joint resolution'
        elif 'resolution' in url:
            bill_type = 'resolution'
        elif 'bill' in url:
            bill_type = 'bill'

        try:
            data = self.get(url).text
        except scrapelib.HTTPError:
            self.warning('skipping URL %s' % url)
            return
        doc = lxml.html.fromstring(data)
        doc.make_links_absolute(url)
        bill_list = doc.xpath('//ul[@class="infoLinks"]/li/div[@class="row-fluid"]')
        for b in bill_list:
            bill_url = b.xpath('./div[@class="span3"]/a/@href')[0]
            bill_id = bill_url.rsplit('/', 1)[-1]
            bill_id = bill_id.upper()

            title = b.xpath('./div[@class="span6"]/text()')[0].replace(' - Relating to: ', '').strip()

            bill = Bill(session, chamber, bill_id, title,
                        type=bill_type)
            bill['subjects'] = list(set(self.subjects[bill_id]))
            self.scrape_bill_history(bill, bill_url)

    def scrape_bill_history(self, bill, url):
        body = self.get(url).text
        doc = lxml.html.fromstring(body)
        doc.make_links_absolute(url)

        bill['status'] = doc.xpath('//div[@class="propStatus"]/h2/text()')[0]

        # add versions
        for a in doc.xpath('//ul[@class="docLinks"]/li//a'):
            # blank ones are PDFs that follow HTML
            if not a.text:
                continue
            elif ('Wisconsin Act' in a.text or
                  'Memo' in a.text or
                  'Government Accountability Board' in a.text or
                  'Redistricting Attachment' in a.text or
                  'Budget Index Report' in a.text or
                  'Veto Message' in a.text
                 ):
                bill.add_document(a.text, a.get('href'))
            elif ('Bill Text' in a.text or
                  'Resolution Text' in a.text or
                  'Enrolled Joint Resolution' in a.text or
                  'Engrossed Resolution' in a.text or
                  'Text as Enrolled' in a.text
                 ):

                bill.add_version(a.text, a.get('href'),
                                 on_duplicate="ingore", mimetype="text/html")

                pdf = a.xpath('following-sibling::span/a/@href')[0]
                bill.add_version(a.text, pdf,
                                 on_duplicate="ignore",
                                 mimetype="application/pdf")

            elif a.text in ('Amendments', 'Fiscal Estimates',
                            'Record of Committee Proceedings'):
                extra_doc_url = a.get('href')
                extra_doc = lxml.html.fromstring(self.get(extra_doc_url).text)
                extra_doc.make_links_absolute(extra_doc_url)
                for extra_a in extra_doc.xpath('//li//a'):
                    if extra_a.text:
                        bill.add_document(extra_a.text, extra_a.get('href'))
            else:
                self.warning('unknown document %s %s' % (bill['bill_id'],
                                                         a.text))

        # add actions (second history dl is the full list)
        hist_table = doc.xpath('//table[@class="history"]')[1]
        for row in hist_table.xpath('.//tr[@class="historyRow"]'):
            date_house, action_td, journal = row.getchildren()

            date, actor = date_house.text_content().split()
            date = datetime.datetime.strptime(date, '%m/%d/%Y')
            actor = {'Asm.': 'lower', 'Sen.': 'upper'}[actor]
            action = action_td.text_content()

            if 'Introduced by' in action:
                self.parse_sponsors(bill, action)

            # classify actions
            atype = 'other'
            for regex, type in action_classifiers.iteritems():
                if re.match(regex, action):
                    atype = type
                    break

            kwargs = {}

            if "committee:referred" in atype:
                kwargs['committees'] = re.sub(
                    'R(ead (first time )?and r)?eferred to committee',
                    '', action)

            bill.add_action(actor, action, date, atype, **kwargs)

            # if this is a vote, add a Vote to the bill
            if 'Ayes' in action:
                vote_url = action_td.xpath('a/@href')
                if vote_url:
                    self.add_vote(bill, actor, date, action, vote_url[0])

        bill.add_source(url)
        self.save_bill(bill)

    def parse_sponsors(self, bill, action):
        if ';' in action:
            lines = action.split(';')
        else:
            lines = [action]

        for line in lines:
            match = re.match(
                '(Introduced|Cosponsored) by (?:joint )?(Senator|Representative|committee|Joint Legislative Council|Law Revision Committee)s?(.*)',
                line)
            if not match:
                # So far, the only one that doens't match is
                # http://docs.legis.wisconsin.gov/2011/proposals/ab568
                # In the following format:
                # Introduced by Representatives Krusick and J. Ott, by ... ;
                match = re.match(
                    'Introduced by (Representatives|Senators) (.*),',
                    line
                )
                if not match:
                    # Nothing to do here :)
                    continue

                type  = "Introduced"
                title, names = match.groups()
                raise Exception("Foo")
            else:
                type, title, people = match.groups()

            if type == 'Introduced':
                sponsor_type = 'primary'
            elif type == 'Cosponsored':
                sponsor_type = 'cosponsor'

            if title == 'Senator':
                sponsor_chamber = 'upper'
            elif title == 'Representative':
                sponsor_chamber = 'lower'
            elif title == 'committee':
                sponsor_chamber = bill['chamber']
                people = 'Committee ' + people
            elif title in ('Joint Legislative Council',
                           'Law Revision Committee'):
                sponsor_chamber = bill['chamber']
                people = title

            for r in re.split(r'\sand\s|\,', people):
                if r.strip():
                    bill.add_sponsor(sponsor_type, r.strip(),
                                     chamber=sponsor_chamber)

    def add_vote(self, bill, chamber, date, text, url):
        votes = re.findall(r'Ayes,?[\s]?(\d+)[,;]\s+N(?:oes|ays),?[\s]?(\d+)', text)
        (yes, no) = int(votes[0][0]), int(votes[0][1])

        vtype = 'other'
        for regex, type in motion_classifiers.iteritems():
            if re.match(regex, text):
                vtype = type
                break

        v = Vote(chamber, date, text, yes > no, yes, no, 0, type=vtype)

        # fetch the vote itself
        if url:
            v.add_source(url)

            if 'av' in url:
                self.add_house_votes(v, url)
            elif 'sv' in url:
                self.add_senate_votes(v, url)

        # other count is brute forced
        v['other_count'] = len(v['other_votes'])
        v.validate()
        bill.add_vote(v)


    def add_senate_votes(self, vote, url):
        html = self.get(url).text
        doc = lxml.html.fromstring(html)

        # what to do with the pieces
        vfunc = None

        # a game of div-div-table
        for ddt in doc.xpath('//div/div/table'):
            text = ddt.text_content()
            if 'Wisconsin Senate' in text or 'SEQUENCE NO' in text:
                continue
            elif 'AYES -' in text:
                for name in text.split('\n\n\n\n\n')[1:]:
                    if name.strip() and 'AYES' not in name:
                        vote.yes(name.strip())
            elif 'NAYS -' in text:
                for name in text.split('\n\n\n\n\n')[1:]:
                    if name.strip() and 'NAYS' not in name:
                        vote.no(name.strip())
            elif 'NOT VOTING -' in text:
                for name in text.split('\n\n\n\n\n')[1:]:
                    if name.strip() and "NOT VOTING" not in name:
                        vote.other(name.strip())
            elif text.strip():
                raise ValueError('unexpected block in vote')

    def add_house_votes(self, vote, url):
        html = self.get(url).text
        doc = lxml.html.fromstring(html)

        header_td = doc.xpath('//td[@align="center"]')[0].text_content()
        ayes_nays = re.findall('AYES - (\d+) .*? NAYS - (\d+)', header_td)
        vote['yes_count'] = int(ayes_nays[0][0])
        vote['no_count'] = int(ayes_nays[0][1])

        for td in doc.xpath('//td[@width="120"]'):
            name = td.text_content()
            if name == 'NAME':
                continue
            for vote_td in td.xpath('./preceding-sibling::td'):
                if vote_td.text_content() == 'Y':
                    vote.yes(name)
                elif vote_td.text_content() == 'N':
                    vote.no(name)
                elif vote_td.text_content() == 'NV':
                    vote.other(name)
