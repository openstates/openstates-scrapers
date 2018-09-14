# -*- coding: utf-8 -*-
import re
import lxml.html
import datetime
import itertools
from pupa.scrape import Scraper, Bill, VoteEvent as Vote


class NoSuchBill(Exception):
    pass


_voteChambers = (
    (u'Aprobado por el Senado en Votac', 'upper'),
    (u'Aprobado por C', 'lower'),
)

_docVersion = (
    ('Entirillado del Informe'),
    ('Texto de Aprobaci'),
    # ('Ley N'),
    ('rendido con enmiendas'),
    ('Radicado'),
)

_classifiers = (
    ('Radicado', '', 'introduction'),
    (u'Aprobado por Cámara en Votación Final', 'lower', 'passage'),
    (u'Aprobado por el Senado en Votación', 'upper', 'passage'),
    ('Aparece en Primera Lectura del', 'upper', 'reading-1'),
    ('Aparece en Primera Lectura de la', 'lower', 'reading-1'),
    ('Enviado al Gobernador', 'executive', 'executive-receipt'),
    ('Veto', 'executive', 'executive-veto'),
    ('Veto de Bolsillo', 'executive', 'executive-veto'),
    # comissions give a report but sometimes they dont do any amendments and
    # leave them as they are.
    # i am not checking if they did or not. but it be easy just read the end and
    # if it dosnt have amendments it should say 'sin enmiendas'
    ('1er Informe', '', 'amendment-amendment'),
    ('2do Informe', '', 'amendment-amendment'),
    ('Aprobado con enmiendas', '', 'amendment-passage'),
    (u'Remitido a Comisión', '', 'referral-committee'),
    (u'Referido a Comisión', '', 'referral-committee'),
    ('Retirada por su Autor', '', 'withdrawal'),
    ('Comisión : * no recomienda aprobación de la medida', '', 'committee-passage-unfavorable'),
    ('Ley N', 'executive', 'executive-signature')
)


