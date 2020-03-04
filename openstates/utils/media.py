import mimetypes


# note this is just guessing based on the url,
# not downloading/parsing anything
def get_media_type(url):
    media_type = mimetypes.guess_type(url)
    return media_type[0]
