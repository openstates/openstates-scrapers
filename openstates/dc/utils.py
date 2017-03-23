import json

def decode_json(stringy_json):
    #the "json" they send is recursively string-encoded.
    if type(stringy_json) == dict:
        for key in stringy_json:
            stringy_json[key] = decode_json(stringy_json[key])

    elif type(stringy_json) == list:
        for i in range(len(stringy_json)):
            stringy_json[i] = decode_json(stringy_json[i])

    elif isinstance(stringy_json, str):
        if len(stringy_json) > 0 and stringy_json[0] in ["[","{",u"[",u"{"]:
            return decode_json(json.loads(stringy_json))
    return stringy_json



