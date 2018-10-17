
def fix_name(name):
    # handles cases like Watson, Jr., Clovis
    if ', ' not in name:
        return name
    last, first = name.rsplit(', ', 1)
    return first + ' ' + last

