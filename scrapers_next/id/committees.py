from lxml import html
from spatula import URL, HtmlListPage, HtmlPage, XPath, SelectorError, SkipItem
from openstates.models import ScrapeCommittee
from lxml.html import fromstring
import requests


class SubcommitteeFound(BaseException):
    def __init__(self, com_name):
        super().__init__(
            f"Scraper has no process for ingesting subcommittee classification: {com_name}"
        )


class CommitteeDetail(HtmlPage):
    def process_error_response(self, exception):
        self.logger.warning(exception)

    def process_page(self):
        com = self.input
        name_path = '//div[@class="wpb_column vc_column_container col-xs-mobile-fullwidth col-sm-8 text-left sm-text-left xs-text-center padding-three"]//p/strong/a'
        role_path = '//div[@class="wpb_column vc_column_container col-xs-mobile-fullwidth col-sm-8 text-left sm-text-left xs-text-center padding-three"]//p/strong/text()'
        name_list = []
        role_list = []
        try:
            name_list = XPath(name_path).match(self.root)
            role_list = XPath(role_path).match(self.root)
        except SelectorError:
            try:

                name_list = XPath(role_path.replace("/text()", "")).match(self.root)
                role_list = ["Member" for x in name_list]
            except SelectorError:

                root = html.fromstring(self.root.text_content())
                try:
                    name_list = XPath(name_path).match(root)
                    role_list = XPath(role_path).match(root)
                except SelectorError:
                    try:
                        name_list = XPath(".//p/strong/a").match(root)
                        role_list = []
                        for name in name_list:
                            full_strong = name.getparent().text_content().strip()
                            raw_role = full_strong.removeprefix(
                                name.text.strip()
                            ).strip()
                            role = raw_role or "Member"
                            role_list.append(role)
                    except SelectorError:
                        SkipItem("empty committee")
        for i in range(len(name_list)):
            try:
                role_list[i]
            except IndexError:
                role_list.append("Member")
        for name, role in zip(name_list, role_list):
            name = name.text
            for rep in ["Rep.", "Sen."]:
                name = name.replace(rep, "")
            name = name.strip()
            role = role.replace(",", "").replace("– ", "").strip()
            if not role or not len(role.strip()):
                role = "Member"
            com.add_member(name, role)

        if not com.members:
            raise SkipItem(f"empty committee: {com.name}")
        com.add_source(
            self.source.url,
            note="Committee Details page",
        )
        com.add_link(
            self.source.url,
            note="homepage",
        )

        if not com.members:
            raise SkipItem(f"empty committee: {com.name}")
        com.add_source(
            self.source.url,
            note="Committee Details page",
        )
        com.add_link(
            self.source.url,
            note="homepage",
        )
        return com


class CommitteeList(HtmlListPage):
    source = URL("https://legislature.idaho.gov/committees/", timeout=15)
    main_website = "https://legislature.idaho.gov"

    leg_council = "https://legislature.idaho.gov/legcouncil/"
    leg_council_name = "Legislative Council"
    leg_council_type = "legislature"

    def extract_committees(self, url, comm_type):
        document = requests.get(url).content
        if comm_type in ["house", "senate"]:
            comm = XPath("//a[contains(@href, '/standingcommittees/')]").match(
                fromstring(document)
            )
            if comm_type == "house":
                chamber = "lower"
            else:
                chamber = "upper"
        else:
            chamber = "legislature"
            comm = XPath(f"//a[contains(@href, '/{comm_type}/')]").match(
                fromstring(document)
            )

        for url in comm:
            yield url.text, self.main_website + url.get("href"), chamber

    def process_page(self):
        committees = ["house", "senate", "joint", "interim"]
        comm = {}
        for comm_type in committees:
            committees_url = XPath(
                f"//a[contains(@href, '/committees/{comm_type}committees/')]"
            ).match(self.root)
            for url in committees_url:
                if url.text and not comm.get(url.get("href")):
                    comm[url.get("href")] = (url.text, comm_type)

        all_committees = [
            (self.leg_council_name, self.leg_council, self.leg_council_type)
        ]
        for url, data in comm.items():
            all_committees += self.extract_committees(url, data[1])

        for data in all_committees:
            if "subcommittee" in data[0]:
                raise SubcommitteeFound(data[0])
            com = ScrapeCommittee(
                name=data[0],
                chamber=data[2],
                parent=None,
                classification="committee",
            )

            com.add_source(
                self.source.url,
                note="homepage",
            )
            members_source = f"{data[1]}#hcode-tab-style2members"
            yield CommitteeDetail(com, source=URL(members_source, timeout=15))
