import re
import uuid
from collections import OrderedDict
from openstates.utils import abbr_to_jid
from spatula import Workflow


def clean_spaces(text):
    return re.sub(r"\s+", " ", text).strip()


PARTIES = {
    "d": "Democratic",
    "r": "Republican",
    "dem": "Democratic",
    "rep": "Republican",
    "democrat": "Democratic",
    "republican": "Republican",
}


class ContactDetail:
    def __init__(self, note):
        self.note = note
        self.voice = None
        self.fax = None
        self.address = None

    def to_dict(self):
        d = {}
        for key in ("voice", "fax", "address"):
            val = getattr(self, key)
            if val:
                # if key in ("voice", "fax"):
                #     val = reformat_phone_number(val)
                d[key] = val
        if d:
            d["note"] = self.note
        return d


class Person:
    def __init__(
        self,
        name,
        *,
        state,
        party,
        district,
        chamber,
        image=None,
        email=None,
        given_name=None,
        family_name=None,
        suffix=None,
    ):
        self.name = clean_spaces(name)
        self.party = party
        self.district = str(district)
        self.chamber = chamber
        self.state = state
        self.given_name = given_name
        self.family_name = family_name
        self.suffix = suffix
        self.image = image
        self.email = email
        self.links = []
        self.sources = []
        self.capitol_office = ContactDetail("Capitol Office")
        self.district_office = ContactDetail("District Office")
        self.ids = {}
        self.extras = {}

    def to_dict(self):
        party = PARTIES.get(self.party.lower(), self.party)
        d = OrderedDict(
            {
                "id": f"ocd-person/{uuid.uuid4()}",
                "name": str(self.name),
                "party": [{"name": party}],
                "roles": [
                    {
                        "district": self.district,
                        "type": self.chamber,
                        "jurisdiction": abbr_to_jid(self.state),
                    }
                ],
                "links": self.links,
                "sources": self.sources,
            }
        )
        if self.given_name:
            d["given_name"] = str(self.given_name)
        if self.family_name:
            d["family_name"] = str(self.family_name)
        if self.suffix:
            d["suffix"] = str(self.suffix)
        if self.image:
            d["image"] = str(self.image)
        if self.email:
            d["email"] = str(self.email)
        if self.ids:
            d["ids"] = self.ids
        if self.extras:
            d["extras"] = self.extras

        # contact details
        d["contact_details"] = []
        if self.district_office.to_dict():
            d["contact_details"].append(self.district_office.to_dict())
        if self.capitol_office.to_dict():
            d["contact_details"].append(self.capitol_office.to_dict())

        return d

    def add_link(self, url, note=None):
        if note:
            self.links.append({"url": url, "note": note})
        else:
            self.links.append({"url": url})

    def add_source(self, url, note=None):
        if note:
            self.sources.append({"url": url, "note": note})
        else:
            self.sources.append({"url": url})


class PeopleWorkflow(Workflow):
    pass
    # def save_object(self, obj, output_dir):
    #     dump_obj(obj, output_dir=Path(output_dir))
