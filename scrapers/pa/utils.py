import datetime


base_url = "http://www.legis.state.pa.us"
members_url = "{}/cfdocs/legis/home/member_information".format(base_url)
urls = {
    "people": {
        "upper": "{}/senators_alpha.cfm".format(members_url),
        "lower": "{}/representatives_alpha.cfm".format(members_url),
    },
    "committees": {
        "upper": "{}/senators_ca.cfm".format(members_url),
        "lower": "{}/representatives_ca.cfm".format(members_url),
    },
    "events": {
        "upper": "{}/cfdocs/legis/cms/index.cfm?chamber=S".format(base_url),
        "lower": "{}/cfdocs/legis/cms/index.cfm?chamber=H".format(base_url),
    },
    "contacts": {
        "upper": "{}/contact.cfm?body=S".format(members_url),
        "lower": "{}/contact.cfm?body=H".format(members_url),
    },
}


def bill_abbr(chamber):
    if chamber == "upper":
        return "S"
    else:
        return "H"


def start_year(session):
    return session[0:4]


def bill_list_url(chamber, session, special):
    return (
        "http://www.legis.state.pa.us/cfdocs/legis/bi/"
        "BillIndx.cfm?sYear=%s&sIndex=%i&bod=%s"
        % (start_year(session), special, bill_abbr(chamber))
    )


def history_url(chamber, session, special, type, bill_number):
    return (
        "http://www.legis.state.pa.us/cfdocs/billinfo/"
        "bill_history.cfm?syear=%s&sind=%i&body=%s&type=%s&BN=%s"
        % (start_year(session), special, bill_abbr(chamber), type, bill_number)
    )


def info_url(chamber, session, special, type, bill_number):
    return (
        "http://www.legis.state.pa.us/cfdocs/billinfo/"
        "billinfo.cfm?syear=%s&sind=%i&body=%s&type=%s&BN=%s"
        % (start_year(session), special, bill_abbr(chamber), type, bill_number)
    )


def vote_url(chamber, session, special, type, bill_number):
    return (
        "http://www.legis.state.pa.us/cfdocs/billinfo/"
        "bill_votes.cfm?syear=%s&sind=%d&body=%s&type=%s&bn=%s"
        % (start_year(session), special, bill_abbr(chamber), type, bill_number)
    )


def parse_action_date(date_str):
    date_str = date_str.lower()
    date_str = date_str.replace("sept", "september")
    date_str = date_str.replace(",", "").replace(".", "")
    try:
        return datetime.datetime.strptime(date_str, "%B %d %Y")
    except ValueError:
        return datetime.datetime.strptime(date_str, "%b %d %Y")
