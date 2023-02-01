import requests


def get_membership_dict(url):
    membership = {}
    response = requests.get(url)
    for each_legislator in response.json()["legislators"]:
        member_id = each_legislator["id"]
        name = each_legislator["formatName"]
        membership[member_id] = name
    return membership
