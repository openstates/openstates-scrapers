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
        'NAME': 'openstates',
    }
}

TIME_ZONE = 'UTC'  # or 'America/New_York'?
LANGUAGE_CODE = 'en-us'
SITE_ID = 1

USE_I18N = False
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
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'locksmith.mongoauth.middleware.APIKeyMiddleware',
    'billy.web.public.middleware.LimitStatesMiddleware',
    #'django.contrib.sessions.middleware.SessionMiddleware',
    #'django.middleware.csrf.CsrfViewMiddleware',
    #'django.contrib.auth.middleware.AuthenticationMiddleware',
    #'django.contrib.messages.middleware.MessageMiddleware',
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
    'django.contrib.humanize',
    'django.contrib.staticfiles',
    'billy.web.api',
    'billy.web.admin',
    'billy.web.public',
    'locksmith.mongoauth',
    'markup_tags',
    'tweets',
    'funfacts',
)

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


# billy/web/public
ACTIVE_STATES = [u'co', u'de', u'ny', u'in', u'tn',
                 u'me', u'wv', u'mt', u'va', u'ak',
                 u'al', u'ar', u'ct', u'az', u'ca',
                 u'dc', u'fl', u'ga', u'hi', u'ia',
                 u'id', u'il', u'ks', u'ky', u'la',
                 u'ma', u'md', u'mi', u'mn', u'mo',
                 u'ms', u'nc', u'nd', u'ne', u'nh',
                 u'nj', u'nm', u'nv', u'oh', u'or',
                 u'pr', u'ri', u'sc', u'sd', u'tx',
                 u'ut', u'vt', u'wa', u'wi', u'wy',
                 u'ok', u'pa']
ACTIVE_STATES = 'ca il la md mn tx wi'.split()

ENABLE_ELASTICSEARCH = True

# Display API urls on pages.
NERD_MODE = True

# Display links to admin pages where relevant.
ADMIN_MODE = True


try:
    from .local_settings import *
except ImportError:
    pass
