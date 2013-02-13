import os
DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    ('James Turk', 'jturk@sunlightfoundation.com'),
    ('Thom Neale', 'tneale@sunlightfoundation.com'),
    ('Paul Tagliamonte', 'paultag@sunlightfoundation.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(os.path.dirname(__file__), 'openstates.sqlite3'),
    }
}

TIME_ZONE = 'UTC'  # or 'America/New_York'?
LANGUAGE_CODE = 'en-us'
SITE_ID = 1

USE_I18N = True
USE_L10N = False
USE_TZ = True

MEDIA_ROOT = ''
MEDIA_URL = ''

DATE_FORMAT = 'Y-m-d'
TIME_FORMAT = 'H:i:s'
DATETIME_FORMAT = 'Y-m-d H:i:s'

STATIC_ROOT = os.path.join(os.path.dirname(__file__), '..', 'collected_static')
STATIC_URL = '/media/'
STATICFILES_DIRS = (
    os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'media')),
)
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'boh2w74##xm+*25ybdk6dmyj2$c)v%nl!sp7zlg$fp+e!q47#('

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.request',
    'django.contrib.auth.context_processors.auth',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'locksmith.mongoauth.middleware.APIKeyMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'openstates_site.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'openstates_site.wsgi.application'

TEMPLATE_DIRS = (
    os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates')),
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.humanize',
    'django.contrib.staticfiles',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.admin',
    'django.contrib.sites',
    'billy.web.api',
    'billy.web.admin',
    'billy.web.public',
    'locksmith.mongoauth',
    'social_auth',
    'markup_tags',
    'funfacts',
)

AUTHENTICATION_BACKENDS = (
    'sunlightauth.backends.SunlightBackend',
    #'django.contrib.auth.backends.ModelBackend',
)

SUNLIGHT_AUTH_BASE_URL = 'http://login.sunlightfoundation.com/'
SUNLIGHT_AUTH_APP_ID = 'openstates'
#SUNLIGHT_AUTH_SECRET = 'set in local settings'
SUNLIGHT_AUTH_SCOPE = []

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

LOGIN_REDIRECT_URL = '/'
LOGIN_URL = '/login/sunlight/'

LOCKSMITH_REGISTRATION_URL = 'http://services.sunlightlabs.com/accounts/register/'

SUNLIGHT_AUTH_SECRET = 'fd53166ae78bad2155548b767489fa'

try:
    from .local_settings import *
except ImportError:
    pass
