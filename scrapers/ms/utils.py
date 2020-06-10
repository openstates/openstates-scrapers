import re


def clean_committee_name(comm_name):
    comm_name = comm_name.strip()
    comm_name = re.sub(" ?[-,] (Co|Vice)?[- ]?Chair$", "", comm_name)
    comm_name = re.sub("Appropriations - S/C:", "Appropriations-S/C on", comm_name)
    if comm_name == "Appropriations-S/C Stimulus":
        comm_name = "Appropriations-S/C on Stimulus"

    return comm_name


def chamber_name(chamber):
    if chamber == "upper":
        return "senate"
    else:
        return "house"


# if an xpath element el has a child child_el
# append it's contents to base_string in parens
def append_parens(el, child_el, base_string):
    if el.xpath(child_el):
        xpath_expr = "{}[1]/text()".format(child_el)
        text = el.xpath(xpath_expr)[0]
        return "{} ({})".format(base_string, text)
    else:
        return base_string
