from suds.client import Client

url = 'http://webservices.legis.ga.gov/GGAServices/%s/Service.svc?wsdl'


def get_client(service):
    client = Client(get_url(service))
    return client


def get_url(service):
    return url % (service)
