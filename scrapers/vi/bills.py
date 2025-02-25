from openstates.scrape import Bill, Scraper
import dateutil


class VIBillScraper(Scraper):
    session = ""
    committees = []
    sponsors = {}

    # this object's keys are order sensitive
    action_mapping = {
        "U_DateRec": ("received", []),
        "U_DateAssign": ("Assigned", []),
        "U_DateToSen": (
            "To Senate",
            [],
        ),  # what is this action? it comes before introduction
        "U_DateIntro": ("Introduced", ["introduction"]),
        "U_DateToLtGov": ("Sent to Lt. Governor", ["executive-receipt"]),
        "U_DateToGov": ("Sent to Governor", ["executive-receipt"]),
        "U_DateVetoed": ("Vetoed", ["executive-veto"]),
        "U_DateAppGov": ("Approved by Governor", ["executive-signature"]),
    }

    bill_type_overrides = {
        "bill&amend": "bill",
        "lease": "contract",
        "amendment": "bill",
    }

    def scrape(self, session=None):

        data = {
            "LegisNumber": session,
            "CardCode": "",
            "BillNumber": "",
            "ActNumber": "",
            "Subject": "",
            "BRNumber": "",
            "ResolutionNumber": "",
            "AmendmentNumber": "",
            "GovernorsNumber": "",
            "SponsorCoSponsor": "0",
        }
        page = self.post(
            "https://billtracking.legvi.org:8082/search", data=data, verify=False
        ).json()

        for row in page["recordset"]:
            if row["BillNumber"] or row["ResolutionNumber"]:
                yield from self.scrape_bill(session, row)

    def scrape_bill(self, session, row: dict):
        data = {"docEntryID": row["ID"]}

        row = self.post(
            "https://billtracking.legvi.org:8082/details", data=data, verify=False
        ).json()
        row = row["recordset"][0]

        identifier = row["U_BillNumber"] or row["U_ResolutionNumber"]
        title = row["U_Subject"]
        bill_type = row["U_RequestType"].lower()

        if bill_type in self.bill_type_overrides:
            bill_type = self.bill_type_overrides[bill_type]

        bill = Bill(
            identifier=identifier,
            legislative_session=session,
            chamber="legislature",
            title=title,
            classification=bill_type,
        )
        bill.add_source("https://billtracking.legvi.org/")

        for sponsor in row["U_CardName"]:
            if sponsor:
                bill.add_sponsorship(sponsor, "primary", "person", primary=True)

        for action_code in self.action_mapping.keys():
            action = self.action_mapping[action_code]
            if action_code in row and row[action_code] is not None:
                when = dateutil.parser.parse(row[action_code]).date()
                bill.add_action(
                    action[0], when, chamber="legislature", classification=action[1]
                )

        if "U_BillNumberLink" in row and row["U_BillNumberLink"] is not None:
            bill_num = row["U_BillNumberLink"]
            bill.add_version_link(
                f"Bill {bill_num}",
                f"https://billtracking.legvi.org:8082/preview/Bill%2F{bill_num}",
                media_type="application/pdf",
                on_duplicate="ignore",
            )

        if "U_ActNumberLink" in row and row["U_ActNumberLink"] is not None:
            act_num = row["U_ActNumberLink"]
            bill.add_version_link(
                f"Act {act_num}",
                f"https://billtracking.legvi.org:8082/preview/Act%2F{act_num}",
                media_type="application/pdf",
                on_duplicate="ignore",
            )

        yield bill
