import mimetypes


# note this is just guessing based on the url, not downloading/parsing anything
def get_media_type(url, *, default=None):
    media_type = mimetypes.guess_type(url)
    if media_type[0]:
        return media_type[0]
    elif default:
        return default
    else:
        raise ValueError(f"could not guess mimetype for {url}, set default")
