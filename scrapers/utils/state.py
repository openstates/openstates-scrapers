from openstates.scrape import Jurisdiction, Organization
from openstates.metadata import lookup

_name_fixes = {
    "SouthCarolina": "South Carolina",
    "NorthCarolina": "North Carolina",
    "SouthDakota": "South Dakota",
    "NorthDakota": "North Dakota",
    "RhodeIsland": "Rhode Island",
    "NewHampshire": "New Hampshire",
    "NewJersey": "New Jersey",
    "NewYork": "New York",
    "NewMexico": "New Mexico",
    "WestVirginia": "West Virginia",
    "PuertoRico": "Puerto Rico",
    "DistrictOfColumbia": "District of Columbia",
}


# this metaclass is a hack to only add the classification on subclasses
# update checks for a few properties to ensure it has a complete Jurisdiction
# and if they're all present on State it'll try to run with it instead
# of the appropriate subclass.  this works around that
class MetaShim(type):
    def __new__(cls, name, bases, dct):
        c = super().__new__(cls, name, bases, dct)
        if name != "State":
            c.classification = "state"
            # while we're here, load the metadata (formerly on a cached property)
            name = _name_fixes.get(name, name)
            c.metadata = lookup(name=name)
        return c


class State(Jurisdiction, metaclass=MetaShim):
    @property
    def division_id(self):
        return self.metadata.division_id

    @property
    def jurisdiction_id(self):
        return "{}/government".format(
            self.division_id.replace("ocd-division", "ocd-jurisdiction"),
        )

    @property
    def name(self):
        return self.metadata.name

    @property
    def url(self):
        return self.metadata.url

    def get_organizations(self):
        legislature = Organization(
            name=self.metadata.legislature_name, classification="legislature"
        )
        yield legislature
        if not self.metadata.unicameral:
            yield Organization(
                self.metadata.upper.name,
                classification="upper",
                parent_id=legislature._id,
            )
            yield Organization(
                self.metadata.lower.name,
                classification="lower",
                parent_id=legislature._id,
            )
