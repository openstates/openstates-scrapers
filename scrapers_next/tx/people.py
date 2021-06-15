from spatula import HtmlListPage, CSS
from ..common.people import PeopleWorkflow


class MemberList(HtmlListPage):
    selector = CSS("#dataListMembers > tbody > tr > td", min_items=32, max_items=150)
    source = "https://capitol.texas.gov/Members/Members.aspx?Chamber="


senate = PeopleWorkflow(MemberList)
