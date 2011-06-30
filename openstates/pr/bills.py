# -*- coding: utf-8 -*-
from billy.scrape import ScrapeError, NoDataForPeriod
from billy.scrape.votes import Vote
from billy.scrape.bills import BillScraper, Bill
from openstates.pr.utils import grouper, doc_link_url, year_from_session

import lxml.html
import datetime
import itertools
import re

class NoSuchBill(Exception):
    pass

_classifiers = (
    ('Radicado', 'bill:introduced'),
    #votes are here
    (u'Aprobado por Cámara en Votación Final', 'bill:passed'),
    (u'Aprobado por el Senado en Votación', 'bill:passed'),
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
        chamber_letter = {'upper':'S', 'lower':'C'}[chamber]

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
                    #print co_author.strip();

            
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
 #               version_txt = ['Radicado','Enmiendas','Entirillado',
#                if u'Votacion  ' != :
                    #regular document
                #get url of action
                #action_document =  tds[1].xpath('a[text()=\''+ action+'\']/@href')
                #check it has a url and is not just text
                #if len(action_document) != 0:
                    #bill.add_document(action,action_document[0]);
                
                
                for pattern, atype in _classifiers:
                    if re.match(pattern, action):
                        break
                else:
                    atype = 'other'
                bill.add_action(chamber, action, date, type=atype)
                #if atype == 'bill:passed':
                    #print 'voto'
                # also has an associated version
                #if tds[1].xpath('a'):
                    #bill.add_version(action, tds[1].xpath('a/@href')[0])

            bill.add_source(url)
            self.save_bill(bill)
