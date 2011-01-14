import re


def clean_committee_name(comm_name):
    comm_name = comm_name.strip()
    comm_name = re.sub(r' ?[-,]? ?\(?(Co|Vice)?[- ]?[Cc]hair\)?',
                       '',
                       comm_name)
    comm_name = re.sub(r'\d+/\d+/\d+ - \d+/\d+/\d+', '', comm_name)
    comm_name = re.sub('Appropriations - S/C:', 'Appropriations-S/C on',
                       comm_name).strip()
    if comm_name == 'Appropriations-S/C Stimulus':
        comm_name = 'Appropriations-S/C on Stimulus'

    return comm_name


def parse_ftp_listing(text):
    lines = text.strip().split('\r\n')
    return (' '.join(line.split()[3:]) for line in lines if line)


def chamber_name(chamber):
    if chamber == 'upper':
        return 'senate'
    else:
        return 'house'
