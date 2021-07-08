from spatula import HtmlListPage, URL, CSS, XPath
from openstates.models import ScrapeCommittee


class CommitteeDetail(HtmlListPage):
    # selector = XPath("//[text()='Members:']/following-sibling/a")
    selector = XPath(
        '//a[(contains(@href, "/sd") or '
        'contains(@href, "assembly.ca.gov/a")) and '
        '(starts-with(text(), "Senator") or '
        'starts-with(text(), "Assembly Member"))]/text()'
    )
    # "//*[@id="node-182047"]/div/div/div/div/p[11]/a[1]"
    # "//*[@id="node-39"]/div/div/div/div/p[25]/a[8]"
    # "//*[@id="node-39"]/div/div/div/div/p[25]/a[9]"

    def process_item(self, item):
        com = self.input
        # print(item)
        member_name = item.lstrip("Senator ")
        # member_name = item.text_content().lstrip("Senator ")
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
            # "https://sbp.senate.ca.gov" # h3 instread of h2,
            # "https://selc.senate.ca.gov" # different format,
            # "https://senv.senate.ca.gov" # different members heading,
            # "https://shea.senate.ca.gov" # h3 p a instead of h2 p a,
            # "https://sjud.senate.ca.gov" # h4 h4 a instead of h2 p a,
            # "https://spsf.senate.ca.gov" # members is p instead of h2,
            # "https://census.senate.ca.gov/" # ul li instead of p a,
            # "https://www.senate.ca.gov/domestic-violence",
            # "https://www.senate.ca.gov/hydrogen-energy",
            # "https://www.senate.ca.gov/mental-health-and-addiction",
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

        # this is being added for each member (only do once)
        com.add_source(self.source.url)
        com.add_link(detail_link)
        # add link as a source as well

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
