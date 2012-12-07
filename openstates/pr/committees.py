# -*- coding: utf-8 -*-
import lxml.html
import lxml.etree
import os
from billy.scrape import NoDataForPeriod
from billy.scrape.committees import CommitteeScraper, Committee
from billy.scrape.utils import convert_pdf

import re

def clean_spaces(s):
    """ remove \xa0, collapse spaces, strip ends """
    if s is not None:
        return re.sub('\s+', ' ', s.replace(u'\xa0', ' ')).strip()


class PRCommitteeScraper(CommitteeScraper):
    jurisdiction = 'pr'

    def scrape(self, chamber, term):
        self.validate_term(term, latest_only=True)

        if chamber == "upper":
            self.scrape_upper()
        elif chamber == "lower":
            self.scrape_lower()

    def scrape_upper(self):
        self.scrape_upper_committee('http://senadopr.us/SiteCollectionDocuments/Comisiones_Permanentes(2009-2012).pdf')
#       joint_comm = 'http://senadopr.us/SiteCollectionDocuments/Comisiones_Conjuntas(2009-2012).pdf';
#       self.scrape_joint_committee(joint_comm);

    def scrape_joint_committee(self,url):
        filename, resp = self.urlretrieve(url)
        root = lxml.etree.fromstring(convert_pdf(filename,'xml'))
        for link in root.xpath('/pdf2xml/page'):
            comm = None
            self.log(lxml.etree.tostring(root))
            return

    def scrape_upper_committee(self,url):
        filename, resp = self.urlretrieve(url)
        root = lxml.etree.fromstring( convert_pdf(filename,'xml'))
        for link in root.xpath('/pdf2xml/page'):
            comm = None
            for line in link.findall('text'):
                text = line.findtext('b')
                if text is not None and text.startswith('Comisi'):
                    comm = Committee('upper',text);
                    comm.add_source(url)
                else:
                    if line.text and line.text.startswith('Hon.'):
                        line_text = line.text.replace(u'–','-')
                        name_split = line_text.split(u'-',1)
                        title = 'member'
#           print name_split
                        if len(name_split) >= 2:
                            name_split[1] = name_split[1].strip()
                            if name_split[1] == 'Presidenta' or name_split[1] == 'Presidente':
                                title = 'chairman'
                            elif name_split[1] == 'Vicepresidente' or name_split[1] == 'Vicepresidenta':
                                title = 'vicechairman'
                            elif name_split[1] == 'Secretaria' or name_split[1] == 'Secretario':
                                title = 'secretary'
#           if title != 'member':
#               print name_split[0]
                        if name_split[0] != 'VACANTE':
                            comm.add_member(name_split[0].replace('Hon.',''),title)
            self.save_committee(comm)
        os.remove(filename);

    def scrape_lower(self):
        url = 'http://www.camaraderepresentantes.org/comisiones.asp'
        with self.urlopen(url) as html:
            doc = lxml.html.fromstring(html)
            doc.make_links_absolute(url)
            for link in doc.xpath('//a[contains(@href, "comisiones2")]'):
                self.scrape_lower_committee(link.text, link.get('href'))

    def scrape_lower_committee(self, name, url):
        com = Committee('lower', name)
        com.add_source(url)

        with self.urlopen(url) as html:
            doc = lxml.html.fromstring(html)

            contact, directiva, reps = doc.xpath('//div[@class="sbox"]/div[2]')
            # all members are tails of images (they use img tags for bullets)
            # first three members are in the directiva div
            chair = directiva.xpath('b[text()="Presidente:"]/following-sibling::img[1]')
            vchair = directiva.xpath('b[text()="Vice Presidente:"]/following-sibling::img[1]')
            sec = directiva.xpath('b[text()="Secretario(a):"]/following-sibling::img[1]')
            member = 0;
            if chair and chair[0].tail is not None:
                chair = chair[0].tail
                com.add_member(clean_spaces(chair), 'chairman')
                member += 1
            if vchair and vchair[0].tail is not None:
                vchair = vchair[0].tail
                com.add_member(clean_spaces(vchair), 'vice chairman')
                member += 1
            if sec and sec is not None:
                sec = sec[0].tail
                com.add_member(clean_spaces(sec), 'secretary')
                member += 1

            for img in reps.xpath('.//img'):
                member_name = clean_spaces(img.tail)
                if member_name is not None:
                    com.add_member(member_name)
                    member += 1
            if member > 0:
                self.save_committee(com)
