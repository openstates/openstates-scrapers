# -*- coding: utf-8 -*-
from billy.scrape import ScrapeError, NoDataForPeriod
from billy.scrape.utils import convert_word
from billy.scrape.votes import Vote
from billy.scrape.bills import BillScraper, Bill
from openstates.pr.utils import grouper, doc_link_url, year_from_session

import lxml.html
import datetime
import itertools
import os
import re

class NoSuchBill(Exception):
    pass
_voteChambers = (
   (u'Aprobado por el Senado en Votac','upper'),
   (u'Aprobado por C','lower'),
)
_classifiers = (
    ('Radicado', 'bill:introduced'),
    #votes are here
    (u'Aprobado por Cámara en Votación Final', 'bill:passed'),
  (u'Aprobado por el Senado en Votación', 'bill:passed'),
#    ('Cuerpo de Origen concurre','bill:passed'),
 ('Aparece en Primera Lectura', 'bill:reading:1'),
 #sent is not the same as received
 ('Enviado al Gobernador', 'governor:received'),
 ('Veto', 'governor:vetoed'),
 #comissions give a report but sometimes they dont do any amendments and live them as they are.
 #i am not checking if they did or not. but it be easy just read the end and if it dosnt have amendments it should say 'sin enmiendas'
    ('1er Informe','amendment:amended'),
    ('2do Informe','amendment:amended'),
    ('Aprobado con enmiendas','amendment:passed'),
    (u'Remitido a Comisión', 'committee:referred'),
    (u'Referido a Comisión', 'committee:referred'),
)
'''    
    , 'bill:introduced'
    , 'bill:passed'
    , 'bill:failed'
    , 'bill:withdrawn'
    , 'bill:substituted'
    , 'bill:filed'
    , 'bill:veto_override:passed'
    , 'bill:veto_override:failed'
    , 'governor:received'
    , 'governor:signed'
    , 'governor:vetoed'
    , 'governor:vetoed:line-item'
    , 'amendment:introduced'
    , 'amendment:passed'
    , 'amendment:failed'
    , 'amendment:tabled'
    , 'amendment:amended'
    , 'amendment:withdrawn'
    , 'committee:referred'
    , 'committee:failed'
    , 'committee:passed'
    , 'committee:passed:favorable'
    , 'committee:passed:unfavorable'
    , 'bill:reading:1'
    , 'bill:reading:2'
    , 'bill:reading:3'
    , 'other'
'''
class PRBillScraper(BillScraper):
    state = 'pr'

    bill_types = {'P': 'bill',
                  'R': 'resolution',
                  'RK': 'concurrent resolution',
                  'RC': 'joint resolution',
                  #'PR': 'plan de reorganizacion',
                 }

    def scrape(self, chamber, session):
        year = session[0:4]

        self.base_url = 'http://www.oslpr.org/legislatura/tl%s/tl_medida_print2.asp' % year

        chamber_letter = {'lower':'C','upper':'S'}[chamber]

        for code, type in self.bill_types.iteritems():
            counter = itertools.count(1)
            for n in counter:
                bill_id = '%s%s%s' % (code, chamber_letter, n)
                try:
                    self.scrape_bill(chamber, session, bill_id, type)
                except NoSuchBill:
                    break

    def scrape_bill(self, chamber, session, bill_id, bill_type):
        url = '%s?r=%s' % (self.base_url, bill_id)
        with self.urlopen(url) as html:
            doc = lxml.html.fromstring(html)

            # search for Titulo, accent over i messes up lxml, so use 'tulo'
            title = doc.xpath(u'//td/b[contains(text(),"tulo")]/../following-sibling::td/text()')
            if not title:
                raise NoSuchBill()
            bill = Bill(session, chamber, bill_id, title[0], type=bill_type)
            author = doc.xpath(u'//td/b[contains(text(),"Autor")]/../text()')[0]
            bill.add_sponsor('primary', author.strip())
          
            co_authors = doc.xpath(u'//td/b[contains(text(),"Co-autor")]/../text()')
            if len(co_authors) !=0:
                for co_author in co_authors[1].split(','):
                    bill.add_sponsor('cosponsor',co_author.strip());

            
            action_table = doc.xpath('//table')[-1]
            for row in action_table[1:]:
                tds = row.xpath('td')

                # ignore row missing date
                if len(tds) != 2:
                    continue


                date = datetime.datetime.strptime(tds[0].text_content(),
                                                  "%m/%d/%Y")
                
                action = tds[1].text_content().strip()
                #parse the text to see if it's a new version or a unrelated document
                #if has - let's *shrug* assume it's a vote document        

                #get url of action
	        action_url = tds[1].xpath('a/@href')
                #check it has a url and is not just text
		if action_url:
		    action_url = action_url[0]
		#check if it's a version of the bill or another type of document.
		#NOTE: not sure if new versions of the bill are only denoted with 'Entirillado' OR if that's the correct name but from what i gather it looks like it.
		    if re.match('Entirillado',action):
        	        bill.add_version(action, action_url)
	            else:
                        bill.add_document(action, action_url)    
                for pattern, atype in _classifiers:
                    if re.match(pattern, action):
                        break
                else:
                    atype = 'other'
                bill.add_action(chamber, action, date, type=atype)
                if atype == 'bill:passed' and action_url:
		   vote_chamber  = None
		   for pattern, vote_chamber in _voteChambers:
		       if re.match(pattern,action):
		           break
                   else:
                       self.warning('coudnt find voteChamber pattern')
		   if vote_chamber == 'lower' and len(action_url) > 0:
			   vote = self.scrape_votes(action_url,action,date,vote_chamber)
		   	   if not vote[0] == None:
		     	       vote[0].add_source(action_url)
			       bill.add_vote(vote[0])
			   else:
			       self.warning('Problem Reading vote: %s,%s' % ( vote[1], bill_id))
               

            bill.add_source(url)
            self.save_bill(bill)

    def get_filename_parts_from_url(self,url):	
        fullname = url.split('/')[-1].split('#')[0].split('?')[0]
        t = list(os.path.splitext(fullname))
        if t[1]:
            t[1] = t[1][1:]
            return t


    def scrape_votes(self, url, motion, date, bill_chamber):
            filename1, extension = self.get_filename_parts_from_url(url)
            filename=filename1+'.'+extension
	    if extension == 'pdf':
		return None,'Vote on PDF'
            vote_pdf, resp = self.urlretrieve(url)
            
            text = convert_word(vote_pdf, 'html')
            os.remove(vote_pdf)
            yes_votes = []
            no_votes = []
            other_votes = []

            doc = lxml.html.fromstring(text)