class PRBillScraper(Scraper):

    bill_types = {
        'P': 'bill',
        'R': 'resolution',
        'RK': 'concurrent resolution',
        'RC': 'joint resolution',
        # 'PR': 'plan de reorganizacion',
    }

    def clean_name(self, name):
        for ch in ['Sr,', 'Sr.', 'Sra.', 'Rep.', 'Sen.']:
            if ch in name:
                name = name.replace(ch, '')
        return name

    def scrape(self, session=None, chamber=None):
        if not session:
            session = self.latest_session()
            self.info('no session specified using %s', session)
        chambers = [chamber] if chamber is not None else ['upper', 'lower']
        for chamber in chambers:
            yield from self.scrape_chamber(chamber, session)

    def scrape_chamber(self, chamber, session):
        year = session[0:4]
        self.base_url = 'http://www.oslpr.org/legislatura/tl%s/tl_medida_print2.asp' % year
        chamber_letter = {'lower': 'C', 'upper': 'S'}[chamber]
        for code, bill_type in self.bill_types.items():
            counter = itertools.count(1)
            for n in counter:
                bill_id = '%s%s%s' % (code, chamber_letter, str(n).zfill(4))
                try:
                    yield from self.scrape_bill(chamber, session, bill_id, bill_type)
                except NoSuchBill:
                    if n == 1:
                        self.warning("Found no bills of type '{}'".format(bill_type))
                    break

    def parse_action(self, chamber, bill, action, action_url, date):
        # if action.startswith('Referido'):
                # committees = action.split(',',1)
                # multiple committees
        if action.startswith('Ley N'):
                action = action[0:42]
        elif action.startswith('Res. Conj.'):
                action = action[0:42]
        action_actor = ''
        atype = None
        # check it has a url and is not just text
        if action_url:
            action_url = action_url[0]
            isVersion = False
            for text_regex in _docVersion:
                if re.match(text_regex, action):
                    isVersion = True
            if isVersion:
                # versions are mentioned several times, lets use original name
                erroneous_filename = False
                action_url = action_url.lower().strip()
                if action_url.endswith(('.doc', 'dot')):
                    media_type = 'application/msword'
                elif action_url.endswith('.rtf'):
                    media_type = 'application/rtf'
                elif action_url.endswith('.pdf'):
                    media_type = 'application/pdf'
                elif action_url.endswith(('docx', 'dotx')):
                    media_type = 'application/vnd.openxmlformats-officedocument' + \
                                 '.wordprocessingml.document'
                elif action_url.endswith('docm'):
                    self.warning("Erroneous filename found: {}".format(action_url))
                    erroneous_filename = True
                else:
                    raise Exception('unknown version type: %s' % action_url)
                if not erroneous_filename:
                    bill.add_version_link(note=action, url=action_url,
                                          media_type=media_type, on_duplicate='ignore')
            else:
                bill.add_document_link(action, action_url, on_duplicate='ignore')
            for pattern, action_actor, atype in _classifiers:
                if re.match(pattern, action):
                    break
                else:
                    action_actor = ''
                    atype = None
        if action_actor == '':
            if action.find('SENADO') != -1:
                action_actor = 'upper'
            elif action.find('CAMARA') != -1:
                action_actor = 'lower'
            else:
                action_actor = chamber

        # manual fix for data error on 2017-2020 P S0623
        if date == datetime.datetime(1826, 8, 1):
            date = date.replace(year=2018)

        bill.add_action(description=action.replace('.', ''),
                        date=date.strftime('%Y-%m-%d'),
                        chamber=action_actor,
                        classification=atype)
        return atype, action

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

        bill = Bill(bill_id,
                    legislative_session=session,
                    chamber=chamber,
                    title=title[0],
                    classification=bill_type)

        author = doc.xpath(u'//td/b[contains(text(),"Autor")]/../text()')[0]
        for aname in author.split(','):
            aname = self.clean_name(aname).strip()
            if aname:
                bill.add_sponsorship(aname, classification='primary',
                                     entity_type='person', primary=True)

        co_authors = doc.xpath(u'//td/b[contains(text(),"Co-autor")]/../text()')
        if len(co_authors) != 0:
            for co_author in co_authors[1].split(','):
                bill.add_sponsorship(self.clean_name(co_author).strip(),
                                     classification='cosponsor',
                                     entity_type='person', primary=False)

        action_table = doc.xpath('//table')[-1]
        bill_vote_chamber = None
        for row in action_table[1:]:
            tds = row.xpath('td')
            # ignore row missing date
            if len(tds) != 2:
                continue
            if tds[0].text_content():
                date = datetime.datetime.strptime(tds[0].text_content(), "%m/%d/%Y")
            action = tds[1].text_content().strip()
            # parse the text to see if it's a new version or a unrelated document
            # if has a hyphen let's assume it's a vote document

            # get url of action
            action_url = tds[1].xpath('a/@href')
            atype, action = self.parse_action(chamber, bill, action, action_url, date)

            # Some lower-house roll calls could be parsed, but finnicky
            # Most roll lists are just images embedded within a document,
            # and offer no alt text to scrape
            # Instead, just scrape the vote counts
            regex = r'(?u)^(.*),\s([\s\d]{2})-([\s\d]{2})-([\s\d]{2})-([\s\d]{0,2})$'
            vote_info = re.search(regex, action)
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

                # TODO replace bill['votes']
                elif u"Se reconsideró" in vote_name:
                    if bill_vote_chamber:
                        vote_chamber = bill_vote_chamber
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
                    start_date=date.strftime('%Y-%m-%d'),
                    motion_text=vote_name,
                    result='pass' if (yes > no) else 'fail',
                    bill=bill,
                    classification='passage',
                )
                vote.set_count('yes', yes)
                vote.set_count('no', no)
                vote.set_count('other', other)
                vote.add_source(url)
                yield vote
                bill_vote_chamber = chamber

        bill.add_source(url)
        yield bill
