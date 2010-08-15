import re, string

def clean_string(s):
    return re.sub('[^0-9]', '', s)

def year_from_session(session):
    return int(session.split()[0])

def separate_name(full_name):
    separated_full_name = string.split(full_name, ' ')

    if len(separated_full_name) < 2:
        raise
    elif len(separated_full_name) == 2:
        first_name = separated_full_name[0]
        last_name = separated_full_name[1]
        middle_name = ''
    elif len(separated_full_name) == 3:
        first_name = separated_full_name[0]
        last_name = separated_full_name[2]
        middle_name = separated_full_name[1]
    else:
        first_name = separated_full_name[0]
        middle_name = separated_full_name[1]
        last_name_list = separated_full_name[1:]
        last_name = ""
        for name in last_name_list:
            last_name += name
  
    return full_name, first_name, middle_name, last_name 

def house_url(chamber):
    if chamber == "upper":
        return "http://www.leg.wa.gov/Senate/Senators/Pages/default.aspx"
    else:
        return "http://www.leg.wa.gov/house/representatives/Pages/default.aspx"

def legs_url(chamber, name_for_url):
    if chamber == 'upper':
        return "http://www.leg.wa.gov/senate/senators/Pages/" + name_for_url + ".aspx"
    else: 
        return "http://www.leg.wa.gov/house/representatives/Pages/" + name_for_url + ".aspx"

def votes_url(id1, id2):
    return "http://flooractivityext.leg.wa.gov/rollcall.aspx?id=" + id1 + "&bienId=" +id2