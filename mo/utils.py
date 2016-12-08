import re


# remove whitespace, linebreaks, and end parentheses
def clean_text(text):
    newtext = re.sub(r"[\r\n]+", " ", text)
    newtext = re.sub(r"\s{2,}", " ", newtext)
    m = re.match(r"(.*)\(.*?\)", newtext)
    if not m:
        return newtext.strip()
    else:
        return m.group(1).strip()


def house_get_actor_from_action(text):
    m = re.search(r"\((\bH\b|\bS\b)\)", text)
    if not m:
        if text.endswith('Governor'):
            return 'Governor'
        else:
            return 'lower'

    abbrev = m.group(1)
    if abbrev == 'S':
        return 'upper'
    return 'lower'


def find_nodes_with_matching_text(page,xpath,regex):
    """
    Using an lxml node, find matching xpath results that have text content
    matching the regex that is passed in here.
    """
    xpath_matches = page.xpath(xpath)
    results = []
    for xp in xpath_matches:
        if re.search(regex,xp.text_content()):
            results.append(xp)
    return results

def senate_get_actor_from_action(text):
    if re.search("Prefiled", text):
        return 'upper'

    m = re.search(r"(\bH\b|\bS\b|House)", text)
    if not m:
        if text.endswith('Governor'):
            return 'Governor'
        else:
            return 'upper'

    if m.group(1) == 'S':
        return 'upper'
    else:
        return 'lower'
