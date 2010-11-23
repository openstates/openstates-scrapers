import datetime as dt
import lxml.html
import re
from StringIO import StringIO

import scrapelib

from fiftystates.scrape.utils import convert_pdf
from fiftystates.scrape.bills import BillScraper, Bill
from fiftystates.scrape.votes import Vote

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

    def scrape(self, chamber, session):
        if 'Regular' in session:
            self.scrape_regular(chamber, session)
        else:
            raise NoDataForPeriod(session)

        """
        TODO: scrape special sessions
        /2009/DE9: Dec 2009 Special Session
        /2009/JN9: June 2009 Special Session
        /2007/AP8: April 2008 Special Session
        /2007/MR8: March 2008 Special Session
        /2007/de7: Dec 2007 Special Session
        /2007/oc7: Oct 2007 Special Session
        /2007/jr7: Jan 2007 Special Session
        /2005/jr5: Jan 2005 Special Session
        /2003/jr3: Jan 2003 Special Session
        /2001/my2: May 2002 Special Session
        /2001/jr2: Jan 2002 Special Session
        /2001/my1: May 2001 Special Session
        """

    def scrape_regular(self, chamber, session):
        types = {'lower': ['ab', 'ajr', 'ar', 'ap'],
                 'upper': ['sb', 'sjr', 'sr', 'sp']}
        bill_types = {'b': 'bill', 'r': 'resolution',
                      'jr': 'joint resolution', 'p': 'petition' }
        year = session[0:4]

        for t in types[chamber]:
            url = 'http://www.legis.state.wi.us/%s/data/%s_list.html' % (year,
                                                                         t)
            bill_type = [bill_types[t[1:]]]

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

                        bill = Bill(session, chamber, bill_id, title,
                                    type=bill_type)
                        self.scrape_bill_history(bill, link)
            except scrapelib.HTTPError, e:
                if e.response.code == 404:
                    self.log('No data for %s %s' % (year, t))

    def scrape_bill_history(self, bill, url):
        body = self.urlopen(url)
        chambers = {'A': 'lower', 'S': 'upper'}

        page = lxml.html.fromstring(body).xpath('//pre')[0]
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

        for doc in line.findall('a'):
            # have this treat amendments better, as they show up like "1" or "3" now..
            bill.add_document(doc.text_content(), doc.get('href'))

        if sane.find('Ayes') != -1:
            self.add_vote(bill, actor, date, line, sane)

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
            filename, resp = self.urlretrieve(link)

            if 'av' in link:
                self.add_house_votes(v, filename)
            elif 'sv' in link:
                self.add_senate_votes(v, filename)

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
            elif text.startswith('NAYS'):
                vfunc = vote.no
            elif text.startswith('NOT VOTING'):
                vfunc = vote.other
            elif text.startswith('SEQUENCE NO'):
                vfunc = None
            elif vfunc:
                vfunc(text)


    def add_house_votes(self, vote, filename):
        xml = convert_pdf(filename, 'xml')
        doc = lxml.html.fromstring(xml)  # use lxml.html for text_content()

        # function to call on next legislator name
        vfunc = None
        name = ''

        for textitem in doc.xpath('//text/text()'):
            if textitem == 'N':
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
