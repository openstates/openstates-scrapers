import json
import requests


API_BASE_URL = 'http://lims.dccouncil.us/_layouts/15/uploader/AdminProxy.aspx'
API_HEADERS = {
    'Content-Type': 'application/json',
    'User-Agent': 'openstates',
}


def api_request(path, **kwargs):
    url = '{}{}'.format(API_BASE_URL, path)
    headers = dict(API_HEADERS)
    headers.update(kwargs.pop('headers', {}))
    response = requests.post(url, headers=headers, **kwargs)
    response.raise_for_status()
    return decode_json(response.json())


def decode_json(stringy_json):
    # the "json" they send is recursively string-encoded.
    if isinstance(stringy_json, dict):
        for key in stringy_json:
            stringy_json[key] = decode_json(stringy_json[key])
    elif isinstance(stringy_json, list):
        for i in range(len(stringy_json)):
            stringy_json[i] = decode_json(stringy_json[i])
    elif isinstance(stringy_json, str):
        if len(stringy_json) > 0 and stringy_json[0] in ["[", "{"]:
            return decode_json(json.loads(stringy_json))
    return stringy_json
