import hashlib
import uuid


def hash_event_key(event_key_str):
    """
    Used to shorten event identifier strings while maintaining uniqueness.
    :param event_key_str: type str - event identifier of variable length
    :return: type str - unique hash of event identifier
    """
    hash_val = hashlib.md5()
    hash_val.update(event_key_str.encode("utf-8"))
    hex_encoded_hash = hash_val.hexdigest()
    uuid_hex = uuid.UUID(hex_encoded_hash)
    unique_event_hash_str = str(uuid_hex)
    return unique_event_hash_str


# the current function to set coordinates requires a
# valid URL and Note, which we often don't have.
# so this will add just coordinates
def set_coordinates(event, lat, lon):
    # the schema requires strings for these
    coords = {
        "latitude": str(lat),
        "longitude": str(lon),
    }
    loc_dict = event.location
    loc_dict["coordinates"] = coords
    event.__setattr__("location", loc_dict)


def set_location_url(event, url: str):
    loc_dict = event.location
    loc_dict["url"] = url
    event.__setattr__("location", loc_dict)


# loop through a dict of
# {"location string", (lat, lon)} entries
# and update the location lat/lon if any matches are found
def match_coordinates(event, locations):
    for location, coords in locations.items():
        if location.lower() in event.location.get("name").lower():
            set_coordinates(event, coords[0], coords[1])
            return
