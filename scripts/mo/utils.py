import re

# remove whitespace, linebreaks, and end parentheses
def clean_text(text):
    newtext = re.sub(r"[\r\n]+"," ",text)
    newtext = re.sub(r"\s{2,}"," ",newtext)
    m = re.match(r"(.*)\(.*?\)",newtext)
    if m == None:
        return newtext
    else:
        return m.group(1)

# look in the action to try to parse out the chamber
# that took the action
def house_get_chamber_from_action(text):
    m = re.search(r"\((H|S)\)",text)
    if m == None:
        return None
    abbrev = m.group(1)
    if abbrev == 'S':
        return 'upper'
    return 'lower'

# look in the action to try to parse out the chamber
# that took the action
def senate_get_chamber_from_action(text):
    if re.search("Prefiled",text):
        return 'upper'
    m = re.search(r"^(H|S)",text)
    if m == None:
        m = re.search(r" (H|S) ",text)
    if m != None:
        if m.group(1) == 'S':
            return 'upper'
        else:
            return 'lower'
    return None
