from spatula import HtmlListPage, URL, CSS, XPath
from openstates.models import ScrapeCommittee


class CommitteeDetail(HtmlListPage):
    selector = XPath("//h2[text()='Members:']/following-sibling::p/a")
    # "//*[@id="node-182047"]/div/div/div/div/p[11]/a[1]"

    def process_item(self, item):
        com = self.input
        com.add_source(self.source.url)

        member_name = item.text_content().rstrip("Senator ")
        com.add_member(name=member_name)
        return com

        # print(member_name)
        # if member_name.contains("(") and member_name.contains(")"):

        # print(item)


class CommitteeList(HtmlListPage):
    source = URL("https://www.senate.ca.gov/committees")
    # "https://www.assembly.ca.gov/committees"

    selector = CSS("div .region.region-content > div.block.block-views.clearfix a")

    def process_item(self, item):
        com_type = (
            item.getparent()
            .getparent()
            .getparent()
            .getparent()
            .getparent()
            .getparent()
            .getparent()
            .text_content()
            .strip()
            .split("\n")[0]
            .strip()
        )

        com_name = item.text_content()
        detail_link = item.get("href")
        different_xml = [
            "https://sbp.senate.ca.gov",
            "https://selc.senate.ca.gov",
            "https://senv.senate.ca.gov",
            "https://shea.senate.ca.gov",
            "https://sjud.senate.ca.gov",
            "https://spsf.senate.ca.gov",
            "https://census.senate.ca.gov/",
            "https://www.senate.ca.gov/domestic-violence",
            "https://www.senate.ca.gov/hydrogen-energy",
            "https://www.senate.ca.gov/mental-health-and-addiction",
            "http://assembly.ca.gov/fairsallocation",
            "http://fisheries.legislature.ca.gov/",
            "https://jtrules.legislature.ca.gov",
            "http://arts.legislature.ca.gov/",
            "http://legaudit.assembly.ca.gov/",
            "https://jtlegbudget.legislature.ca.gov/",
            "http://climatechangepolicies.legislature.ca.gov",
            "https://jtemergencymanagement.legislature.ca.gov/",
        ]
        if detail_link in different_xml:
            self.skip()

        com = ScrapeCommittee(
            name=com_name,
            parent="upper",
        )

        com.add_source(self.source.url)
        com.add_link(detail_link)

        # print(com_type)
        """
        if com_type == "Sub Committees":
            # com_type = com_type.lower()
            com.classification = "subcommittee"
        elif com_type != "Standing Committees":
            com.extras['Committee Type'] = com_type.lower()
        """
        com.extras["Committee Type"] = com_type.lower()

        source = URL(detail_link)
        # print(source)
        # if source == "https://sbp.senate.ca.gov":
        #    return com
        # else:
        return CommitteeDetail(com, source=source)
