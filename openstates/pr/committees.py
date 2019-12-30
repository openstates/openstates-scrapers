# -*- coding: utf-8 -*-
import re
from pupa.scrape import Scraper, Organization
from openstates.utils import LXMLMixin


class PRCommitteeScraper(Scraper, LXMLMixin):
    def _match_title(self, member):
        # Regexes should capture both gendered forms.
        title_regex = {
            "chairman": r", President.*$",
            "vice chairman": r", Vice President.*$",
            "secretary": r", Secretari.*$",
        }

        for title in title_regex:
            matched_title = None
            match = re.search(title_regex[title], member)

            if match is not None:
                matched_title = title
                member = re.sub(title_regex[title], "", member)
                break

        return member, matched_title

    def scrape(self, chamber=None):
        chambers = [chamber] if chamber is not None else ["upper", "lower"]
        for chamber in chambers:
            yield from getattr(self, "scrape_" + chamber + "_chamber")()

    def scrape_lower_chamber(self):
        url = (
            "http://www.tucamarapr.org/dnncamara/ActividadLegislativa/"
            "ComisionesyProyectosEspeciales.aspx"
        )

        page = self.lxmlize(url)

        # Retrieve links to committee pages.
        links = self.get_nodes(page, '//a[contains(@id, "lnkCommission")]')

        for link in links:
            yield from self.scrape_lower_committee(link.text, link.get("href"))

    def scrape_lower_committee(self, committee_name, url):
        page = self.lxmlize(url)

        committee_name = committee_name.strip()
        comm = Organization(committee_name, chamber="lower", classification="committee")
        comm.add_source(url)

        info_node = self.get_node(
            page,
            './/div[@id = "dnn_ctr1109_ViewWebCommission_WebCommission1_'
            'pnlCommission"]',
        )

        # This will likely capture empty text nodes as well.
        members = self.get_nodes(
            info_node,
            './/div[@class="two-cols com"]/div[@class="col"]//text()'
            "[normalize-space() and preceding-sibling::br]",
        )

        member_count = 0

        for member in members:
            member = re.sub(r"Hon\.\s*", "", member).strip()

            # Skip empty nodes.
            if not member:
                continue

            member, title = self._match_title(member)

            if title is not None:
                comm.add_member(member, title)
            else:
                comm.add_member(member)

            member_count += 1

        if member_count > 0:
            yield comm

    def scrape_upper_chamber(self):
        url = "https://senado.pr.gov/Pages/Comisiones.aspx"
        doc = self.lxmlize(url)
        for link in doc.xpath("//tr/td[1]/a/@href"):
            yield from self.scrape_upper_committee(link)

    def scrape_upper_committee(self, url):
        doc = self.lxmlize(url)
        inner_content = self.get_node(doc, '//section[@class="inner-content"]')
        comm_name = self.get_node(inner_content, ".//h2").text.strip()

        # Remove "Committee" from committee names
        comm_name = (
            comm_name.replace(u"Comisión de ", "")
            .replace(u"Comisión sobre ", "")
            .replace(u"Comisión para ", "")
            .replace(u"Comisión Especial para el Estudio de ", "")
            .replace(u"Comisión Especial para ", "")
            .replace(u"Comisión ", "")
        )
        comm_name = re.sub(r"(?u)^(las?|el|los)\s", "", comm_name)
        comm_name = comm_name[0].upper() + comm_name[1:]

        comm = Organization(comm_name, chamber="upper", classification="committee")
        comm.add_source(url)

        members = self.get_nodes(inner_content, ".//li")
        for member in members:
            name_parts = member.text.split("-")
            name = name_parts[0].replace("Hon. ", "").strip()

            if len(name_parts) > 1:
                title = name_parts[1].strip()

                # Translate titles to English for parity with other states
                if "President" in title:
                    title = "chairman"
                elif title.startswith("Vicepresident"):
                    title = "vicechairman"
                elif title.startswith("Secretari"):
                    title = "secretary"
                else:
                    raise AssertionError("Unknown member type: {}".format(title))

                comm.add_member(name, title)
            else:
                comm.add_member(name)

        yield comm
