from spatula import URL, CSS, HtmlListPage, HtmlPage, XPath, SelectorError
from openstates.models import ScrapePerson
import re


class LegDetail(HtmlPage):
    def process_page(self):
        p = self.input

        img = CSS("img").match(self.root)[6].get("src")
        p.image = img

        addresses = CSS("address").match(self.root)
        for num, address in enumerate(addresses):
            addr = ""
            phone = None
            fax = None
            lines = XPath("text()").match(address)
            for line in lines:
                if re.search(r"(Senator|Hon\.)", line.strip()):
                    continue
                elif re.search(r"(FAX|Fax|fax)", line.strip()):
                    fax = line.strip()
                elif re.search(r"\(\d{3}\)\s\d{3}-\d{4}", line.strip()):
                    phone = line.strip()
                else:
                    addr_lines = line.strip().split("\n")
                    for addr_line in addr_lines:
                        addr += addr_line.strip()
                        addr += " "

            if (p.chamber == "upper" and num == 0) or (
                p.chamber == "lower" and num == len(addresses) - 1
            ):
                p.capitol_office.address = addr.strip()
                if phone:
                    p.capitol_office.voice = phone
                if fax:
                    fax = re.search(r"(FAX|Fax|fax):\s(.+)", fax).groups()[1]
                    p.capitol_office.fax = fax
            else:
                if phone and fax:
                    fax = re.search(r"(FAX|Fax|fax):\s(.+)", fax).groups()[1]
                    p.add_office(
                        classification="district",
                        address=addr,
                        voice=phone,
                        fax=fax,
                    )
                elif phone:
                    p.add_office(classification="district", address=addr, voice=phone)
                elif fax:
                    fax = re.search(r"(FAX|Fax|fax):\s(.+)", fax).groups()[1]
                    p.add_office(classification="district", address=addr, fax=fax)
                else:
                    p.add_office(classification="district", address=addr)

        social_links = CSS("div.Widget.MemberBio-SocialLinks a").match(self.root)
        for link in social_links:
            if re.search(
                r"(enewsletters|library|pacapitol|news|(C|c)ontact|linkedin|vimeo|email|feed|google|RSS|protect|sk=wall)",
                link.get("href"),
            ):
                continue
            elif re.search(r"(F|f)acebook", link.get("href")):
                fb = link.get("href").split("/")
                if fb[-1] == "" or not re.search(r"[A-Za-z]", fb[-1]):
                    fb_id = fb[-2]
                else:
                    fb_id = fb[-1]
                p.ids.facebook = fb_id
            elif re.search(r"twitter", link.get("href")):
                twitter = link.get("href").split("/")
                if twitter[-1] == "":
                    tw_id = twitter[-2]
                else:
                    tw_id = twitter[-1]
                p.ids.twitter = tw_id.lstrip("@")
            elif re.search(r"instagram", link.get("href")):
                insta = link.get("href").split("/")
                if insta[-1] == "" or re.search(r"hl=en", insta[-1]):
                    insta_id = insta[-2]
                else:
                    insta_id = insta[-1]
                p.ids.instagram = insta_id
            elif re.search(r"youtube", link.get("href")):
                youtube = link.get("href").split("/")
                if youtube[-1] == "" or re.search(r"featured", youtube[-1]):
                    youtube_id = youtube[-2]
                else:
                    youtube_id = youtube[-1]
                p.ids.youtube = youtube_id
            else:
                p.extras["website"] = link.get("href")

        try:
            if p.chamber == "lower":
                sibs = XPath(
                    "/html/body/div/section/div/div[2]/div/div[3]/h4[contains(text(), 'Education')]"
                ).match_one(self.root)
                ed1 = sibs.tail.strip()
                if ed1 != "":
                    p.extras["Education"] = [ed1]
                for sib in sibs.itersiblings():
                    if sib.text_content().strip() == "Military Service":
                        break
                    p.extras["Education"] += [sib.tail.strip()]
            else:
                sibs = (
                    XPath("//*[@id='Mbr-Bio']/h4[contains(text(), 'Attended')]")
                    .match_one(self.root)
                    .itersiblings()
                )
                education = []
                for sib in sibs:
                    if (
                        sib.text_content().strip() == "Career"
                        or sib.text_content().strip() == "Military Service"
                    ):
                        break
                    if sib.text_content().strip() != "":
                        education += [sib.text_content().strip()]
                if len(education) > 0:
                    p.extras["Education"] = education
        except SelectorError:
            pass

        return p


class LegList(HtmlListPage):
    selector = CSS("div.MemberInfoList-MemberWrapper")

    def process_item(self, item):
        name_dirty = CSS("a").match_one(item).text_content().strip().split(", ")
        name = name_dirty[1] + " " + name_dirty[0]

        district = CSS("br").match_one(item).tail.strip()
        district = re.search(r"District\s(.+)", district).groups()[0]

        party = CSS("b").match_one(item).tail.strip()
        if party == "(D)":
            party = "Democratic"
        elif party == "(R)":
            party = "Republican"
        elif party == "(I)":
            party = "Independent"

        p = ScrapePerson(
            name=name,
            state="pa",
            chamber=self.chamber,
            district=district,
            party=party,
        )

        detail_link = CSS("a").match_one(item).get("href")

        p.add_source(self.source.url)
        p.add_source(detail_link)
        p.add_link(detail_link, note="homepage")

        return LegDetail(p, source=detail_link)


class Senate(LegList):
    source = URL(
        "https://www.legis.state.pa.us/cfdocs/legis/home/member_information/mbrList.cfm?body=S&sort=alpha"
    )
    chamber = "upper"


class House(LegList):
    source = URL(
        "https://www.legis.state.pa.us/cfdocs/legis/home/member_information/mbrList.cfm?body=H&sort=alpha"
    )
    chamber = "lower"
