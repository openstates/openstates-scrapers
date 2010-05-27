#!/usr/bin/env python
import datetime as dt
import lxml.html
import sys
import os
import re
import name_tools

from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter, process_pdf
from pdfminer.pdfdevice import PDFDevice
from pdfminer.converter import TextConverter
from pdfminer.cmapdb import CMapDB
from pdfminer.layout import LAParams

from StringIO import StringIO
import urllib2

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.legislation import (LegislationScraper, Bill, Vote, Legislator,
                                 NoDataForYear)


class WisconsinScraper(LegislationScraper):
    state = 'wi'
    earliest_year = 1999
    internal_sessions = {}

    def scrape_bills(self, chamber, year):
        # we need to be able to make http://www.legis.state.wi.us/2009/data/AB2hst.html
        # and http://www.legis.state.wi.us/2009/data/DE9AB2hst.html
        for sess in self.internal_sessions[int(year)]:
          yp = sess[0][1:].split('/', 1)
          (year, prefix) = (yp[0], yp[1]) if len(yp) == 2 else (yp[0], '')
          self.scrape_session(chamber, year, prefix, sess[1])
          

    def scrape_session(self, chamber, year, prefix, session):
        def parse_sponsors(bill, line, chamber):
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
                bill.add_sponsor(sponsor_type, r.strip(), chamber=leg_chamber[sponsor_type])


        def parse_action(bill, line, actor, date):
            line = lxml.html.fromstring(line)
            sane = line.text_content()
            # "06-18.  S. Received from Assembly  ................................... 220 "
            # "___________                      __________________________________________"
            #    11         
            sane = sane.strip()[11:]  #take out the date and house
            if sane.find('..') != -1: 
                sane = sane[0:sane.find(' ..')]  #clear out bookkeeping
            bill.add_action(actor, sane, date)
            for doc in line.findall('a'):
                # have this treat amendments better, as they show up like "1" or "3" now..
                bill.add_document(doc.text_content(), doc.get('href'))

            if sane.find('Ayes') != -1:
                self.add_vote(bill, actor, date, sane)

        house = 'SB' if (chamber == 'upper') else 'AB'
        chambers = {'S': 'upper', 'A': 'lower'}
        i = 1
        while True:
            try:
                url = "http://www.legis.state.wi.us/%s/data/%s%s%dhst.html" % (year, prefix, house, i)
                body = unicode(self.urlopen(url), 'latin-1')
            except urllib2.HTTPError as e: #404tastic
                 return
 
            page = lxml.html.fromstring(body).cssselect('pre')[0]
            # split the history into each line, exluding all blank lines and the title line
            history = filter(lambda x: len(x.strip()) > 0, lxml.html.tostring(page).split("\n"))[2:-1]
            buffer = ''
            bill_id = page.find("a").text_content()
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

                buffer = buffer + ' ' + line.strip()
                if(stop and not bill_title):
                    bill_title = workdata
                    bill = Bill(session, chamber, bill_id, bill_title)
                    continue

                if(stop and not bill_sponsors):
                    parse_sponsors(bill, workdata, chamber)
                    bill_sponsors = True
                    current_chamber = chambers[dm[2]]
                    action_date = dt.datetime(current_year, int(dm[0]), int(dm[1]))
                    continue
                    
                if(stop):
                    parse_action(bill, workdata, current_chamber, action_date)
                    #now update the date
                    current_chamber = chambers[dm[2]]
                    action_date = dt.datetime(current_year, int(dm[0]), int(dm[1]))
                
            current_chamber = chambers[dm[2]]
            action_date = dt.datetime(current_year, int(dm[0]), int(dm[1]))    
            parse_action(bill, buffer, current_chamber, action_date)
            bill.add_source(url)
            self.save_bill(bill)
            i = i + 1

    def add_vote(self, bill, chamber, date, line):
        votes = re.findall(r'Ayes (\d+)\, Noes (\d+)', line)
        (yes, no) = int(votes[0][0]), int(votes[0][1])
        v = Vote(chamber, date, line, yes > no, yes, no, 0)
        bill.add_vote(v)

        return
        if line.findall('a') != []:
            vote_url = filter(lambda x: x.get('href').find('votes') != -1, line.findall('a'))
            vote_url = vote_url[0].get('href')
        with self.urlopen_context(vote_url) as the_pdf:
    
            # UGH! What a useful yet convoluted library.
            outtext = StringIO()
            rsrc = PDFResourceManager()
            device = TextConverter(rsrc, outtext, codec='ascii')
            process_pdf(rsrc, device, StringIO(the_pdf), set())
            outtext.seek(0)
            text = outtext.read()
            """
            Wisconsin Senate Roll Call20092010 SESSIONSB 1PASSAGEAYES  18 CARPENTER COGGS DECKER 
            ERPENBACH HANSEN HOLPERIN JAUCH KREITLOW LASSA LEHMAN MILLER PLALE RISSER ROBSON SULLIVAN 
            TAYLOR VINEHOUT WIRCH NAYS  14 COWLES DARLING ELLIS FITZGERALD GROTHMAN HARSDORF HOPPER 
            KANAVAS KAPANKE LASEE LAZICH LEIBHAM OLSEN SCHULTZ NOT VOTING  1 KEDZIE SEQUENCE NO. 15 
            Tuesday, February 10, 2009 1:01 PM  Wisconsin Senate Roll Call1
            """

            """
            WISCONSIN ASSEMBLY20092010 SESSIONSpeaker SheridanAB 1BY CLARKSTATE AND LOCAL PROCUREMENT
            PERCENTAGESPASSAGEAYES  77   NAYS  22   NOT VOTING  0   PAIRED  0 ANNVNAMENBALLWEGRYBARCAD
            YBENEDICTDYBERCEAUDYBERNARDSCHABERDYBIESRYBLACKDYBROOKSRYCLARKDYCOLONDYCULLENDYDANOUDYDAVISR
            YDEXTERDYFIELDSDNFITZGERALDRYFRISKERYGARTHWAITEDNGOTTLIEBRYGRIGSBYDNGUNDERSONRNGUNDRUMRYHEBLD
            YHILGENBERGDYHINTZDYHIXSONDYHONADELRYHRAYCHUCKDYHUBLERDYHUEBSCHRYJORGENSENDYKAUFERTRNKERKMANR
            ANNVNAMEYKESSLERDYKESTELLRNKLEEFISCHRNKNODLRNKRAMERRYKRUSICKDNLEMAHIEURNLOTHIANRYMASONDYMEYERR
            YMILROYDYMOLEPSKEDYMONTGOMERYRYMURSAURYMURTHARNNASSRYNELSONDYNERISONRNNEWCOMERRYNYGRENR
            YOTT, A.RYOTT, J.RYPARISIDYPASCHDYPETERSENRYPETROWSKIRYPOCANDYPOPEROBERTSDNPRIDEMORERYRADCLIFFED
            YRHOADESRYRICHARDSDYRIPPRANNVNAMEYROTHRYROYSDYSCHNEIDERDYSEIDELDYSHERMANDYSHILLINGDYSINICKIDYSMITHD
            YSOLETSKIDYSPANBAUERRYSTASKUNASDYSTEINBRINKDNSTONERNSTRACHOTARNSUDERRYTAUCHENRYTOLESDYTOWNSENDR
            YTURNERDYVAN AKKERENDNVAN ROYRNVOSRYVRUWINKDNVUKMIRRYWILLIAMS, A.DYWILLIAMS, M.RNWOODIYYOUNGD
            YZEPNICKDNZIEGELBAUERDYZIGMUNTDYZIPPERERRYSPEAKERDIN CHAIR: STASKUNAS 
            NO VACANT DISTRICTS SEQUENCE NO. 6 Tuesday, January 27, 2009 2:49 PM  WISCONSIN ASSEMBLY ROLL CALL1
            """
            print text
    

    def scrape_legislators(self, chamber, year):
        year = int(year)
        session = self.internal_sessions[year][0][1]
        # iterating through subsessions would be a better way to do this..
        if year % 2 == 0 and (year != dt.date.today().year or  year+1 != dt.date.today().year):
            raise NoDataForYear(year)

        if chamber == 'upper':
            url = "http://legis.wi.gov/w3asp/contact/legislatorslist.aspx?house=senate"
        else:
            url = "http://legis.wi.gov/w3asp/contact/legislatorslist.aspx?house=assembly"
        
        body = unicode(self.urlopen(url), 'latin-1')
        page = lxml.html.fromstring(body)

        for row in page.cssselect("#ctl00_C_dgLegData tr"):
            if len(row.cssselect("td a")) > 0:
                rep_url = list(row)[0].cssselect("a[href]")[0].get("href")
                (full_name, party) = re.findall(r'([\w\-\,\s\.]+)\s+\(([\w])\)', 
                                     list(row)[0].text_content())[0]

                pre, first, last, suffixes = name_tools.split(full_name)

                district = str(int(list(row)[2].text_content()))

                leg = Legislator(session, chamber, district, full_name,
                                 first, last, '', party,
                                 suffix=suffixes)
                leg.add_source(rep_url)

                leg = self.add_committees(leg, rep_url, session)
                self.save_legislator(leg)

    def add_committees(self, legislator, rep_url, session):
        url = 'http://legis.wi.gov/w3asp/contact/' + rep_url + '&display=committee'
        body = unicode(self.urlopen(url), 'latin-1')
        cmts = lxml.html.fromstring(body).cssselect("#ctl00_C_lblCommInfo a")
        for c in map(lambda x: x.text_content().split('(')[0], list(cmts)):
            legislator.add_role('committee member', session, committee=c.strip())
        return legislator


    def scrape_metadata(self):
        sessions = []
        session_details = {}

        with self.soup_context("http://www.legis.state.wi.us/") as session_page:
            for option in session_page.find(id='session').findAll('option'):
                year = int(re.findall(r'[0-9]+', option.string)[0])
                text = option.string.strip()
                if not year in self.internal_sessions:
                    self.internal_sessions[year] = []
                    session_details[year] = {'years': [year], 'sub_sessions':[] }
                    sessions.append(year)
                session_details[year]['sub_sessions'].append(text)
                self.internal_sessions[year].append([option['value'], text])
        return {
            'state_name': 'Wisconsin',
            'legislature_name': 'Wisconsin State Legislature',
            'lower_chamber_name': 'Assembly',
            'upper_chamber_name': 'Senate',
            'lower_title': 'Representative',
            'upper_title': 'Senator',
            'lower_term': 2,
            'upper_term': 4,
            'sessions': sessions,
            'session_details': session_details
        }


if __name__ == '__main__':
    WisconsinScraper.run()
