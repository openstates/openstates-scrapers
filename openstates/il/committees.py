from openstates_core.scrape import Scraper, Organization
import lxml.html

from ._committees import COMMITTEES
from ._utils import canonicalize_url


class IlCommitteeScraper(Scraper):
    def scrape_members(self, o, url):
        session = int(url.split("=")[-1])
        start = 1917 + session
        end = start + 1

        data = self.get(url).text
        if "No members added" in data:
            return
        doc = lxml.html.fromstring(data)

        for row in doc.xpath('//table[@cellpadding="3"]/tr')[1:]:
            tds = row.xpath("td")

            # remove colon and lowercase role
            role = tds[0].text_content().replace(":", "").strip().lower()

            name = tds[1].text_content().strip()
            o.add_member(name, role, start_date=str(start), end_date=str(end))

    def scrape(self, latest_only=True):
        chambers = (("upper", "senate"), ("lower", "house"))
        committees = {}

        for chamber, chamber_name in chambers:

            CURRENT_SESSION = 101
            sessions = (
                [CURRENT_SESSION] if latest_only else range(93, CURRENT_SESSION + 1)
            )

            for session in sessions:

                bad_keys = []

                url = "http://ilga.gov/{0}/committees/default.asp?GA={1}".format(
                    chamber_name, session
                )
                html = self.get(url).text
                doc = lxml.html.fromstring(html)
                doc.make_links_absolute(url)

                top_level_com = None

                for a in doc.xpath('//a[contains(@href, "members.asp")]'):
                    name = a.text.strip()
                    code = a.getparent().getnext()
                    com_url = canonicalize_url(a.get("href"))
                    if "&GA=" not in com_url:
                        com_url += "&GA=" + str(session)
                    if "TaskForce" in com_url:
                        code = None
                        o_id = (name, code)
                    else:
                        code = code.text_content().strip()
                        if (name, code) not in COMMITTEES:
                            bad_keys.append((name, code))
                            continue

                        o_id = COMMITTEES[(name, code)]

                    skip_code = False
                    if (name, code) in {
                        ("Energy Resources Subcommittee", "HENE-ENRE"),
                        ("Workers' Compensation Subcommittee", "HLBR-WORK"),
                        ("Subcommittee on Readiness", "SENE-SENR"),
                        ("Trans. Regulation Accountability", "HTRR-TRAS"),
                        ("Subcommittee on Airports", "STRN-STRA"),
                    }:
                        skip_code = True

                    if o_id in committees:
                        committees[o_id]["name"].add(name)
                        committees[o_id]["source"].add(com_url)
                        if not skip_code:
                            committees[o_id]["code"].add(code)
                    else:
                        committees[o_id] = {
                            "name": {name},
                            "code": set(),
                            "source": {com_url},
                        }
                        if not skip_code:
                            committees[o_id]["code"].add(code)

                    if code is not None and "-" in code:
                        committees[o_id]["parent"] = top_level_com
                    else:
                        committees[o_id]["chamber"] = chamber
                        top_level_com = o_id
                if len(bad_keys) > 0:
                    bad_keys.sort(key=lambda tup: tup[0])
                    # formatted for quick copy-paste insertion into _committees.py
                    bad_keys_str = "\n".join(
                        ["('" + "', '".join(bad) + "'): ''," for bad in bad_keys]
                    )
                    raise ValueError("unknown committees:\n" + bad_keys_str)
        top_level = {
            o_id: committee
            for o_id, committee in committees.items()
            if "chamber" in committee
        }

        sub_committees = {
            o_id: committee
            for o_id, committee in committees.items()
            if "parent" in committee
        }

        for o_id, committee in list(top_level.items()):
            o = self.dict_to_org(committee)
            top_level[o_id] = o
            yield o

        for committee in sub_committees.values():
            committee["parent"] = top_level[committee["parent"]]
            o = self.dict_to_org(committee)
            yield o

    def dict_to_org(self, committee):
        names = sorted(committee["name"])
        first_name = names.pop()
        if "chamber" in committee:
            o = Organization(
                first_name, classification="committee", chamber=committee["chamber"]
            )
        else:
            o = Organization(
                first_name, classification="committee", parent_id=committee["parent"]
            )
        for other_name in names:
            o.add_name(other_name)
        for code in committee["code"]:
            if code:
                o.add_name(code)
        for source in committee["source"]:
            o.add_source(source)
            self.scrape_members(o, source)

        return o
