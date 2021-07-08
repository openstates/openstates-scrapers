from spatula import HtmlListPage, URL, CSS
from openstates.models import ScrapeCommittee


# class CommitteeDetail():


class CommitteeList(HtmlListPage):
    source = URL("https://www.senate.ca.gov/committees")
    # "https://www.assembly.ca.gov/committees"

    selector = CSS("div .region.region-content > div.block.block-views.clearfix a")

    def process_item(self, item):
        # if item.get("class") != "block block-views clearfix":
        #    self.skip()

        # com_type = CSS(".title-header").match_one(item).text_content()
        # com_list = CSS(".content a").match(item)

        # return CommitteeList(item)

        # divs_to_skip = ["block block-system clearfix", "block block-scgcommittees clearfix"]

        # print(com_type)
        # for committee in com_list:
        com_name = item.text_content()
        detail_link = item.get("href")

        com = ScrapeCommittee(
            name=com_name,
            parent="upper",
        )

        com.add_source(self.source.url)
        com.add_link(detail_link)
        return com
