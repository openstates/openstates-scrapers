NS = {'wa': "http://WSLWebServices.leg.wa.gov/"}


def xpath(elem, path):
    """
    A helper to run xpath with the proper namespaces for the Washington
    Legislative API.
    """
    return elem.xpath(path, namespaces=NS)
