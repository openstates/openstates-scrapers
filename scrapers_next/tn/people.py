from spatula import CSS, URL, HtmlListPage, HtmlPage, XPath, SelectorError
from openstates.models import ScrapePerson
import re


class LegDetail(HtmlPage):
    def process_page(self):
        p = self.input

        addr_lst = XPath(
            "/html/body/div[1]/div/div/div[2]/div/div[1]/div[2]/p[1]/text()"
        ).match(self.root)
        cap_address = ""
        for line in addr_lst:
            if re.search(r"Phone", line):
                cap_phone = re.search(r"Phone:?\s(.+)", line).groups()[0].strip()
                p.capitol_office.voice = cap_phone
            elif re.search(r"Fax", line):
                cap_fax = re.search(r"Fax:?\s(.+)", line).groups()[0].strip()
                p.capitol_office.fax = cap_fax
            elif re.search(r"\d?-?\d{3}-\d{3}-\d{4}", line):
                p.extras["extra phone"] = line.strip()
            else:
                cap_address += line.strip()
                cap_address += " "
        p.capitol_office.address = cap_address.strip()

        img = CSS("img.framed-photo").match_one(self.root).get("src")
        p.image = img

        try:
            if (
                XPath(
                    "/html/body/div[1]/div/div/div[2]/div/div[1]/div[2]/h2[2]/text()"
                ).match(self.root)[0]
                == "District Address"
            ):
                district_addr_lst = XPath(
                    "/html/body/div[1]/div/div/div[2]/div/div[1]/div[2]/p[2]/text()"
                ).match(self.root)
                distr_address = ""
                for line in district_addr_lst:
                    if re.search(r"Phone", line):
                        distr_phone = (
                            re.search(r"Phone:?\s(.+)", line).groups()[0].strip()
                        )
                        p.district_office.voice = distr_phone
                    elif re.search(r"Fax", line):
                        distr_fax = re.search(r"Fax:?\s(.+)", line).groups()[0].strip()
                        p.district_office.fax = distr_fax
                    else:
                        distr_address += line.strip()
                        distr_address += " "
                p.district_office.address = distr_address.strip()
        except SelectorError:
            p.district_office.voice = ""
            p.district_office.fax = ""
            p.district_office.address = ""

        extra_info = XPath(
            "/html/body/div[1]/div/div/div[2]/div/div[2]/ul[2]/li[1]/ul/li"
        ).match(self.root)
        if len(extra_info) > 0:
            p.extras["personal info"] = []
            for line in extra_info:
                p.extras["personal info"] += [line.text_content().strip()]

        try:
            if (
                XPath("/html/body/div[1]/div/div/div[2]/div/div[1]/div[2]/h2")
                .match(self.root)[1]
                .text_content()
                .strip()
                == "Staff Contacts"
            ):
                staff_contacts = (
                    XPath("/html/body/div[1]/div/div/div[2]/div/div[1]/div[2]/p[2]")
                    .match(self.root)[0]
                    .text_content()
                )
                p_num = 2
            elif (
                XPath("/html/body/div[1]/div/div/div[2]/div/div[1]/div[2]/h2")
                .match(self.root)[2]
                .text_content()
                .strip()
                == "Staff Contacts"
            ):
                try:
                    staff_contacts = (
                        XPath("/html/body/div[1]/div/div/div[2]/div/div[1]/div[2]/p[3]")
                        .match(self.root)[0]
                        .text_content()
                    )
                    p_num = 3
                except Exception:
                    staff_contacts = ""
        except IndexError:
            staff_contacts = ""

        counter = 0
        for line in staff_contacts.split("\n"):
            if line.strip() != "":
                staff_name = line.strip().split(", ")[0]
                staff_role = None
                if len(line.strip().split(", ")) > 1:
                    staff_role = line.strip().split(", ")[1]
                try:
                    staff_email = (
                        XPath(
                            f"/html/body/div[1]/div/div/div[2]/div/div[1]/div[2]/p[{p_num}]/a"
                        )
                        .match(self.root)[counter]
                        .get("href")
                    )
                    staff_email = re.search(r"mailto:\s?(.+)", staff_email).groups()[0]
                    if staff_role:
                        p.extras[staff_role + " email"] = staff_email
                    else:
                        p.extras["staff email"] = staff_email
                except SelectorError:
                    pass

                if staff_role:
                    p.extras[staff_role] = staff_name
                else:
                    p.extras["staff"] = staff_name
                counter += 1

        return p


class Legislators(HtmlListPage):
    selector = CSS("tbody tr")

    def process_item(self, item):
        if CSS("td").match(item)[1].text_content().strip() == "Vacant":
            self.skip("vacant")

        name_dirty = CSS("td").match(item)[1].text_content().strip().split(", ")
        name = name_dirty[1] + " " + name_dirty[0]
        if "Speaker" in name:
            name = re.sub(r"Speaker ", "", name)

        party = CSS("td").match(item)[2].text_content().strip()
        # sometimes members don't have a party listed?!
        if not party:
            self.skip("missing party")
        if party == "D":
            party = "Democratic"
        elif party == "R":
            party = "Republican"
        elif party == "I":
            party = "Independent"

        district = CSS("td").match(item)[4].text_content().strip()
        district = re.search(r"District\s(.+)", district).groups()[0]

        p = ScrapePerson(
            name=name,
            state="tn",
            chamber=self.chamber,
            district=district,
            party=party,
        )

        detail_link = CSS("td a").match(item)[1].get("href")

        p.add_source(self.source.url)
        p.add_source(detail_link)
        p.add_link(detail_link, note="homepage")

        email = CSS("td a").match(item)[0].get("href")
        email = re.search(r"mailto:(.+)", email).groups()[0]
        p.email = email

        # this is also being grabbed above in capitol_office.address
        office_room = CSS("td").match(item)[5].text_content().strip()
        p.extras["office"] = office_room

        return LegDetail(p, source=detail_link)


class Senate(Legislators):
    source = URL("https://www.capitol.tn.gov/senate/members/")
    chamber = "upper"


class House(Legislators):
    source = URL("https://www.capitol.tn.gov/house/members/")
    chamber = "lower"
