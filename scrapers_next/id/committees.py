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
    def process_page(self):
        com = self.input
        tet = XPath(
            '//div[@class="wpb_column vc_column_container col-xs-mobile-fullwidth col-sm-8 text-left sm-text-left '
            'xs-text-center padding-three"]//p/strong/a').match(
            self.root)
        for t in tet:
            print(t.text)
        #
        # p_path = ['//*[@id="hcode-tab-style2members"]/div/div/div/div/section',
        #           '//*[@id="hcode-tab-style2members"]/div/div/div/section'
        #           ]
        # # //*[@id="hcode-tab-style2members"]/div/div/div/div/section[8]/div[1]/div/div/div[2]/div/p/strong/a
        # for pth in p_path:
        #     try:
        #         sections = len(XPath(pth).match(self.root))
        #     except SelectorError:
        #         continue
        #     for sec in range(2, sections):
        #         div_path = f"{pth}[{sec}]/div"
        #         div_length = len(XPath(div_path).match(self.root))
        #         for i in range(1, div_length):
        #             name_path = f"{div_path}[{i}]/div/div/div[2]/div/p/strong/a"
        #             name = XPath(name_path).match(self.root)[0].text
        #             print(name)
        com.add_source(
            self.source.url,
            note="Committee Details page",
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
            comm = XPath(f"//a[contains(@href, '/standingcommittees/')]").match(fromstring(document))
            if comm_type == "house":
                chamber = "lower"
            else:
                chamber = "upper"
        else:
            chamber = "legislature"
            comm = XPath(f"//a[contains(@href, '/{comm_type}/')]").match(fromstring(document))

        for url in comm:
            yield url.text, self.main_website + url.get("href"), chamber

    def process_page(self):
        committees = ["senate", "house", "joint", "interim"]
        comm = {}
        for comm_type in committees:
            committees_url = XPath(f"//a[contains(@href, '/committees/{comm_type}committees/')]").match(self.root)
            for url in committees_url:
                if url.text and not comm.get(url.get("href")):
                    comm[url.get("href")] = (url.text, comm_type)

        all_committees = [(self.leg_council_name, self.leg_council, self.leg_council_type)]
        for url, data in comm.items():
            all_committees += self.extract_committees(url, data[1])
            break
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
                data[1],
                note="Committees from legislature.idaho.gov site",
            )
            members_source = f"{data[1]}#hcode-tab-style2members"
            yield CommitteeDetail(com, source=URL(members_source, timeout=15))


if __name__ == '__main__':
    c = CommitteeList()
    for i in c.do_scrape():
        print(i)
