import re
from pydantic import BaseModel, validator
from openstates.people.models.people import Link, ContactType, PersonIdBlock, PartyName


PARTIES = {
    "d": "Democratic",
    "r": "Republican",
    "dem": "Democratic",
    "rep": "Republican",
    "ind": "Independent",
    "democrat": "Democratic",
}


class BaseModelConfig(BaseModel):
    # switch this to be openstates.people.models.common.BaseModel once ready to merge
    class Config:
        anystr_strip_whitespace = True
        extra = "forbid"
        validate_assignment = True
        use_enum_values = True


class ScrapeContactDetail(BaseModelConfig):
    # switch this to be a version of openstates' ContactDetail without root_validator when ready
    note: ContactType
    address: str = ""
    voice: str = ""
    fax: str = ""


class ScrapePerson(BaseModelConfig):
    name: str
    state: str
    party: PartyName
    district: str
    chamber: str
    image: str = ""
    email: str = ""
    given_name: str = ""
    family_name: str = ""
    suffix: str = ""

    links: list[Link] = []
    sources: list[Link] = []
    ids: PersonIdBlock = PersonIdBlock()
    capitol_office = ScrapeContactDetail(note="Capitol Office")
    district_office = ScrapeContactDetail(note="District Office")
    extras: dict = {}

    @validator("party", pre=True)
    def common_abbreviations(cls, val):
        # replace with proper name if one exists
        return PARTIES.get(val.lower(), val)

    @validator("name")
    def collapse_spaces(cls, val):
        return re.sub(r"\s+", " ", val).strip()

    def add_link(self, url, note=""):
        self.links.append(Link(url=url, note=note))

    def add_source(self, url, note=""):
        self.sources.append(Link(url=url, note=note))
