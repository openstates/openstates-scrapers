import json
from spatula import JsonPage, HtmlPage, CSS
from openstates.models import ScrapePerson


class LegDetail(JsonPage):
    example_source = (
        "https://www.njleg.state.nj.us/legislative-roster/328/senator-addiego"
    )

    def process_page(self):
        p = self.input

        # response is 3 lists: bio data, addresses, then committee memberships
        bio_data = self.data[0][0]

        p.email = bio_data["ccMailName"]
        if pos := bio_data["Legislative_Position"]:
            p.extras["position"] = pos

        for address_data in self.data[1]:
            if address_data["Address_Type"] == "District Office":
                office = p.district_office
            elif address_data["Address_Type"] == "Other":
                continue
            else:
                raise ValueError(
                    f"unexpected address type {address_data['Address_Type']}, update scraper"
                )

            if address_data["Street_Address"]:
                address = (
                    address_data["Street_Address"]
                    + "; "
                    + address_data["City"]
                    + " "
                    + address_data["State"]
                    + " "
                    + address_data["Zipcode"]
                )
                office.address = address
            office.voice = address_data["Phone_Number"]

        p.add_source(self.source.url)

        return p


class LegList(HtmlPage):
    source = "https://www.njleg.state.nj.us/legislative-roster"

    def process_page(self):
        data_elem = CSS("#__NEXT_DATA__").match_one(self.root).text_content()
        data = json.loads(data_elem)
        for item in data["props"]["pageProps"]["legrosterData"][0]:
            first = item["First_Name"]
            middle = item["Middle_Name"]
            last = item["Last_Name"]
            suffix = item["Suffix"]
            member_id = item["BioLink"].split("/")[2]
            url = "https://www.njleg.state.nj.us" + item["BioLink"]
            party = {"D": "Democratic", "R": "Republican"}[item["Party"]]
            district = item["Roster_District"]
            chamber = "upper" if item["Roster_House"] == "Senate" else "lower"
            if middle:
                name = f"{first} {middle} {last}"
            else:
                name = f"{first} {last}"
            if suffix:
                name += f", {suffix}"

            p = ScrapePerson(
                name=name,
                given_name=first,
                family_name=last,
                state="nj",
                chamber=chamber,
                party=party,
                district=district,
            )
            p.add_source(self.source.url)
            p.add_source(url)
            p.add_link(url)
            api_url = f"https://www.njleg.state.nj.us/api/legislatorData/legislatorBio/{member_id}"
            p.add_source(api_url)
            yield LegDetail(p, source=api_url)
