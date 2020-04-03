from openstates_core.scrape import Person, Scraper

from scrapers.utils import LXMLMixin

from .util import get_client, get_url, backoff, SESSION_SITE_IDS


HOMEPAGE_URLS = {
    "lower": (
        "http://www.house.ga.gov/Representatives/en-US/"
        "member.aspx?Member={code}&Session={sid}"
    ),
    "upper": (
        "http://www.senate.ga.gov/SENATORS/en-US/"
        "member.aspx?Member={code}&Session={sid}"
    ),
}


class GAPersonScraper(Scraper, LXMLMixin):
    sservice = get_client("Members").service
    ssource = get_url("Members")

    def clean_list(self, dirty_list):
        new_list = []
        for x in dirty_list:
            if x is None:
                new_list.append(x)
            else:
                new_list.append(x.strip())
        return new_list

    def scrape_homepage(self, url, kwargs):
        url = url.format(**kwargs)
        page = self.lxmlize(url)
        images = page.xpath("//img[contains(@src, 'SiteCollectionImages')]")

        if len(images) != 1:
            raise Exception

        return url, images[0].attrib["src"]

    def scrape_session(self, session, chambers):
        sid = SESSION_SITE_IDS[session]
        members = backoff(self.sservice.GetMembersBySession, sid)["MemberListing"]

        seen_guids = []
        for member in members:
            guid = member["Id"]
            member_info = backoff(self.sservice.GetMember, guid)

            # If a member switches chambers during the session, they may
            # appear twice. Skip the duplicate record accordingly.
            if guid in seen_guids:
                self.warning(
                    "Skipping duplicate record of {}".format(
                        member_info["Name"]["Last"]
                    )
                )
                continue
            else:
                seen_guids.append(guid)

            # Check to see if the member has vacated; skip if so.
            # A member can have multiple services for a given session,
            # if they switched chambers. Filter these down to just the
            # active service.
            try:
                (legislative_service,) = [
                    service
                    for service in member_info["SessionsInService"][
                        "LegislativeService"
                    ]
                    if service["Session"]["Id"] == sid
                    and service["DateVacated"] is None
                ]
            except ValueError:
                self.info(
                    "Skipping retired member {}".format(member_info["Name"]["Last"])
                )
                continue

            nick_name, first_name, middle_name, last_name = (
                member_info["Name"][x] for x in ["Nickname", "First", "Middle", "Last"]
            )

            first_name = nick_name if nick_name else first_name

            if middle_name:
                full_name = "%s %s %s" % (first_name, middle_name, last_name)
            else:
                full_name = "%s %s" % (first_name, last_name)

            party = legislative_service["Party"]

            if party == "Democrat":
                party = "Democratic"

            elif party.strip() == "":
                party = "other"

            chamber, district = (
                legislative_service["District"][x] for x in ["Type", "Number"]
            )

            chamber = {"House": "lower", "Senate": "upper"}[chamber]

            url, photo = self.scrape_homepage(
                HOMEPAGE_URLS[chamber], {"code": guid, "sid": sid}
            )

            legislator = Person(
                name=full_name,
                district=str(district),
                party=party,
                primary_org=chamber,
                image=photo,
            )
            legislator.extras = {
                "family_name": last_name,
                "given_name": first_name,
                "guid": guid,
            }

            if (
                member_info["Address"]["Street"] is not None
                and member_info["Address"]["Street"].strip()
            ):
                capitol_address_info = {
                    k: v.strip()
                    for k, v in dict(member_info["Address"]).items()
                    if k in ["Street", "City", "State", "Zip"]
                }
                capitol_address = "{Street}\n{City}, {State} {Zip}".format(
                    **capitol_address_info
                )
                legislator.add_contact_detail(
                    type="address", value=capitol_address, note="Capitol Address"
                )
            else:
                self.warning(
                    "Could not find full capitol address for {}".format(full_name)
                )

            capitol_contact_info = self.clean_list(
                [member_info["Address"][x] for x in ["Email", "Phone", "Fax"]]
            )

            # Sometimes email is set to a long cryptic string.
            # If it doesn't have a @ character, simply set it to None
            # examples:
            # 01X5dvct3G1lV6RQ7I9o926Q==&c=xT8jBs5X4S7ZX2TOajTx2W7CBprTaVlpcvUvHEv78GI=
            # 01X5dvct3G1lV6RQ7I9o926Q==&c=eSH9vpfdy3XJ989Gpw4MOdUa3n55NTA8ev58RPJuzA8=
            if capitol_contact_info[0] and "@" not in capitol_contact_info[0]:
                capitol_contact_info[0] = None

            if capitol_contact_info[0]:
                # Site was hacked in the past
                assert "quickrxdrugs@yahoo.com" not in capitol_contact_info[0]

            if capitol_contact_info[1]:
                legislator.add_contact_detail(
                    type="voice", value=capitol_contact_info[1], note="Capitol Address"
                )
            if capitol_contact_info[2]:
                legislator.add_contact_detail(
                    type="fax", value=capitol_contact_info[2], note="Capitol Address"
                )
            if capitol_contact_info[0]:
                legislator.add_contact_detail(
                    type="email", value=capitol_contact_info[0], note="Capitol Address"
                )

            if (
                member_info["DistrictAddress"]["Street"] is not None
                and member_info["DistrictAddress"]["Street"].strip()
            ):
                district_address_info = {
                    k: v.strip()
                    for k, v in dict(member_info["DistrictAddress"]).items()
                    if k in ["Street", "City", "State", "Zip"]
                }
                district_address = "{Street}\n{City}, {State} {Zip}".format(
                    **district_address_info
                )
                legislator.add_contact_detail(
                    type="address", value=district_address, note="District Address"
                )
            else:
                self.warning(
                    "Could not find full district address for {}".format(full_name)
                )

            district_contact_info = self.clean_list(
                [member_info["DistrictAddress"][x] for x in ["Email", "Phone", "Fax"]]
            )

            # Same issue with district email. See above comment
            if district_contact_info[0] and "@" not in district_contact_info[0]:
                district_contact_info[0] = None

            if district_contact_info[0]:
                # Site was hacked in the past
                assert "quickrxdrugs@yahoo.com" not in district_contact_info[0]

            if district_contact_info[1]:
                legislator.add_contact_detail(
                    type="voice",
                    value=district_contact_info[1],
                    note="District Address",
                )
            if district_contact_info[2]:
                legislator.add_contact_detail(
                    type="fax", value=district_contact_info[2], note="District Address"
                )
            if district_contact_info[0]:
                legislator.add_contact_detail(
                    type="email",
                    value=district_contact_info[0],
                    note="District Address",
                )

            legislator.add_link(url)
            legislator.add_source(self.ssource)
            legislator.add_source(
                HOMEPAGE_URLS[chamber].format(**{"code": guid, "sid": sid})
            )

            yield legislator

    def scrape(self, session=None, chamber=None):
        if not session:
            session = self.latest_session()
            self.info("no session specified, using %s", session)

        chambers = [chamber] if chamber is not None else ["upper", "lower"]

        yield from self.scrape_session(session, chambers)
