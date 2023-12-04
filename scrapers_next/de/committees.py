from spatula import (
    JsonPage,
    HtmlPage,
    XPath,
    URL,
    SelectorError,
    SkipItem,
)
from openstates.models import ScrapeCommittee


class CommitteeJsonData(JsonPage):
    def process_page(self):
        for committee in self.response.json().get("Data"):
            name = committee.get("CommitteeName")
            id = committee.get("CommitteeId")

            com = ScrapeCommittee(
                name=name,
                classification="committee",
                chamber=self.input.get("chamber"),
            )
            com.add_source(self.source.url, note="Committee json data")

            link = f"https://legis.delaware.gov/CommitteeDetail?committeeId={id}"
            yield CommitteeMembers(com, source=URL(link, timeout=30))


class CommitteeMembers(HtmlPage):
    def process_page(self):
        com = self.input

        # Add sources and links for current page
        com.add_source(self.source.url, note="Member list page")
        com.add_link(self.source.url, note="homepage")

        # Members are organized by role
        # If any of these selectors fail, assume that there are no members of
        # that type listed on the page
        chairs = []
        try:
            chairs = XPath(
                "//div[@class='info-group']/label[text()='Chair:']/../div[@class='info-value']/a/text()"
            ).match(self.root)
        except SelectorError:
            pass

        vice_chairs = []
        try:
            vice_chairs = XPath(
                "//div[@class='info-group']/label[text()='Vice-Chair(s):']/../div[@class='info-value']/a/text()"
            ).match(self.root)
        except SelectorError:
            pass

        members = []
        try:
            members = XPath(
                "//div[@class='info-group']/label[text()='Members:']/../div[@class='info-value']/a/text()"
            ).match(self.root)
        except SelectorError:
            pass

        # Add all the members found for each role
        for name in chairs:
            com.add_member(name=name, role="Chair")
        for name in vice_chairs:
            com.add_member(name=name, role="Vice-Chair")
        for name in members:
            com.add_member(name=name, role="Member")

        # Check to make sure there was at least one member
        if len(com.members) == 0:
            raise SkipItem(f"No member data for: {com.name}")

        return com


class CommitteeList(HtmlPage):
    # This page is scraped before getting the json data because the current
    # session id needs to be extracted. This page has a <select> element where
    # the first <option> inside of it has the required session id.
    source = "https://legis.delaware.gov/Committees"

    def process_page(self):
        # Get current legislative session from a <select> element
        session_id = XPath("//*[@id='committeesGARefiner']/option[1]/@value").match_one(
            self.root
        )

        # Build query to send to the API
        source = URL(
            "https://legis.delaware.gov/json/Committees/GetCommitteesByTypeId?ga=",
            timeout=30,
            method="POST",
            headers={
                "Content-Type": "application/x-www-form-urlencoded;",
                "charset": "UTF-8",
            },
            data=f"sort=&group=&filter=&assemblyId={session_id}&committeeTypeId={self.committeeTypeId}",
        )

        # Yield all committee results
        yield CommitteeJsonData({"chamber": self.chamber}, source=source)


class Senate(CommitteeList):
    chamber = "upper"
    committeeTypeId = "1"


class House(CommitteeList):
    chamber = "lower"
    committeeTypeId = "2"


class Joint(CommitteeList):
    chamber = "legislature"
    committeeTypeId = "3"
