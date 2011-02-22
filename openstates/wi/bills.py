import datetime as dt
import lxml.html
import os
import re
from StringIO import StringIO
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
}


class WIBillScraper(BillScraper):
    state = 'wi'

    def __init__(self, *args, **kwargs):
        super(WIBillScraper, self).__init__(*args, **kwargs)
        #self.build_issue_index()

    def build_issue_index(self):
        self.log('building WI issue index')
        self._subjects = defaultdict(list)

        n = 2
        try:
            while True:
                url = 'http://nxt.legis.state.wi.us/nxt/gateway.dll/Session%%20Related/indxsubj/%s' % n
                with self.urlopen(url) as html:
                    doc = lxml.html.fromstring(html)
                    title = doc.xpath('//title/text()')[0]
                    links = doc.xpath('//a/text()')
                    for link in links:
                        if '-' in link:  # check that its a bill
                            link = link.replace('-', ' ').strip()
                            self._subjects[link].append(title)
                n += 1
                print n
        except scrapelib.ScrapeError:
            pass

    def scrape(self, chamber, session):
        types = {'lower': ['ab', 'ajr', 'ar', 'ap'],
                 'upper': ['sb', 'sjr', 'sr', 'sp']}
        base_url = 'http://www.legis.state.wi.us/%s/data/%s_list.html'
        year = None
        for term in self.metadata['terms']:
            if session in term['sessions']:
                year = term['name'][0:4]
                break

        if 'Regular' in session:
            for t in types[chamber]:
                url =  base_url % (year, t)
                self.scrape_bill_list(chamber, session, url)
        else:
            site_id = self.metadata['session_details'][session]['site_id']
            url = base_url % (year, site_id)
            self.scrape_bill_list(chamber, session, url)

    def scrape_bill_list(self, chamber, session, url):
        bill_types = {'B': 'bill', 'R': 'resolution',
                      'JR': 'joint resolution', 'P': 'petition' }

        try:
            with self.urlopen(url) as data:
                doc = lxml.html.fromstring(data)
                doc.make_links_absolute(url)
                rows = doc.xpath('//tr')
                for row in rows[1:]:
                    link = row.xpath('td[1]/a')[0]
                    bill_id = link.text
                    link = link.get('href')
                    title = row.xpath('td[2]/text()')[0][13:]

                    # first part of bill_id with first char stripped off
                    prefix = bill_id.split()[0]

                    # skip bills from other chamber (for special sessions)
                    bill_chamber = 'lower' if prefix[0] == 'A' else 'upper'
                    if bill_chamber != chamber:
                        continue
                    bill_type = bill_types[prefix[1:]]

                    bill = Bill(session, chamber, bill_id, title,
                                type=bill_type)
                    #bill['subjects'] = self._subjects[bill_id]
                    self.scrape_bill_history(bill, link)
        except scrapelib.HTTPError, e:
            if e.response.code == 404:
                self.log('No data for %s' % url)

    def scrape_bill_history(self, bill, url):
        chambers = {'A': 'lower', 'S': 'upper'}
        body = self.urlopen(url)
        doc = lxml.html.fromstring(body)

        # first link on page is always official bill text
        link = doc.xpath('//a')[0].get('href')
        bill.add_version('Official Version', link)

        page = doc.xpath('//pre')[0]
        # split the history into each line, exluding all blank lines and title
        history = [x for x in lxml.html.tostring(page).split('\n')
                   if len(x.strip()) > 0][2:-1]

        buffer = ''
        bill_title = None
        bill_sponsors = False
        current_year = None
        action_date = None
        current_chamber = None

        for line in history:
            stop = False

            # the year changed
            if re.match(r'^(\d{4})[\s]{0,1}$', line):
                current_year = int(line.strip())
                continue

            # the action changed.
            if re.match(r'\s+(\d{2})-(\d{2}).\s\s([AS])\.\s', line):
               dm = re.findall(r'\s+(\d{2})-(\d{2}).\s\s([AS])\.\s', line)[0]
               workdata = buffer
               buffer = ''
               stop = True

            buffer += (' ' + line.strip())

            if stop and not bill_title:
                bill_title = workdata
                continue

            if stop and not bill_sponsors:
                self.parse_sponsors(bill, workdata, bill['chamber'])
                bill_sponsors = True
                current_chamber = chambers[dm[2]]
                action_date = dt.datetime(current_year, int(dm[0]), int(dm[1]))
                self.parse_action(bill, workdata, current_chamber, action_date)
                continue

            if stop:
                self.parse_action(bill, workdata, current_chamber, action_date)
                #now update the date
                current_chamber = chambers[dm[2]]
                action_date = dt.datetime(current_year, int(dm[0]), int(dm[1]))

        current_chamber = chambers[dm[2]]
        action_date = dt.datetime(current_year, int(dm[0]), int(dm[1]))
        self.parse_action(bill, buffer, current_chamber, action_date)
        bill.add_source(url)
        self.save_bill(bill)

    def parse_sponsors(self, bill, line, chamber):
        sponsor_type = None
        if chamber == 'upper':
            leg_chamber = {'primary': 'upper', 'cosponsor': 'lower'}
        else:
            leg_chamber = {'primary': 'lower', 'cosponsor': 'upper'}
        for r in re.split(r'\sand\s|\,|;', line):
            r = r.strip()
            if r.find('Introduced by') != -1:
                sponsor_type = 'primary'
                r = re.split(r'Introduced by \w+', r)[1]
            if r.find('cosponsored by') != -1:
                sponsor_type = 'cosponsor'
                r = re.split(r'cosponsored by \w+', r)[1]
            if r.strip():
                bill.add_sponsor(sponsor_type, r.strip(),
                                 chamber=leg_chamber[sponsor_type])

    def parse_action(self, bill, line, actor, date):
        line = lxml.html.fromstring(line)
        sane = line.text_content()
        # "06-18.  S. Received from Assembly  ................................... 220 "
        # "___________                      __________________________________________"
        #    11
        sane = sane.strip()[11:]  #take out the date and house
        if sane.find('..') != -1:
            sane = sane[0:sane.find(' ..')]  #clear out bookkeeping

        # classify actions
        atype = 'other'
        for regex, type in action_classifiers.iteritems():
            if re.match(regex, sane):
                atype = type
                break
        bill.add_action(actor, sane, date, type=atype)

        # add documents
        self.add_documents(bill, line, sane)

        if 'Ayes' in sane:
            self.add_vote(bill, actor, date, line, sane)

    def add_documents(self, bill, line, sane):
        for a in line.findall('a'):
            link_text = a.text_content()
            link = a.get('href')

            if 'Ayes' in sane or 'Noes' in sane or 'Paired' in sane:
                pass
            elif link_text == 'Fiscal estimate received':
                self.add_document(bill, 'Fiscal estimate', link)
            elif len(link_text) <= 3 and 'offered' in sane:
                self.add_document(bill, sane.split(' offered')[0], link)
            elif link_text.startswith('Act'):
                name = '%s Wisconsin %s' % (bill['session'], link_text)
                self.add_document(bill, name, link)
            elif link_text == 'Printed engrossed':
                self.add_document(bill, 'Engrossed Printing', link)
            else:
                self.add_document(bill, sane, link)

    def add_document(self, bill, name, link):
        """ avoid adding duplicate documents """

        for doc in bill['documents']:
            if link == doc['url']:
                return
        bill.add_document(name, link)

    def add_vote(self, bill, chamber, date, line, text):
        votes = re.findall(r'Ayes (\d+)\, Noes (\d+)', text)
        (yes, no) = int(votes[0][0]), int(votes[0][1])

        vtype = 'other'
        for regex, type in motion_classifiers.iteritems():
            if re.match(regex, text):
                vtype = type
                break

        v = Vote(chamber, date, text, yes > no, yes, no, 0, type=vtype)

        # fetch the vote itself
        link = line.xpath('//a[contains(@href, "/votes/")]')
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
                vote['other_count'] = int(nv)+int(paired)
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
