# -*- coding: utf-8 -*-
import re

import os

from billy.scrape.committees import CommitteeScraper, Committee
from billy.scrape.utils import convert_pdf
from openstates.utils import LXMLMixin


def clean_spaces(s):
    """ remove \xa0, collapse spaces, strip ends """
    if s is not None:
        return " ".join(s.split())


class PRCommitteeScraper(CommitteeScraper, LXMLMixin):
    jurisdiction = 'pr'
    latest_only = True

    def scrape(self, chamber, term):
        if chamber == 'upper':
            self.scrape_upper()
        elif chamber == 'lower':
            self.scrape_lower()

    def scrape_upper(self):
        url = 'http://senado.pr.gov/comisiones/Pages/default.aspx'
        doc = self.lxmlize(url)
        for link in doc.xpath('//a[contains(@href, "ComposicionComisiones")]/@href'):
            doc = self.lxmlize(link)
            (pdf_link, ) = doc.xpath('//a[contains(@href,".pdf")]/@href')
            self.scrape_upper_committee(pdf_link)

    def scrape_upper_committee(self, url):
        filename, resp = self.urlretrieve(url)
        lines = convert_pdf(filename, 'text').split('\n')
        comm = None
        comm_name = ''
        title = ''
        for line in (x.decode('utf8') for x in lines):
            line = line.strip()
            if not line.strip():
                continue

            if line.startswith('Comisi'):
                if comm:
                    comm.add_source(url)
                    self.save_committee(comm)
                    comm = None
                    comm_name = ''
                comm_name = line

                # Remove "Committee" from committee names
                comm_name = comm_name.\
                        replace(u"Comisión de ", "").\
                        replace(u"Comisión Conjunta sobre ", "").\
                        replace(u"Comisión Especial para el Estudio de ", "").\
                        replace(u"Comisión Especial para ", "")
                comm_name = re.sub(r'(?u)^(las?|el|los)\s', "", comm_name)
                comm_name = comm_name[0].upper() + comm_name[1: ]

            # Committee president is always listed right after committee name
            elif not comm and comm_name and not line.startswith("President"):
                comm_name = comm_name + " " + line
            elif not comm and line.startswith("President"):
                comm = Committee('upper', comm_name)

            if comm:
                assert re.search(r'(?u)Hon\.?\s\w', line)
                (temp_title, name) = line.split("Hon")
                name = name.strip(". ")

                if temp_title.strip():
                    title = temp_title

                    # Translate titles to English for parity with other states
                    if title.startswith("President"):
                        title = 'chairman'
                    elif title.startswith("Vicepresident"):
                        title = 'vicechairman'
                    elif title.startswith("Secretari"):
                        title = 'secretary'
                    elif "Miembr" in title:
                        title = 'member'
                    else:
                        raise AssertionError("Unknown member type: {}".
                                format(title))

                # Many of the ex-officio members have appended titles
                if ", " in name:
                    name = name.split(", ")[0]

                if name.lower() != 'vacante':
                    comm.add_member(name, title)

        os.remove(filename)

    def scrape_lower(self):
        url = 'http://www.camaraderepresentantes.org/comisiones.asp'
        doc = self.lxmlize(url)
        for link in doc.xpath('//a[contains(@href, "comisiones2")]'):
            self.scrape_lower_committee(link.text, link.get('href'))

    def scrape_lower_committee(self, name, url):
        com = Committee('lower', name)
        com.add_source(url)
        doc = self.lxmlize(url)

        contact, directiva, reps = doc.xpath('//div[@class="sbox"]/div[2]')
        # all members are tails of images (they use img tags for bullets)
        # first three members are in the directiva div
        chair = directiva.xpath('b[text()="Presidente:"]/following-sibling::img[1]')
        vchair = directiva.xpath('b[text()="Vice Presidente:"]/following-sibling::img[1]')
        sec = directiva.xpath('b[text()="Secretario(a):"]/following-sibling::img[1]')
        member = 0
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
