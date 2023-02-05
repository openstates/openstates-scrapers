"""
This initial commit is the starting contribution from first-time
Open States contributor, GH user @fvescia.

Open-source contributions to complete this scraper
are welcome and encouraged!

If you have any questions, you can comment on the draft PR,
or on the original GH issue for this scraper at url:
https://github.com/openstates/issues/issues/889
"""


# from spatula import HtmlPage, HtmlListPage, CSS, XPath, SelectorError, URL
# from openstates.models import ScrapeCommittee
#
#
# class SenateCommitteeList(HtmlListPage):
#     source = "https://www.scstatehouse.gov/committee.php?chamber=S"
#     selector = XPath("//h4/a")
#     chamber = "upper"
#
#     def process_item(self, item):
#         committees = item.text_content()
#         for com in committees:
#             return SenateCommitteeDetail(source=URL(item.get("href"), timeout=30))
#
#
# class SenateCommitteeDetail(HtmlPage):
#     example_source = "https://www.scstatehouse.gov/CommitteeInfo/senateagri.php"
#
#     # REQUESTED INFO: THOUGHTS / NOTES
#     # name: set in process_page, xpath should be ("//head/title")?
#     # chamber: hardcode in SenateCommitteeList?
#     # classification (committee or subcommittee):
#     #  as of 1/29/2023, only the Senate finance committe has subcommittees,
#     #  see Word Doc linked on https://www.scstatehouse.gov/committee.php?chamber=S
#     # parent (if subcommittee)
#     # source: add using add_source in process_page?
#     # members: add using add_member()method on instance of
#     #  ScrapeCommittee type object, xpath should be
#     #  ("//body//div[@id='contentsection']//a[@style='font-size: 12px;'")?
#
#     def process_page(self):
#         com = self.input
#         com.add_source(self.source.url, note="Committee Details Page")
