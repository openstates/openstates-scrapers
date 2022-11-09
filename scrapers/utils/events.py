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
