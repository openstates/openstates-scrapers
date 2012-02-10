# -*- coding: utf-8 -*-
from billy.scrape import ScrapeError, NoDataForPeriod
from billy.scrape.votes import Vote
from billy.scrape.bills import BillScraper, Bill
from .utils import grouper, doc_link_url, year_from_session

import lxml.html
import datetime
import itertools
import subprocess
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
    #comissions give a report but sometimes they dont do any amendments and leave them as they are.
    #i am not checking if they did or not. but it be easy just read the end and if it dosnt have amendments it should say 'sin enmiendas'
    ('1er Informe','amendment:amended'),
    ('2do Informe','amendment:amended'),
    ('Aprobado con enmiendas','amendment:passed'),
    (u'Remitido a Comisión', 'committee:referred'),
    (u'Referido a Comisión', 'committee:referred'),
)


class PRBillScraper(BillScraper):
    state = 'pr'

    bill_types = {'P': 'bill',
                  'R': 'resolution',
                  'RK': 'concurrent resolution',
                  'RC': 'joint resolution',
                  #'PR': 'plan de reorganizacion',
                 }



    def clean_name(self, name):
        name =  name.replace('Sr,','').replace('Sr.','').replace('Sra.','').replace('Rep.','').replace('Sen.','')
	return name
    def fix_name(self,name):
	if name == u'Pedro Rodríguez González':
	   name = 'Pedro A. Rodríguez González'
	elif name == u'María de L. Ramos Rivera':
	   name = 'María de Lourdes Ramos Rivera'
	elif name == u'Carmen Yulín Cruz Soto':
	   name = 'Carmen Y. Cruz Soto'
	elif name == u'Carlos J. Méndez Núñez' or name == u'Carlos J. Méndez Nuñez':
	   name = 'Carlos “Johnny” Méndez Nuñez'
	elif name == u'Héctor Torres Calderón':
	   name = 'Héctor A. Torres Calderón'
	elif name == u'Pedro Rodríguez González':
	   name = 'Pedro A. Rodríguez González'
	elif name == u'Héctor J. Ferrer Ríos':
	   name = 'Héctor Ferrer Ríos'
	elif name == u'José Enrique Meléndez Ortiz':
	   name = 'Jose E. Melendez Ortiz'
	elif name == u'José L. López Muñoz':
	   name = 'José  López Muñoz'
	elif name == u'Liza M. Fernández Rodríguez':
	   name = 'Liza  Fernández Rodríguez'
	elif name == u'José E. Torres Zamora':
	   name = 'Jose Torres Zamora'
	elif name == u'Angel Pérez Otero':
	   name = 'Angel A. Pérez Otero'
	elif name == u'Arnaldo I. Jiménez Valle':
	   name = 'Arnaldo Jiménez Valle'
	elif name == 'Luis Vega Ramos':
	   name = 'Luis R. Vega Ramos'
	elif name == u'Angel Rodríguez Miranda':
           name = 'Angel E. Rodríguez Miranda'
	   print name
	return name

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
            for aname in author.split(','):
                bill.add_sponsor('primary', self.fix_name(self.clean_name(aname)).strip())

            co_authors = doc.xpath(u'//td/b[contains(text(),"Co-autor")]/../text()')
            if len(co_authors) != 0:
                for co_author in co_authors[1].split(','):
                    bill.add_sponsor('cosponsor', self.fix_name(self.clean_name(co_author)).strip());


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
                    if re.match('Entirillado', action):
                        bill.add_version(action, action_url)
                    else:
			
                        bill.add_document(action, action_url)

                for pattern, atype in _classifiers:
                    if re.match(pattern, action):
                        break
                else:
                    atype = 'other'
		if action.startswith('Ley N'):
		    action = action[0:42]
		elif action.startswith('Res. Conj.'):
		    action = action[0:42]
                bill.add_action(chamber, action.replace('.',''), date, type=atype)

                if atype == 'bill:passed' and action_url:
                    vote_chamber  = None
                    for pattern, vote_chamber in _voteChambers:
                       if re.match(pattern,action):
                           break
                    else:
                       self.warning('coudnt find voteChamber pattern')

                    if vote_chamber == 'lower' and len(action_url) > 0:
                        vote = self.scrape_votes(action_url, action,date,
                                                 vote_chamber)
                        if not vote[0] == None:
                            vote[0].add_source(action_url)
                            bill.add_vote(vote[0])
                        else:
                            self.warning('Problem Reading vote: %s,%s' %
                                         (vote[1], bill_id))

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

        if extension == 'pdf':
            return None,'Vote on PDF'

        vote_doc, resp = self.urlretrieve(url)

        # use abiword to convert document
        html_name = vote_doc + '.html'
        subprocess.check_call('abiword --to=%s %s' % (html_name, vote_doc),
                              shell=True, cwd='/tmp/')
        text = open(html_name).read()
        os.remove(html_name)
        os.remove(vote_doc)

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
                name_td = self.clean_name(tds[0].text_content().replace('\n', ' ').replace('','',1)).strip();
		split_name = name_td.split(',')
		if len(split_name) > 1:
		   name_td = split_name[1].strip() + ' ' + split_name[0].strip()
		if name_td == u'Catherine J. Nolasco Ortiz' or name_td == u'Julissa Nolasco Ortiz':
		   name_td = 'Julissa Nolasco Ortíz'
		elif name_td == u'Angel Pérez Otero' or name_td == u'Ángel Pérez Otero':
		   name_td = 'Angel A. Pérez Otero'
		elif name_td == u'Alba I. Rivera Ramírez':
		   name_td = 'Albita  Rivera Ramírez'
		elif name_td == u'Angel Rodríguez Miranda':
		   name_td = 'Angel E. Rodríguez Miranda'
		elif name_td == u'Arnaldo I. Jiménez Valle':
		   name_td = 'Arnaldo Jiménez Valle'
		elif name_td == u'Carmen Yulín Cruz Soto':
		   name_td = 'Carmen Y. Cruz Soto'
		elif name_td == u'Cristobal Colón Ruiz':
		   name_td = 'Cristóbal Colón Ruiz'
		elif name_td == u'Héctor J. Ferrer Ríos':
		   name_td = 'Héctor Ferrer Ríos'
		elif name_td == u'Héctor Torres Calderón':
		   name_td = 'Héctor A. Torres Calderón'
		elif name_td == u'Iván Rodriguez Traverzo':
		   name_td == 'Iván Rodríguez Traverzo'
		elif name_td == u'Jaime Perelló Borrás':
		   name_td = 'Jaime R. Perelló Borrás'
		elif name_td == u'Jenniffer González Colón':
		   name_td = 'Jenniffer A. González Colón'	
		elif name_td == u'Jorge L. Navarro Suárez':
		   name_td = 'Jorge  Navarro Suárez'
		elif name_td == u'José E. Meléndez Ortiz' or name_td == u'José Enrique Meléndez Ortiz' or name_td == u'Meléndez Ortiz':
		   name_td = 'Jose E. Melendez Ortiz'
		elif name_td == u'José E. Torres Zamora' or name_td == u'José Torres Zamora':
		   name_td = 'Jose Torres Zamora'
		elif name_td == u'José J. Chico Vega':
		   name_td = 'José Chico Vega'
		elif name_td == u'José L. López Muñoz':
		   name_td = 'José López Muñoz'
		elif name_td == u'José Luis Jiménez Negrón':
		   name_td = 'José L. Jiménez Negrón'
		elif name_td == u'Lourdes Ramos Rivera':
		   name_td = 'María de Lourdes Ramos Rivera'
		elif name_td == u'Luis E. Farinacci Morales':
   	           name_td ='Luis E. Farinacci Morales'
		elif name_td == u'Luis León Rodríguez':
		   name_td = 'Luis G. León Rodríguez'
		elif name_td == u'Luis R. . Vega Ramos' or name_td == 'Luis Vega Ramos':
		   name_td = 'Luis R. Vega Ramos'
		elif name_td == u'Lydia R. Méndez Silva':
		   name_td = 'Lydia Méndez Silva'
		elif name_td == u'María Vega Pagán':
		   name_td = 'María M. Vega Pagán'
		elif name_td == u'María de L. Ramos Rivera':
		   name_td = 'María de Lourdes Ramos '
		elif name_td == u'Paula Rodríguez Homs':
		   name_td = 'Paula A. Rodríguez Homs'
		elif name_td == u'Pedro Rodríguez González':
		   name_td = 'Pedro A. Rodríguez González'
		elif name_td == u'Rafael E. Rivera Ortega':
		   name_td = 'Rafael Rivera Ortega'
		elif name_td == u'Rafael Hernandez Montañez':
		   name_td = 'Rafael Hernández Montañez'
		elif name_td == u'Roberto Rivera Ruíz De Porra':
		   name_td = 'Roberto Rivera Ruiz de Porras'
		elif name_td == u'Sylvia Rodríguez De Corujo' or name_td == u'Sylvia Rodríguez de Corujo':
		   name_td = 'Sylvia  Rodríguez Aponte'
		elif name_td == u'Victor Vasallo Anadón' or name_td == u'Víctor L. Vassallo Anadón':
		   name_td = 'Víctor L. Vasallo Anadón'
		elif name_td == u'Ángel E. Rodríguez Miranda':
		   name_td = 'Angel E. Rodríguez Miranda'
		elif name_td == u'Ángel L. Bulerín Ramos':
		   name_td = 'Angel  Bulerín Ramos'
		elif name_td == u'Ángel R. Peña Ramírez':
		   name_td = 'Angel R. Peña Ramírez'

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
