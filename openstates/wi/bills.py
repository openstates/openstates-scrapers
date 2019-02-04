import re
import pytz
import datetime
from collections import defaultdict

import lxml.html
import scrapelib
from pupa.scrape import Scraper, Bill, VoteEvent

from .common import SESSION_TERMS, SESSION_SITE_IDS

motion_classifiers = {
    '(Assembly|Senate)( substitute)? amendment': 'amendment',
    'Report (passage|concurrence)': 'passage',
    'Report (adoption|introduction and adoption) of Senate( Substitute)? Amendment': 'amendment',
    'Report Assembly( Substitute)? Amendment': 'amendment',
    'Read a third time': 'passage',
    'Adopted': 'passage',
}

action_classifiers = {
    '(Senate|Assembly)( substitute)? amendment .* offered': 'amendment-introduction',
    '(Senate|Assembly)( substitute)? amendment .* rejected': 'amendment-failure',
    '(Senate|Assembly)( substitute)? amendment .* adopted': 'amendment-passage',
    '(Senate|Assembly)( substitute)? amendment .* laid on table': 'amendment-deferral',
    '(Senate|Assembly)( substitute)? amendment .* withdrawn': 'amendment-withdrawal',
    'Report (passage|concurrence).* recommended': 'committee-passage-favorable',
    'Report approved by the Governor with partial veto': 'executive-veto-line-item',
    'Report approved by the Governor on': 'executive-signature',
    'Report vetoed by the Governor': 'executive-veto',
    '.+ (withdrawn|added) as a co(author|sponsor)': None,
    'R(ead (first time )?and r)?eferred to committee': 'referral-committee',
    'Read a third time and (passed|concurred)': 'passage',
    'Adopted': 'passage',
    'Presented to the Governor': 'executive-receipt',
    'Introduced by': 'introduction',
    'Read a second time': 'reading-2',
}

TIMEZONE = pytz.timezone('US/Central')