#           header = doc.xpath('/html/body/div/table[1]/tbody/tr[1]/td[2]')
#           header_txt = header[0][0][0].text_content();
#           assembly_number = header[0][0][1].text_content();
#           bill_id = header[0][0][3].text_content().lstrip().rstrip();
            #show legislator,party,yes,no,abstention,observations
            table = doc.xpath('/html/body/div/table[2]/tbody')
	    if len(table) == 0:
		return None,'Table body Problem'
	    #they have documents(PC0600') that have the action name as vote but in reality the actual content is the bill text which breaks the parser
	    try:
		table[0].xpath('tr')[::-1][0].xpath('td')[1]
	    except IndexError:
		table = doc.xpath('/html/body/div/table[3]/tbody')
		
            #loop thru table and skip first one
            vote = None
            for row in table[0].xpath('tr')[::-1]:
                tds = row.xpath('td')
                party = tds[1].text_content().replace('\n', ' ').replace(' ','').replace('&nbsp;','');
                yes_td =  tds[2].text_content().replace('\n', ' ').replace(' ','').replace('&nbsp;','')
                nays_td =  tds[3].text_content().replace('\n', ' ').replace(' ','').replace('&nbsp;','')
                abstent_td =  tds[4].text_content().replace('\n', ' ').replace(' ','').replace('&nbsp;','')
                if party != 'Total':
                    name_td = tds[0].text_content().replace('\n', ' ').strip();
                    if yes_td == 'r':
                        yes_votes.append(name_td)
                    if nays_td == 'r':
                        no_votes.append(name_td)
                    if abstent_td == 'r':
                        other_votes.append(name_td)
                    #observations
#                   observations_td =  tds[5].text_content().replace('\n', ' ').replace(' ','').replace('&nbsp;','')
#                   print observations_td
            
            
            
            # return vote object
            yes_count = len(yes_votes)
            no_count = len(no_votes)
            other_count = len(other_votes)
            #FixME: Since i am searching for the word passed it means that passed will always be true.
            vote = Vote(bill_chamber, date, motion, True, yes_count, no_count,
                        other_count)
            vote['yes_votes'] = yes_votes
            vote['no_votes'] = no_votes
            vote['other_votes'] = other_votes
            return vote,'Good'

            
