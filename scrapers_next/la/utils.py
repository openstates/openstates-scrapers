import re
from lxml.html import Element

def extract_info(name_and_title: list[str]) -> tuple[str, str, str]:
    """Extract and correct name

    Helper function called in `CommitteeDetail()` class,
    extracts full name and role of each member.

    :param name_and_title: Name and title data
    :return: Tuple containing Last, First and Role
    """
    last_name, *first_name = name_and_title[0].split(", ")
    first_name = ", ".join(first_name)
    role = name_and_title[1].split("|")[0]

    return last_name, first_name, role


def remove_title_reorder_name(person_name: str) -> str:
    """Remove titles from text

    :param person_name: Person text
    """
    name = re.sub(
        r"Treasurer|(Chairman-)|(Lieutenant)? ?Governor|Attorney General|Secretary of State|Senate President|House Speaker|Senator|Representative|Commissioner",
        "",
        person_name,
    )
    name = re.sub(r"( - .*)|(, (Vice)? ?Chairman)", "", name)
    name = re.sub("\(?Sen\.\)?|\(?Rep\.\)?", "", name)
    name = re.sub("Representative|Senator", "", name)
    name = re.sub(r", [A-Z]{3,}.*", "", name)
    name = re.sub(r"\"\w+\"", "", name)
    name = name.strip()
    if re.match("\w+, \w+", name):
        m = re.match(r"Sr\.|Jr\.|III?|IV|V", name.split()[-1])
        if m:
            a, b = name.split(",", 1)
            b = b.replace(m.group(), "")
            name = f"{b.strip()} {a.strip()}, {m.group()}"
        else:
            a, b = name.split(",", 1)
            name = f"{b.strip()} {a.strip()}"
    clean_name = name.strip()
    return clean_name


def select_chamber(comm_url: str, comm_name: str) -> str:
    """Identify chamber in miscellaneous cases.

    This gets us roughly where we want to be. Not all Misc committees are
    legislative though so we need to do some cleanup here.

    :param comm_url: The committee website url
    :param comm_name: The committee name
    :return: committee chamber type
    """
    if "cid=h" in comm_url.lower():
        return "lower"
    elif "Sen_Committees" in comm_url or "Senate" in comm_name:
        return "upper"
    return "legislature"


def _identify_member_role(row_content: str) -> str:
    """Normalize member role information

    :param row_content: Row content that contains role type
    :return: normalized role type
    """
    for opt in ["Ex Officio", "Co-Chairmain", "Chairman", "Vice Chair"]:
        if opt in row_content:
            return opt.lower()
    if "Interim Member" in row_content:
        return "interim"
    elif "Ex-O" in row_content:
        return "ex officio"
    return "member"

def _manually_fix_broken_links(link: Element) -> Element:
    """Fix a couple broken or incorrect links

    :param link: Link html element
    :return: Link element
    """
    if link.get('href') == "http://www.doa.la.gov/Pages/IEB/index.aspx":
        link.set("href", "https://www.doa.la.gov/state-employees/interim-emergency-board/board-info/board-members/")
    elif link.get('href') == "http://jlcb.legis.la.gov/":
        link.set("href", "https://jlcb.legis.la.gov/default_Members")
    return link