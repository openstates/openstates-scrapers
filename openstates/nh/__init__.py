from pupa.scrape import Jurisdiction, Organization


class NewHampshire(Jurisdiction):
    division_id = "ocd-division/country:us/state:nh"
    classification = "government"
    name = "New Hampshire"
    url = "http://gencourt.state.nh.us/"
    scrapers = {
    }
    parties = [
        {'name': 'Republican'},
        {'name': 'Democratic'}
    ]
    legislative_sessions = [
        {
            "_scraped_name": "2017 Session",
            "classification": "primary",
            "identifier": "2017",
            "name": "2017 Regular Session"
        }
    ]
    ignored_scraped_sessions = []

    def get_organizations(self):
        legislature_name = "New Hampshire General Court"
        lower_chamber_name = "House"
        lower_seats = None
        lower_title = "Representative"
        upper_chamber_name = "Senate"
        upper_seats = 0
        upper_title = "Senator"

        legislature = Organization(name=legislature_name,
                                   classification="legislature")
        upper = Organization(upper_chamber_name, classification='upper',
                             parent_id=legislature._id)
        lower = Organization(lower_chamber_name, classification='lower',
                             parent_id=legislature._id)

        for n in range(1, upper_seats+1):
            upper.add_post(
                label=str(n), role=upper_title,
                division_id='{}/sldu:{}'.format(self.division_id, n))
        for n in range(1, lower_seats+1):
            lower.add_post(
                label=str(n), role=lower_title,
                division_id='{}/sldl:{}'.format(self.division_id, n))

        yield legislature
        yield upper
        yield lower
