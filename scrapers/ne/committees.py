import re

from openstates_core.scrape import Scraper, Organization

from scrapers.utils import LXMLMixin


class NECommitteeScraper(Scraper, LXMLMixin):
    def _scrape_standing_committees(self):
        """Scrapes the Standing Committees page of the Nebraska state
        legislature."""
        main_url = (
            "http://www.nebraskalegislature.gov/committees/standing-committees.php"
        )
        page = self.lxmlize(main_url)

        committee_nodes = self.get_nodes(
            page,
            '//a[@class="accordion-switch"][contains(text(), "Standing Committees")]'
            '/ancestor::div[@class="panel panel-leg"]//div[@class="list-group"]'
            '/a[@class="list-group-item"]',
        )

        for committee_node in committee_nodes:
            committee_page_url = committee_node.attrib["href"]
            committee_page = self.lxmlize(committee_page_url)

            name_text = self.get_node(
                committee_page,
                '//div[@class="container view-front"]/div[@class="row"]/'
                'div[@class="col-sm-6 col-md-7"]/h1/text()[normalize-space()]',
            )
            name = name_text.split()[0:-1]

            committee_name = ""
            for x in range(len(name)):
                committee_name += name[x] + " "
            committee_name = committee_name[0:-1]

            org = Organization(
                name=committee_name, chamber="legislature", classification="committee"
            )

            members = self.get_nodes(
                committee_page,
                '//div[@class="col-sm-4 col-md-3 ltc-col-right"][1]/'
                'div[@class="block-box"][1]/ul[@class="list-unstyled '
                'feature-content"]/li/a/text()[normalize-space()]',
            )

            for member in members:
                member_name = re.sub(r"\Sen\.\s+", "", member)
                member_name = re.sub(r", Chairperson", "", member_name).strip()
                if "Chairperson" in member:
                    member_role = "Chairperson"
                else:
                    member_role = "member"
                org.add_member(member_name, member_role)

            org.add_source(main_url)
            org.add_source(committee_page_url)

            yield org

    def _scrape_select_special_committees(self):
        """Scrapes the Select and Special Committees page of the
        Nebraska state legislature."""
        main_url = "http://www.nebraskalegislature.gov/committees/select-committees.php"
        page = self.lxmlize(main_url)

        committee_nodes = self.get_nodes(
            page,
            '//a[contains(@class, "accordion-switch")]'
            '/ancestor::div[@class="panel panel-leg"]',
        )

        for committee_node in committee_nodes:
            committee_name = self.get_node(
                committee_node, './/h2[@class="panel-title"]/text()[normalize-space()]'
            )

            if committee_name is None:
                committee_name = self.get_node(
                    committee_node,
                    './/h2[@class="panel-title"]/a/text()[normalize-space()]',
                )

            org = Organization(
                name=committee_name, chamber="legislature", classification="committee"
            )
            org.add_source(main_url)

            members = self.get_nodes(
                committee_node,
                './/a[@class="list-group-item"]' "/text()[normalize-space()]",
            )

            for member in members:
                member_name = re.sub(r"\Sen\.\s+", "", member)
                member_name = re.sub(r", Chairperson", "", member_name).strip()
                if "Chairperson" in member:
                    member_role = "Chairperson"
                else:
                    member_role = "member"
                org.add_member(member_name, member_role)

            if not org._related:
                self.warning("No members found in {} committee.".format(org.name))
            else:
                yield org

    def scrape(self):
        yield from self._scrape_standing_committees()
        yield from self._scrape_select_special_committees()
