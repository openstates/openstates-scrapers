from pupa.scrape import Jurisdiction, Organization
import openstates_metadata


# this metaclass is a hack to only add the classification on subclasses
# pupa checks for a few properties to ensure it has a complete Jurisdiction
# and if they're all present on State it'll try to run with it instead
# of the appropriate subclass.  this works around that
class MetaShim(type):
    def __new__(cls, name, bases, dct):
        c = super().__new__(cls, name, bases, dct)
        if name != "State":
            c.classification = "government"
            # while we're here, load the metadata (formerly on a cached property)
            c.metadata = openstates_metadata.lookup(name=name)
        return c


class State(Jurisdiction, metaclass=MetaShim):
    @property
    def division_id(self):
        return self.metadata.division_id

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
