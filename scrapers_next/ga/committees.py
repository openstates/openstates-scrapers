import requests
from hashlib import sha512
import time
from spatula import URL, JsonListPage, JsonPage, HtmlListPage, XPath
from openstates.people.models.committees import ScrapeCommittee


def get_key(timestamp):
    # this comes out of Georgia's javascript
    # 1) part1 (and the overall format) comes from
    #   (e.prototype.getKey = function (e, t) {
    #     return Ht.SHA512("QFpCwKfd7f" + c.a.obscureKey + e + t);
    #
    # 2) part2 is obscureKey in the source code :)
    #
    # 3) e is the string "letvarconst"
    # (e.prototype.refreshToken = function () {
    #   return this.http
    #     .get(c.a.apiUrl + "authentication/token", {
    #       params: new v.f()
    #         .append("key", this.getKey("letvarconst", e))
    part1 = "QFpCwKfd7"
    part2 = "fjVEXFFwSu36BwwcP83xYgxLAhLYmKk"
    part3 = "letvarconst"
    key = part1 + part2 + part3 + timestamp
    return sha512(key.encode()).hexdigest()


def get_token():
    timestamp = str(int(time.time() * 1000))
    key = get_key(timestamp)
    token_url = (
        f"https://www.legis.ga.gov/api/authentication/token?key={key}&ms={timestamp}"
    )
    return "Bearer " + requests.get(token_url).json()


class CommitteeDetail(JsonPage):
    def process_page(self):
        # print(self.data['members'])
        com = self.input
        com.add_source(self.source.url)
        com.add_link(self.source.url)

        for memb in self.data["members"]:
            # print(memb)
            member = memb["name"]
            role = memb["role"]
            com.add_member(member, role)
        # grab office address and phone?
        # grab member link?
        # grab district as well?

        return com


class CommitteeList(JsonListPage):

    source = URL(
        "https://www.legis.ga.gov/api/committees/List/1029",
        headers={"Authorization": get_token()},
    )

    def process_item(self, item):
        if item["chamber"] == 2:
            chamber = "upper"
            source = "https://www.legis.ga.gov/committees/senate/"
        elif item["chamber"] == 1:
            chamber = "lower"
            source = "https://www.legis.ga.gov/committees/house/"

        source = URL(
            f"https://www.legis.ga.gov/api/committees/details/{item['id']}/1029",
            headers={"Authorization": get_token()},
        )

        # print(item.get('href'))
        com = ScrapeCommittee(
            name=item["name"],
            parent=chamber,
        )

        com.add_source(self.source.url)
        com.add_link(self.source.url)

        return CommitteeDetail(
            com,
            source=source,
        )


class HouseSpecialCommittees(HtmlListPage):
    source = "https://www.house.ga.gov/Committees/en-US/StudyCommittees.aspx"
    selector = XPath("//*[@id='WebPartWPQ2']/table[1]/tbody/tr")
    # CSS("div #WebPartWPQ2 table tbody").first

    def process_item(self, item):
        # if item.__class__ == "ms-rteTableHeaderRow-1":
        #    self.skip()

        name = item.text_content()
        name = name.strip()

        com = ScrapeCommittee(
            name=name,
            parent="lower",
        )

        return com
