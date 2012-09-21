# -*- coding: utf-8 -*-
from billy.scrape import ScrapeError, NoDataForPeriod
from billy.scrape.votes import Vote
from billy.scrape.bills import BillScraper, Bill
from .utils import grouper, doc_link_url, year_from_session

import lxml.html
import datetime
import itertools
import subprocess
import shutil
import os
import re

class NoSuchBill(Exception):
    pass

_voteChambers = (
    (u'Aprobado por el Senado en Votac','upper'),
    (u'Aprobado por C','lower'),
)
_docVersion = (
    ('Entirillado del Informe'),
    ('Texto de Aprobaci'),
#    ('Ley N'),
    ('rendido con enmiendas'),
    ('Radicado'),
)
_classifiers = (
    ('Radicado','', 'bill:introduced'),
    (u'Aprobado por Cámara en Votación Final','lower', 'bill:passed'),
    (u'Aprobado por el Senado en Votación','upper', 'bill:passed'),
    ('Aparece en Primera Lectura del', 'upper','bill:reading:1'),
    ('Aparece en Primera Lectura de la','lower','bill:reading:1'),
    ('Enviado al Gobernador', 'governor','governor:received'),
    ('Veto', 'governor','governor:vetoed'),
    ('Veto de Bolsillo','governor','governor:vetoed'),
    # comissions give a report but sometimes they dont do any amendments and
    # leave them as they are.
    # i am not checking if they did or not. but it be easy just read the end and
    # if it dosnt have amendments it should say 'sin enmiendas'
    ('1er Informe','committee','amendment:amended'),
    ('2do Informe','committee','amendment:amended'),
    ('Aprobado con enmiendas','','amendment:passed'),
    (u'Remitido a Comisión','', 'committee:referred'),
    (u'Referido a Comisión','', 'committee:referred'),
    ('En el Calendario de Ordenes Especiales de la C','lower','other'),
    ('Texto de Aprobación Final enviado al Senado','upper','other'),
    ('Retirada por su Autor','sponsor','bill:withdrawn'),
    ('Comisión : * no recomienda aprobación de la medida','','committee:passed:unfavorable'),
    ('Ley N','governor','governor:signed')
)


class PRBillScraper(BillScraper):
    state = 'pr'

    bill_types = {
        'P': 'bill',
        'R': 'resolution',
        'RK': 'concurrent resolution',
        'RC': 'joint resolution',
        #'PR': 'plan de reorganizacion',
    }

    def clean_name(self, name):
        for ch in ['Sr,','Sr.','Sra.','Rep.','Sen.']:
            if ch in name:
                name = name.replace(ch,'')
        return name

    def scrape(self, chamber, session):
        # check for abiword
        if os.system('which abiword') != 0:
            raise ScrapeError('abiword is required for PR scraping')


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

    def parse_action(self,chamber,bill,action,action_url,date):
        #if action.startswith('Referido'):
                #committees = action.split(',',1)
                #multiple committees
        if action.startswith('Ley N'):
                action = action[0:42]
        elif action.startswith('Res. Conj.'):
                action = action[0:42]
        action_actor = ''
        atype = 'other'
        #check it has a url and is not just text
        if action_url:
            action_url = action_url[0]
            isVersion = False;
            for text_regex in _docVersion:
                if re.match(text_regex, action):
                   isVersion = True;
            if isVersion:
                # versions are mentioned several times, lets use original name
                if action_url.endswith('.doc'):
                    mimetype = 'application/msword'
                elif action_url.endswith('.rtf'):
                    mimetype = 'application/rtf'
                else:
                    mimetype = None
                bill.add_version(action, action_url, on_duplicate='use_old',
                                 mimetype=mimetype)
            else:
                bill.add_document(action, action_url)
            for pattern, action_actor,atype in _classifiers:
                if re.match(pattern, action):
                    break
                else:
                    action_actor = ''
                    atype = 'other'
        if action_actor == '':
            if action.find('SENADO') != -1:
                action_actor = 'upper'
            elif action.find('CAMARA') != -1:
                action_actor = 'lower'
            else:
                action_actor = chamber
        #if action.startswith('Referido'):
            #for comme in committees:
            #print comme
        bill.add_action(action_actor, action.replace('.',''),date,type=atype)
        return atype,action

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
                bill.add_sponsor('primary', self.clean_name(aname).strip())
            co_authors = doc.xpath(u'//td/b[contains(text(),"Co-autor")]/../text()')
            if len(co_authors) != 0:
                for co_author in co_authors[1].split(','):
                    bill.add_sponsor('cosponsor', self.clean_name(co_author).strip());
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
                atype,action = self.parse_action(chamber,bill,action,action_url,date)
                if atype == 'bill:passed' and action_url:
                    vote_chamber  = None
                    for pattern, vote_chamber in _voteChambers:
                       if re.match(pattern,action):
                           break

                    else:
                       self.warning('coudnt find voteChamber pattern')

                    if vote_chamber == 'lower' and len(action_url) > 0:
                        vote = self.scrape_votes(action_url[0], action,date,
                                                 vote_chamber)
                        if not vote[0] == None:
                            vote[0].add_source(action_url[0])
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
        if isinstance(url,basestring):
            filename1, extension = self.get_filename_parts_from_url(url)
        else:
            return None, 'No url'
        if extension == 'pdf':
            return None,'Vote on PDF'

        vote_doc, resp = self.urlretrieve(url)

        # use abiword to convert document
        html_name = vote_doc + '.html'
        subprocess.check_call('abiword --to=%s %s' % (html_name, vote_doc),
                              shell=True, cwd='/tmp/')
        text = open(html_name).read()
        os.remove(html_name)
        try:
            # try and remove files too
            shutil.rmtree(html_name + '_files')
        except OSError:
            pass
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

        # they have documents(PC0600') that have the action name as vote but in
        # reality the actual content is the bill text which breaks the parser
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
        #FIXME: Since i am searching for the word passed it means that passed
        # will always be true.
        vote = Vote(bill_chamber, date, motion, True, yes_count, no_count,
                    other_count)
        vote['yes_votes'] = yes_votes
        vote['no_votes'] = no_votes
        vote['other_votes'] = other_votes
        return vote,'Good'
