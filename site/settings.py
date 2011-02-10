import os

DEBUG = False
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    ('James Turk', 'jturk@sunlightfoundation.com'),
    ('Michael Stephens', 'mstephens@sunlightfoundation.com'),
)

MANAGERS = ADMINS
TIME_ZONE = 'UTC'
LANGUAGE_CODE = 'en-us'
SITE_ID = 1
USE_I18N = False

MEDIA_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                          'media/'))
MEDIA_URL = ''
ADMIN_MEDIA_PREFIX = '/admin_media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'qe_7q2@i9sskbz&hf5tx)39z0=shicxr*_57yr0jw2bxr7=i8+'

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'locksmith.auth.middleware.APIKeyMiddleware',
)

ROOT_URLCONF = 'billy.site.urls'

INSTALLED_APPS = (
    'django.contrib.humanize',
    'django.contrib.gis',
    'billy.site.api',
    'billy.site.geo',
    'billy.site.browse',
    'locksmith.auth',
)

DATE_FORMAT = 'Y-m-d'
TIME_FORMAT = 'H:i:s'
DATETIME_FORMAT = 'Y-m-d H:i:s'

try:
    from local_settings import *
except ImportError:
    pass
