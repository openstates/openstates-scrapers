import re
import lxml.html

from billy.scrape.committees import CommitteeScraper, Committee

COMMITTEE_URL = ("http://www.colorado.gov/cs/Satellite?c=Page&"
    "childpagename=CGA-LegislativeCouncil%2FCLCLayout&"
    "cid=1245677985421&pagename=CLCWrapper")


class COCommitteeScraper(CommitteeScraper):
    jurisdiction = "co"

    def lxmlize(self, url):
        text = self.get(url).text
        page = lxml.html.fromstring(text)
        page.make_links_absolute(url)
        return page, text

    def scrape_page(self, a, chamber, term):
        page, text = self.lxmlize(a.attrib['href'])
        committee = a.text_content()
        twitter_ids = re.findall("setUser\('(.*)'\)", text)
        twitter_id = twitter_ids[0] if twitter_ids != [] else None
        roles = {
            ", Chair": "chair",
            ", Vice-Chair": "member"
        }

        committee = Committee(chamber, committee,
                              twitter=twitter_id)

        committee.add_source(a.attrib['href'])

        tables = page.xpath("//table[@width='545' or @width='540']")
        added = False

        seen_people = set([])
        for table in tables:
            people = table.xpath(
                ".//a[contains(@href, 'MemberDetailPage')]/text()")
            for person in [x.strip() for x in people]:
                role = "member"
                for flag in roles:
                    if person.endswith(flag):
                        role = roles[flag]
                        person = person[:-len(flag)].strip()
                if person in seen_people:
                    continue

                if person in "":
                    continue

                seen_people.add(person)
                committee.add_member(person, role)
                added = True

        if added:
            self.save_committee(committee)
            return

        tables = page.xpath("//table[@width='466']")
        added = False
        seen_people = set([])
        for table in tables:
            if "committee members" in table.text_content().lower():
                for person in table.xpath(".//td/text()"):
                    person = person.strip()
                    if person != "":
                        if person in seen_people:
                            continue
                        seen_people.add(person)
                        committee.add_member(person, "member")
                        added = True

        if added:
            self.save_committee(committee)
            return

        self.warning("Unable to scrape!")

    def scrape(self, term, chambers):
        page, _ = self.lxmlize(COMMITTEE_URL)
        chamber = "other"
        for div in page.xpath("//div[@id='Content_COITArticleDetail']"):
            hrefs = div.xpath(
                ".//a[contains(@href,'childpagename=CGA-LegislativeCouncil')]")

            if hrefs == []:
                div_txt = div.text_content().lower()
                flags = {
                    "house": "lower",
                    "senate": "upper",
                    "joint": "joint"
                }
                for flag in flags:
                    if flag in div_txt:
                        chamber = flags[flag]

            for a in hrefs:
                cchamber = chamber
                text = a.text_content().strip()
                for flag in flags:
                    if flag in text:
                        cchamber = flags[flag]
                self.scrape_page(a, cchamber, term)