class WIBillScraper(Scraper):
    subjects = defaultdict(list)

    def scrape_subjects(self, year, site_id):
        last_url = None
        next_url = 'http://docs.legis.wisconsin.gov/%s/related/subject_index/index/' % year
        last_subject = None

        # if you visit this page in your browser it is infinite-scrolled
        # but if you disable javascript you'll see the 'Down' links
        # that we use to scrape the data

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

    def scrape(self, chamber=None, session=None):
        if session is None:
            session = self.latest_session()
            self.info('no session specified, using %s', session)

        chambers = [chamber] if chamber is not None else ['upper', 'lower']

        for chamber in chambers:
            yield from self.scrape_chamber(chamber, session)

    def scrape_chamber(self, chamber, session):
        # get year
        year = SESSION_TERMS[session][0:4]
        site_id = SESSION_SITE_IDS.get(session, 'reg')
        chamber_slug = {'upper': 'sen', 'lower': 'asm'}[chamber]

        if not self.subjects:
            self.scrape_subjects(year, site_id)

        types = ('bill', 'joint_resolution', 'resolution')

        for type in types:
            url = 'http://docs.legis.wisconsin.gov/%s/proposals/%s/%s/%s' % (
                year, site_id, chamber_slug, type)

            yield from self.scrape_bill_list(chamber, session, url)

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

            title = b.xpath(
                './div[@class="span6"]/text()'
            )[0].replace(' - Relating to: ', '').strip()

            bill = Bill(
                bill_id,
                legislative_session=session,
                title=title,
                chamber=chamber,
                classification=bill_type,
            )
            bill.subject = list(set(self.subjects[bill_id]))
            yield from self.scrape_bill_history(bill, bill_url, chamber)

            yield bill

    def scrape_bill_history(self, bill, url, chamber):
        body = self.get(url).text
        doc = lxml.html.fromstring(body)
        doc.make_links_absolute(url)

        bill.extras['status'] = doc.xpath('//div[@class="propStatus"]/h2/text()')[0]

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
                    'Veto Message' in a.text):
                bill.add_document_link(a.text, a.get('href'), on_duplicate='ignore')
            elif ('Bill Text' in a.text or
                    'Resolution Text' in a.text or
                    'Enrolled Joint Resolution' in a.text or
                    'Engrossed Resolution' in a.text or
                    'Text as Enrolled' in a.text):
                bill.add_version_link(a.text, a.get('href'), media_type='text/html',
                                      on_duplicate='ignore')

                pdf = a.xpath('following-sibling::span/a/@href')[0]
                bill.add_version_link(a.text, pdf, media_type='application/pdf',
                                      on_duplicate='ignore')

            elif a.text in ('Amendments', 'Fiscal Estimates',
                            'Record of Committee Proceedings'):
                extra_doc_url = a.get('href')
                extra_doc = lxml.html.fromstring(self.get(extra_doc_url).text)
                extra_doc.make_links_absolute(extra_doc_url)
                for extra_a in extra_doc.xpath('//ul[@class="docLinks"]/li//a'):
                    if extra_a.text:
                        bill.add_document_link(extra_a.text, extra_a.get('href'))
            else:
                self.warning('unknown document %s %s' % (bill.identifier,
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
                self.parse_sponsors(bill, action, chamber)

            # classify actions
            atype = None
            for regex, type in action_classifiers.items():
                if re.match(regex, action):
                    atype = type
                    break

            kwargs = {}
            if "referral-committee" in (atype or ''):
                kwargs['related_entities'] = [{
                    'entity_type': 'committee',
                    'name': re.sub('R(ead (first time )?and r)?eferred to committee',
                                   '', action)
                }]

            bill.add_action(action, TIMEZONE.localize(date), chamber=actor, classification=atype)

            # if this is a vote, add a Vote to the bill
            if 'Ayes' in action:
                vote_url = action_td.xpath('a/@href')
                if 'committee' in action.lower():
                    vote_url = journal.xpath('a/@href')
                if vote_url:
                    yield self.add_vote(bill, actor, date, action, vote_url[0])

        bill.add_source(url)

    def parse_sponsors(self, bill, action, chamber):
        if ';' in action:
            lines = action.split(';')
        else:
            lines = [action]

        for line in lines:
            match = re.match(
                '(Introduced|Cosponsored) by (?:joint )?(Senator|Representative|committee|Joint Legislative Council|Law Revision Committee)s?(.*)',  # noqa
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

                type = "Introduced"
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
                sponsor_chamber = chamber
                people = 'Committee ' + people
            elif title in ('Joint Legislative Council',
                           'Law Revision Committee'):
                sponsor_chamber = chamber
                people = title

            for r in re.split(r'\sand\s|\,', people):
                if r.strip():
                    bill.add_sponsorship(
                        r.strip(),
                        chamber=sponsor_chamber,
                        classification=sponsor_type,
                        primary=sponsor_type == 'primary',
                        entity_type='person',
                    )

    def add_vote(self, bill, chamber, date, text, url):
        votes = re.findall(r'Ayes,?[\s]?(\d+)[,;]\s+N(?:oes|ays),?[\s]?(\d+)', text)
        yes, no = int(votes[0][0]), int(votes[0][1])

        vtype = 'other'
        for regex, type in motion_classifiers.items():
            if re.match(regex, text):
                vtype = type
                break

        v = VoteEvent(
            chamber=chamber,
            start_date=TIMEZONE.localize(date),
            motion_text=text,
            result='pass' if yes > no else 'fail',
            classification=vtype,
            bill=bill,
        )
        v.pupa_id = url.split('/')[-1]
        v.set_count('yes', yes)
        v.set_count('no', no)

        # fetch the vote itself
        if url:
            v.add_source(url)

            if 'av' in url:
                self.add_house_votes(v, url)
            elif 'sv' in url:
                self.add_senate_votes(v, url)

        return v

    def add_senate_votes(self, vote, url):
        try:
            html = self.get(url).text
        except scrapelib.HTTPError:
            self.warning('No Senate Votes found for %s' % url)
            return

        doc = lxml.html.fromstring(html)
        trs = doc.xpath('//table[@class="senate"]/tbody/tr[./td[@class="vote-count"]]')

        motion = doc.xpath('//div/p/b/text()')[1]
        vote.motion_text = motion

        vote_types = ['yes', 'no', 'not voting']
        vote_counts = {}  # Vote counts for yes, no, other
        name_counts = {}

        for index, tr in enumerate(trs):

            vote_type = vote_types[index]
            names = tr.xpath('.//table//td/text()')
            vote_count = int(tr.xpath('./td/text()')[0].split('-')[1])
            vote_counts[vote_type] = vote_count
            name_counts[vote_type] = len(names)

            for name in names:
                vote.vote(vote_type, name.strip())

        for vote_type in vote_types:
            vote.set_count(vote_type, vote_counts[vote_type])

        if name_counts != vote_counts:
            raise ValueError("Vote Count and number of Names don't match")

    def add_house_votes(self, vote, url):
        try:
            html = self.get(url).content
        except scrapelib.HTTPError:
            self.warning('No House Votes found for %s' % url)
            return

        doc = lxml.html.fromstring(html)
        motion = doc.xpath('//div/p/b/text()')[1]
        vote.motion_text = motion

        header_td = doc.xpath('//div/p[text()[contains(., "AYES")]]')[0].text_content()
        vote_counts = re.findall(r'AYES - (\d+).*NAYS - (\d+).*NOT VOTING - (\d+).*', header_td)

        vote.set_count('yes', int(vote_counts[0][0]))
        vote.set_count('no', int(vote_counts[0][1]))
        vote.set_count('not voting', int(vote_counts[0][2]))

        yes_names_count = 0
        no_names_count = 0

        for td in doc.xpath('//tbody/tr/td[4]'):
            name = td.text_content()
            for vote_td in td.xpath('./preceding-sibling::td'):
                if vote_td.text_content() == 'Y':
                    vote.vote('yes', name)
                    yes_names_count += 1
                elif vote_td.text_content() == 'N':
                    vote.vote('no', name)
                    no_names_count += 1
                elif vote_td.text_content() == 'NV':
                    vote.vote('not voting', name)

        if yes_names_count != int(vote_counts[0][0]):
            raise ValueError("Yes votes and number of Names doesn't match")
        if no_names_count != int(vote_counts[0][1]):
            raise ValueError("No votes and number of Names doesn't match")
