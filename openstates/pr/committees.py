# -*- coding: utf-8 -*-
import re
import os
from billy.scrape.committees import CommitteeScraper, Committee
from billy.scrape.utils import convert_pdf
from openstates.utils import LXMLMixin


class PRCommitteeScraper(CommitteeScraper, LXMLMixin):
    jurisdiction = 'pr'
    latest_only = True

    def _clean_spaces(self, string):
        """ Remove \xa0, collapse spaces, strip ends. """
        if string is not None:
            return ' '.join(string.split())

    def _match_title(self, member):
        # Regexes should capture both gendered forms.
        title_regex = {
            'chairman': r', President.*$',
            'vice chairman': r', Vice President.*$',
            'secretary': r', Secretari.*$'
        }

        for title in title_regex:
            matched_title = None
            match = re.search(title_regex[title], member)

            if match is not None:
                matched_title = title
                member = re.sub(title_regex[title], '', member)
                break

        return member, matched_title

    def scrape(self, chamber, term):
        getattr(self, 'scrape_' + chamber + '_chamber')()

    def scrape_lower_chamber(self):
        url = 'http://www.tucamarapr.org/dnncamara/ActividadLegislativa/'\
            'ComisionesyProyectosEspeciales.aspx'

        page = self.lxmlize(url)

        # Retrieve links to committee pages.
        links = self.get_nodes(
            page,
            '//a[contains(@id, "lnkCommission")]')

        for link in links:
            self.scrape_lower_committee(link.text, link.get('href'))

    def scrape_lower_committee(self, committee_name, url):
        page = self.lxmlize(url)

        committee_name = committee_name.strip()
        committee = Committee('lower', committee_name)
        committee.add_source(url)

        info_node = self.get_node(
            page,
            './/div[@id = "dnn_ctr1109_ViewWebCommission_WebCommission1_'
            'pnlCommission"]')

        # This will likely capture empty text nodes as well.
        members = self.get_nodes(
            info_node,
            './/div[@class="two-cols com"]/div[@class="col"]//text()'
            '[normalize-space() and preceding-sibling::br]')

        member_count = 0

        for member in members:
            member = re.sub(r'Hon\.\s*', '', member).strip()

            # Skip empty nodes.
            if not member:
                continue

            member, title = self._match_title(member)

            if title is not None:
                committee.add_member(member, title)
            else:
                committee.add_member(member)
            
            member_count += 1

        if member_count > 0:
            self.save_committee(committee)

    def scrape_upper_chamber(self):
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
        MINIMUM_NAME_LENGTH = len('Hon _ _')

        for line in (x.decode('utf8') for x in lines):
            line = line.strip()
            if not line.strip():
                continue

            if (line.startswith('Comisi') or
                    line.startswith('COMISIONES') or
                    line.startswith('SECRETAR')):

                if comm:
                    # Joint committee rosters are not complete, unfortunately
                    if "Conjunta" not in comm_name:
                        self.save_committee(comm)
                    comm = None
                    comm_name = ''

                if not (line.startswith('COMISIONES') or
                        line.startswith('SECRETAR')):
                    comm_name = line

                    # Remove "Committee" from committee names
                    comm_name = (
                        comm_name.
                        replace(u"Comisión de ", "").
                        replace(u"Comisión Especial para el Estudio de ", "").
                        replace(u"Comisión Especial para ", "")
                    )
                    comm_name = re.sub(r'(?u)^(las?|el|los)\s', "", comm_name)
                    comm_name = comm_name[0].upper() + comm_name[1:]

            # Committee president is always listed right after committee name
            elif (not comm and
                    comm_name and
                    not re.search(r'^(?:Co.)?President', line) and
                    not line.startswith('Miembr')):
                comm_name = comm_name + " " + line

            elif (not comm and
                    (re.search(r'^(?:Co.)?President', line) or
                     line.startswith('Miembr')) and
                    len(line) > len('Presidente ') + MINIMUM_NAME_LENGTH):
                comm = Committee('upper', comm_name)
                comm.add_source(url)

            if comm:
                assert re.search(r'(?u)Hon\.?\s\w', line)
                (temp_title, name) = line.split("Hon")
                name = name.strip(". ")

                if temp_title.strip():
                    title = temp_title

                    # Translate titles to English for parity with other states
                    if "President" in title:
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

        if comm and "Conjunta" not in comm_name:
            self.save_committee(comm)

        os.remove(filename)
