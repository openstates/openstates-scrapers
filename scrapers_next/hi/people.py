import re
from spatula import XPath, HtmlListPage
from openstates.models import ScrapePerson


class Legislators(HtmlListPage):
    source = "http://www.capitol.hawaii.gov/members/legislators.aspx"
    selector = XPath(".//div[@class='contact-box center-version active']")

    multi_commas_regex = re.compile(r",.+,")
    leader_regex = re.compile(r"(.+),(.+)\s+\(([A-Z]+)\)\s+(.+)")
    regular_regex = re.compile(r"(.+),(.+)\s+\(([A-Z]+)\)")

    email_removal = [
        " iii",
        "jr.",
        " ",
        "-",
    ]
    email_remove_regexes = [re.compile(string) for string in email_removal]

    soc_domain_and_handle_regex = re.compile(r"\.*\/*(\w+)\.com/(.+)")

    social_removal = [
        "user",
        "channel",
        "playlists",
        "photos",
        "/",
    ]
    social_remove_regexes = [re.compile(string) for string in social_removal]

    def process_item(self, item):
        a_tag = item.xpath("a")[0]
        member_page = a_tag.get("href")
        member_photo = a_tag.xpath("img")[0].get("src")

        member_text = a_tag.text_content().strip()

        # Conditional re-formats member_text in cases with multiple commas
        #   Ex: Richards\r\n, III, Herbert M. "Tim" (D)
        multi_commas = self.multi_commas_regex.search(member_text)
        if multi_commas:
            single_line = member_text.replace("\r\n", "")
            comma_split = [x.strip() for x in single_line.split(",")]
            member_text = f"{' '.join(comma_split[0:2])}, {comma_split[-1]}"

        leader = self.leader_regex.search(member_text)
        if leader:
            name_parts = [x.strip() for x in leader.groups()]
            # Extracts title: only leaders have one listed
            title = name_parts.pop()
        else:
            regular_member = self.regular_regex.search(member_text)
            name_parts = [x.strip() for x in regular_member.groups()]

        # Extracts party abbreviation from list
        party = name_parts.pop()

        last_name, first_name = name_parts[0], " ".join(name_parts[1:])

        dist_text = item.xpath("div/a")[0].text_content().strip()
        chamber, district = [x.strip() for x in dist_text.split("District")]

        contact_info = item.xpath("div/address")[0]
        split_lines = contact_info.text_content().split("\r\n")
        contact_list = [x.strip() for x in split_lines if len(x.strip())]

        state_addr_base = "415 S Beretania St, Honolulu, HI 96813"
        capitol_addr = f"{contact_list[0]}, {state_addr_base}"

        cap_phone, cap_fax = [x.split(":")[-1].strip() for x in contact_list]

        # Website does not allow scraping of member emails, so a manual check
        #   of all member emails confirmed accuracy of below solution.
        email_user = last_name.lower()
        for string in self.social_remove_regexes:
            email_user = string.sub("", email_user)
        email_start = {"House": "rep", "Senate": "sen"}
        email = email_start[chamber] + email_user + "@capitol.hawaii.gov"

        soc_handles = {}
        soc_links = contact_info.getnext().xpath("a")
        for link in soc_links:
            href = link.get("href").lower()
            dom, han = self.soc_domain_and_handle_regex.search(href).groups()
            for string in self.social_remove_regexes:
                han = string.sub("", han)
            soc_handles[dom] = han

        # Website provides bad youtube handle for Sen Mike Gabbard
        if f"{first_name} {last_name}" == "Mike Gabbard":
            soc_handles["youtube"] = "senmikegabbard"

        p = ScrapePerson(
            name=f"{first_name} {last_name}",
            state="hi",
            chamber="lower" if chamber[0] == "H" else "upper",
            district=district,
            given_name=first_name,
            family_name=last_name,
            party="Democratic" if party == "D" else "Republican",
            image=member_photo,
            email=email,
        )

        if title:
            p.extras["title"] = title

        p.capitol_office.address = capitol_addr
        p.capitol_office.voice = cap_phone
        p.capitol_office.fax = cap_fax

        p.add_source(self.source.url)
        p.add_link(member_page)

        if soc_handles["facebook"]:
            p.ids.facebook = soc_handles["facebook"]
        if soc_handles["instagram"]:
            p.ids.instagram = soc_handles["instagram"]
        if soc_handles["twitter"]:
            p.ids.twitter = soc_handles["twitter"]
        if soc_handles["youtube"]:
            p.ids.youtube = soc_handles["youtube"]
        if soc_handles["flickr"]:
            p.ids.flickr = soc_handles["flickr"]

        return p
