import datetime
from typing import Literal

old_base_url = "https://www.legis.state.pa.us"
base_url = "https://www.palegis.us"
urls = {
    "people": {
        "upper": "{}/senate/members".format(base_url),
        "lower": "{}/house/members".format(base_url),
    },
    "committees": {
        "upper": "{}/senate/committees/committee-list".format(base_url),
        "lower": "{}/house/committees/committee-list".format(base_url),
    },
    "events": {
        "upper": "{}/senate/committees/meeting-schedule".format(base_url),
        "lower": "{}/house/committees/meeting-schedule".format(base_url),
    },
    "contacts": {
        "upper": "{}/senate/committees/member-assignments".format(base_url),
        "lower": "{}/house/committees/member-assignments".format(base_url),
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
        "https://www.palegis.us/legislation/bills/bill-index?&display=index"
        "&sessyr=%s&sessind=%s&billbody=%s"
        % (start_year(session), special, bill_abbr(chamber))
    )


def info_url(session, special, bill_number):
    bill_number = bill_number.replace(" ", "").lower()
    if special == 0:
        return "https://www.palegis.us/legislation/bills/%s/%s" % (
            start_year(session),
            bill_number,
        )
    else:
        return "https://www.palegis.us/legislation/bills/%s/%s/%s" % (
            start_year(session),
            special,
            bill_number,
        )


def vote_url(chamber, year, special, rc_number):
    return (
        "https://www.palegis.us/%s/roll-calls/summary?sessYr=%s&sessInd=%s&rcNum=%s"
        % (
            chamber,
            year,
            special,
            rc_number,
        )
    )


def committee_vote_url(
    chamber, year, special, bill_body, biil_type, bill_num, comm_code
):
    return (
        "https://www.palegis.us/%s/committees/roll-call-votes/vote-list?"
        "sessYr=%s&sessInd=%s&billBody=%s&billType=%s&billNum=%s&committeeCode=%s"
        % (
            chamber,
            year,
            special,
            bill_body,
            biil_type,
            bill_num,
            comm_code,
        )
    )


def parse_action_date(date_str):
    date_str = date_str.lower()
    date_str = date_str.replace("sept", "september")
    date_str = date_str.replace(",", "").replace(".", "")
    try:
        return datetime.datetime.strptime(date_str, "%B %d %Y")
    except ValueError:
        return datetime.datetime.strptime(date_str, "%b %d %Y")


def get_sponsor_chamber(name: str) -> Literal["upper", "lower"]:
    chamber = None
    if "Sen." in name or "Senator" in name:
        chamber = "upper"
    elif "Rep." in name or "Representative" in name:
        chamber = "lower"
    return chamber


def clean_sponsor_name(name: str) -> str:
    if name:
        return (
            name.replace("Senator", "")
            .replace("Representative", "")
            .replace("Sen.", "")
            .replace("Rep.", "")
            .strip()
            .title()
        )
    else:
        return ""
