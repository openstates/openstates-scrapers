from spatula import URL, JsonPage, HtmlPage, CSS, XPath, SelectorError
from openstates.models import ScrapePerson
import re


class LegDetail(HtmlPage):
    def process_page(self):
        p = self.input
        img = CSS("img.profile-photo").match_one(self.root).get("src")
        p.image = img

        try:
            state_email = (
                XPath("//*[@id='main-content']/div[2]/dl/dt[text()='Email']")
                .match_one(self.root)
                .getnext()
                .text_content()
                .strip()
            )
            if (
                state_email.strip() != ""
                and state_email.strip() not in p.extras["emails"].values()
            ):
                p.extras["emails"]["state email"] = state_email.strip()
                # which one should be assigned to p.email?
                # I'm guessing state email
        except SelectorError:
            pass

        district_map = (
            XPath("//*[@id='main-content']/div[2]/dl/dt[contains(text(), 'District')]")
            .match_one(self.root)
            .getnext()
            .getchildren()[0]
            .get("href")
        )
        p.add_link(district_map, note="district map")

        return p


class LegList(JsonPage):
    source = URL("https://legislature.vermont.gov/people/loadAll/2022")

    def process_page(self):
        legislators = self.data["data"]

        for leg in legislators:
            if leg["MI"].strip() != "":
                name = (
                    leg["FirstName"].strip()
                    + " "
                    + leg["MI"].strip()
                    + ". "
                    + leg["LastName"].strip()
                )
            else:
                name = leg["FirstName"].strip() + " " + leg["LastName"].strip()

            party = leg["Party"].strip()
            party = re.sub("Democrat", "Democratic", party)

            district = leg["District"].strip()
            district = re.sub("District", "", district)
            # these are names rather than numbers

            if leg["Title"].strip() == "Senator":
                chamber = "upper"
            elif leg["Title"].strip() == "Representative":
                chamber = "lower"

            p = ScrapePerson(
                name=name, state="vt", chamber=chamber, district=district, party=party
            )
            p.add_source(self.source.url)

            p.given_name = leg["FirstName"].strip()
            p.family_name = leg["LastName"].strip()
            if leg["NameSuffix"].strip() != "":
                p.suffix = leg["NameSuffix"].strip()

            work_addr = ""
            if leg["WorkAddress1"].strip() != "":
                work_addr += leg["WorkAddress1"].strip()
                work_addr += " "
            if leg["WorkAddress2"].strip() != "":
                work_addr += leg["WorkAddress2"].strip()
                work_addr += " "
            if leg["WorkCity"].strip() != "":
                work_addr += leg["WorkCity"].strip()
                work_addr += ", "
            if leg["WorkState"].strip() != "":
                work_addr += leg["WorkState"].strip()
                work_addr += " "
            if leg["WorkZIP"].strip() != "":
                work_addr += leg["WorkZIP"].rstrip("-").strip()
                work_addr += " "
            if work_addr.strip() != "":
                p.extras["work address"] = work_addr.strip()

            home_addr = ""
            if leg["HomeAddress1"].strip() != "":
                home_addr += leg["HomeAddress1"].strip()
                home_addr += " "
            if leg["HomeAddress2"].strip() != "":
                home_addr += leg["HomeAddress2"].strip()
                home_addr += " "
            if leg["HomeCity"].strip() != "":
                home_addr += leg["HomeCity"].strip()
                home_addr += ", "
            if leg["HomeState"].strip() != "":
                home_addr += leg["HomeState"].strip()
                home_addr += " "
            if leg["HomeZIP"].strip() != "":
                home_addr += leg["HomeZIP"].rstrip("-").strip()
                home_addr += " "
            if home_addr.strip() != "":
                p.extras["home address"] = home_addr.strip()

            if leg["HomePhone"].strip() != "":
                p.extras["home phone"] = leg["HomePhone"].strip()

            p.extras["emails"] = {}
            if leg["Email"].strip() != "":
                # p.email = leg["Email"].strip()
                p.extras["emails"]["email"] = leg["Email"].strip()

            if (
                leg["WorkEmail"].strip() != ""
                and leg["WorkEmail"].strip() != leg["Email"].strip()
            ):
                # p.extras["work email"] = leg["WorkEmail"].strip()
                p.extras["emails"]["work email"] = leg["WorkEmail"].strip()

            if (
                leg["HomeEmail"].strip() != ""
                and leg["HomeEmail"].strip() != leg["Email"].strip()
                and leg["HomeEmail"].strip() != leg["WorkEmail"].strip()
            ):
                # p.extras["home email"] = leg["HomeEmail"].strip()
                p.extras["emails"]["home email"] = leg["HomeEmail"].strip()

            mail_addr = ""
            if leg["MailingAddress1"].strip() != "":
                mail_addr += leg["MailingAddress1"].strip()
                mail_addr += " "
            if leg["MailingAddress2"].strip() != "":
                mail_addr += leg["MailingAddress2"].strip()
                mail_addr += " "
            if leg["MailingCity"].strip() != "":
                mail_addr += leg["MailingCity"].strip()
                mail_addr += ", "
            if leg["MailingState"].strip() != "":
                mail_addr += leg["MailingState"].strip()
                mail_addr += " "
            if leg["MailingZIP"].strip() != "":
                mail_addr += leg["MailingZIP"].strip()
                mail_addr += " "
            if mail_addr.strip() != "":
                p.extras["mailing address"] = mail_addr.strip()

            detail_link = (
                f"http://legislature.vermont.gov/people/single/2022/{leg['PersonID']}"
            )
            p.add_source(detail_link)
            p.add_link(detail_link, note="homepage")

            yield LegDetail(p, source=detail_link)

            # old code hard-coded capitol address
            # "Vermont State House\;115 State Street\;Montpelier, VT 05633"
            # (802) 828-2228 looks like capitol phone
            # old code assigned mailing address as district_office.address

            # leg['vTown']
            # leg['Town']
