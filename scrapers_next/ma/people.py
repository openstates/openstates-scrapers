from spatula import XPath, JsonListPage, JsonPage, SelectorError, URL
from openstates.models import ScrapePerson


def list_url():
    general_court_num = "193"
    return f"https://malegislature.gov/api/GeneralCourts/{general_court_num}/LegislativeMembers/"


class LegDetail(JsonPage):

    example_source = (
        "http://malegislature.gov/api/GeneralCourts/192/LegislativeMembers/R_C1"
    )

    def process_page(self):
        member_code = self.data["MemberCode"]
        image = f"https://malegislature.gov/Legislators/Profile/170/{member_code}.jpg"
        chamber = "upper" if self.data["Branch"] == "Senate" else "lower"

        party = self.data["Party"]
        if party == "Unenrolled":
            party = "Independent"

        p = ScrapePerson(
            name=self.data["Name"],
            state="ma",
            party=party,
            district=self.data["District"],
            chamber=chamber,
            image=image,
            email=self.data["EmailAddress"],
        )

        room_num = self.data["RoomNumber"]
        if room_num:
            capitol_address = f"24 Beacon St., Room {room_num}; Boston, MA 02133"
            p.capitol_office.address = capitol_address

        # phone number and fax number (if it exists) are both from capitol office address
        phone = self.data["PhoneNumber"]
        numbers_only_phone_length = 10

        if phone:
            # there are 3 formats for phone numbers (some must be adjusted for extensions):
            # 61772228007309 is 617 722 2800x7309
            # (617) 722-1660 is (617) 722-1660
            # (617) 722-2800 x7306 is (617) 722-2800 x7306
            if (
                len(phone) > numbers_only_phone_length
                and " " not in phone
                and "x" not in phone
            ):
                phone = phone[:10] + " x" + phone[10:]

            p.capitol_office.voice = phone

        try:
            fax = self.data["FaxNumber"]
            if fax:
                p.capitol_office.fax = fax
        except SelectorError:
            pass

        if self.data["LeadershipPosition"]:
            p.extras["leadership position"] = self.data["LeadershipPosition"]

        p.extras["member code"] = member_code

        p.add_source(self.source.url)
        p.add_source(list_url())
        p.add_link(f"https://malegislature.gov/Legislators/Profile/{member_code}")

        return p


class LegList(JsonListPage):

    source = URL(list_url(), timeout=30)
    selector = XPath("//LegislativeMemberSummary/Details")

    def process_item(self, item):

        url = item["Details"]
        return LegDetail(source=URL(url, timeout=30))
