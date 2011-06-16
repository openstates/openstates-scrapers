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
    ('Aparece en Primera Lectura', 'bill:reading:1'),
    (u'Remitido a Comisión', 'committee:referred'),
    (u'Referido a Comisión', 'committee:referred'),
    ('Enviado al Gobernador', 'governor:received'),
    ('Aprobado por Cámara', 'bill:passed'),
    ('Aprobado por el Senado', 'bill:passed'),
)

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

            action_table = doc.xpath('//table')[-1]
            for row in action_table[1:]:
                tds = row.xpath('td')

                # ignore row missing date
                if len(tds) != 2:
                    continue


                date = datetime.datetime.strptime(tds[0].text_content(),
                                                  "%m/%d/%Y")
                action = tds[1].text_content().strip()
                for pattern, atype in _classifiers:
                    if re.match(pattern, action):
                        break
                else:
                    atype = 'other'
                bill.add_action(chamber, action, date, type=atype)

                # also has an associated version
                if tds[1].xpath('a'):
                    bill.add_version(action, tds[1].xpath('a/@href')[0])

            bill.add_source(url)
            self.save_bill(bill)
