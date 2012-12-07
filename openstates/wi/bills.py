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
        next_url = 'https://docs.legis.wisconsin.gov/%s/related/subject_index/index/' % year

        # if you visit this page in your browser it is infinite-scrolled
        # but if you disable javascript you'll see the 'Down' links
        # that we use to scrape the data

        self.subjects = defaultdict(list)

        while last_url != next_url:
            html = self.urlopen(next_url)
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
                    './preceding::span[@class="qs_subjecthead_"]/text()')
                # there wasn't a subject get the one from end of the prior page
                if not preceding_subject:
                    preceding_subject = last_subject[0]
                else:
                    preceding_subject = preceding_subject[-1]
                preceding_subject = preceding_subject.replace(u'\xe2\x80\x94',
                                                              '')
                self.subjects[bill_id].append(preceding_subject)

            # last subject on the page, in case we get a bill_id on next page
            last_subject_span = doc.xpath(
                '//span[@class="qs_subjecthead_"]/text()')
            if last_subject_span:
                last_subject = last_subject_span[0]


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
            data = self.urlopen(url)
        except scrapelib.HTTPError:
            self.warning('skipping URL %s' % url)
            return
        doc = lxml.html.fromstring(data)
        doc.make_links_absolute(url)
        links = doc.xpath('//li//a')
        for link in links:
            bill_url = link.get('href')
            bill_id = bill_url.rsplit('/', 1)[-1]

            title = link.tail.replace(' - Relating to: ', '').strip()

            bill = Bill(session, chamber, bill_id, title,
                        type=bill_type)
            bill['subjects'] = list(set(self.subjects[bill_id]))
            self.scrape_bill_history(bill, bill_url)

    def scrape_bill_history(self, bill, url):
        body = self.urlopen(url)
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
                bill.add_version(a.text, a.get('href'), mimetype="text/html")

                pdf = a.xpath('following-sibling::span/a/@href')[0]
                bill.add_version(a.text, pdf, mimetype="application/pdf")

            elif a.text in ('Amendments', 'Fiscal Estimates',
                            'Record of Committee Proceedings'):
                extra_doc_url = a.get('href')
                extra_doc = lxml.html.fromstring(self.urlopen(extra_doc_url))
                extra_doc.make_links_absolute(extra_doc_url)
                for extra_a in extra_doc.xpath('//li//a'):
                    if extra_a.text:
                        bill.add_document(extra_a.text, extra_a.get('href'))
            else:
                self.warning('unknown document %s %s' % (bill['bill_id'],
                                                         a.text))

        # add actions (second history dl is the full list)
        history_dl = doc.xpath('//dl[@class="history"]')[-1]
        for dt in history_dl.xpath('dt'):
            date = dt.text.strip()
            date = datetime.datetime.strptime(date, '%m/%d/%Y')
            actor = dt.xpath('abbr/text()')[0]
            actor = {'Asm.': 'lower', 'Sen.': 'upper'}[actor]
            # text is in the dd immediately following
            dd = dt.xpath('following-sibling::dd[1]')[0]
            action = dd.text_content()
            # get the journal number from the end of the line & strip it
            jspan = dd.xpath('string(.//span[@class="journal noprint"])')
            if jspan:
                action = action[:-len(jspan)]

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
                dd = dt.xpath('following-sibling::dd[1]')[0]
                self.add_vote(bill, actor, date, action, dd)

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

    def add_vote(self, bill, chamber, date, text, dd):
        votes = re.findall(r'Ayes (\d+)\, N(?:oes|ays) (\d+)', text)
        (yes, no) = int(votes[0][0]), int(votes[0][1])

        vtype = 'other'
        for regex, type in motion_classifiers.iteritems():
            if re.match(regex, text):
                vtype = type
                break

        v = Vote(chamber, date, text, yes > no, yes, no, 0, type=vtype)

        # fetch the vote itself
        link = dd.xpath('.//a[contains(@href, "/votes/")]')
        if link:
            link = link[0].get('href')
            v.add_source(link)

            filename, resp = self.urlretrieve(link)

            if 'av' in link:
                self.add_house_votes(v, filename)
            elif 'sv' in link:
                self.add_senate_votes(v, filename)

            os.remove(filename)

        bill.add_vote(v)


    def add_senate_votes(self, vote, filename):
        xml = convert_pdf(filename, 'xml')
        doc = lxml.html.fromstring(xml)  # use lxml.html for text_content()

        # what to do with the pieces
        vfunc = None

        for textitem in doc.xpath('//text'):

            text = textitem.text_content().strip()

            if text.startswith('AYES'):
                vfunc = vote.yes
                vote['yes_count'] = int(text.split(u' \u2212 ')[1])
            elif text.startswith('NAYS'):
                vfunc = vote.no
                vote['no_count'] = int(text.split(u' \u2212 ')[1])
            elif text.startswith('NOT VOTING'):
                vfunc = vote.other
                vote['other_count'] = int(text.split(u' \u2212 ')[1])
            elif text.startswith('SEQUENCE NO'):
                vfunc = None
            elif vfunc:
                vfunc(text)


    def add_house_votes(self, vote, filename):
        vcount_re = re.compile('AYES.* (\d+).*NAYS.* (\d+).*NOT VOTING.* (\d+).* PAIRED.*(\d+)')
        xml = convert_pdf(filename, 'xml')
        doc = lxml.html.fromstring(xml)  # use lxml.html for text_content()

        # function to call on next legislator name
        vfunc = None
        name = ''

        for textitem in doc.xpath('//text/text()'):
            if textitem.startswith('AYES'):
                ayes, nays, nv, paired = vcount_re.match(textitem).groups()
                vote['yes_count'] = int(ayes)
                vote['no_count'] = int(nays)
                vote['other_count'] = int(nv)
                # NOTE: paired do not count in WI's counts so we omit them
            elif textitem == 'N':
                vfunc = vote.no
                name = ''
            elif textitem == 'Y':
                vfunc = vote.yes
                name = ''
            elif textitem == 'x':
                vfunc = vote.other
                name = ''
            elif textitem in ('R', 'D', 'I'):
                vfunc(name)
            else:
                if name:
                    name += ' ' + textitem
                else:
                    name = textitem
