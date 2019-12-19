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
