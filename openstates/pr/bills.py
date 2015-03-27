# -*- coding: utf-8 -*-
from billy.scrape.votes import Vote
from billy.scrape.bills import BillScraper, Bill

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
    jurisdiction = 'pr'

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
                erroneous_filename = False
                action_url = action_url.lower().strip()
                if action_url.endswith('.doc'):
                    mimetype = 'application/msword'
                elif action_url.endswith('.rtf'):
                    mimetype = 'application/rtf'
                elif action_url.endswith('.pdf'):
                    mimetype = 'application/pdf'
                elif action_url.endswith('docx'):
                    mimetype = 'application/octet-stream'
                elif action_url.endswith('docm'):
                    self.warning("Erroneous filename found: {}".format(action_url))
                    erroneous_filename = True
                else:
                    raise Exception('unknown version type: %s' % action_url)
                if not erroneous_filename:
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
        html = self.get(url).text
        if "error '80020009'" in html:
            self.warning('asp error on page, skipping %s', bill_id)
            return
        doc = lxml.html.fromstring(html)
        # search for Titulo, accent over i messes up lxml, so use 'tulo'
        title = doc.xpath(u'//td/b[contains(text(),"tulo")]/../following-sibling::td/text()')
        if not title:
            raise NoSuchBill()
        bill = Bill(session, chamber, bill_id, title[0], type=bill_type)
        author = doc.xpath(u'//td/b[contains(text(),"Autor")]/../text()')[0]
        for aname in author.split(','):
            aname = self.clean_name(aname).strip()
            if aname:
                bill.add_sponsor('primary', aname)
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
            if tds[0].text_content():
                date = datetime.datetime.strptime(tds[0].text_content(), "%m/%d/%Y")
            action = tds[1].text_content().strip()
            #parse the text to see if it's a new version or a unrelated document
            #if has a hyphen let's assume it's a vote document

            #get url of action
            action_url = tds[1].xpath('a/@href')
            atype,action = self.parse_action(chamber,bill,action,action_url,date)

            # Some lower-house roll calls could be parsed, but finnicky
            # Most roll lists are just images embedded within a document,
            # and offer no alt text to scrape
            # Instead, just scrape the vote counts
            vote_info = re.search(r'(?u)^(.*),\s([\s\d]{2})-([\s\d]{2})-([\s\d]{2})-([\s\d]{0,2})$', action)
            if vote_info and re.search(r'\d{1,2}', action):
                vote_name = vote_info.group(1)

                if u"Votación Final" in vote_name:
                    (vote_chamber, vote_name) = re.search(
                            r'(?u)^\w+ por (.*?) en (.*)$', vote_name).groups()
                    if "Senado" in vote_chamber:
                        vote_chamber = 'upper'
                    else:
                        vote_chamber = 'lower'

                elif "Cuerpo de Origen" in vote_name:
                    vote_name = re.search(
                            r'(?u)^Cuerpo de Origen (.*)$', vote_name).group(1)
                    vote_chamber = chamber

                elif u"informe de Comisión de Conferencia" in vote_name:
                    (vote_chamber, vote_name) = re.search(
                            r'(?u)^(\w+) (\w+ informe de Comisi\wn de Conferencia)$',
                            vote_name).groups()
                    if vote_chamber == "Senado":
                        vote_chamber = 'upper'
                    else:
                        vote_chamber = 'lower'

                elif u"Se reconsideró" in vote_name:
                    if bill['votes']:
                        vote_chamber = bill['votes'][-1]['chamber']
                    else:
                        vote_chamber = chamber

                else:
                    raise AssertionError(
                            u"Unknown vote text found: {}".format(vote_name))

                vote_name = vote_name.title()

                yes = int(vote_info.group(2))
                no = int(vote_info.group(3))
                other = 0
                if vote_info.group(4).strip():
                    other += int(vote_info.group(4))
                if vote_info.group(5).strip():
                    other += int(vote_info.group(5))

                vote = Vote(
                        chamber=vote_chamber,
                        date=date,
                        motion=vote_name,
                        passed=(yes > no),
                        yes_count=yes,
                        no_count=no,
                        other_count=other
                        )
                vote.add_source(url)
                bill.add_vote(vote)

        bill.add_source(url)
        self.save_bill(bill)
