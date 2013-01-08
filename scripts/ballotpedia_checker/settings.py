CLIENT_ID = None  # Something like '123467893423.apps.googleusercontent.com'
CLIENT_SECRET = None # Something like 'asdlfkalskdjhfaslkdjhflaksj'
REDIRECT_URI = None # Something like 'urn:ietf:wg:oauth:2.0:oob'

try:
    from local_settings import *
except ImportError:
    pass