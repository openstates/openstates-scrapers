import argparse

from billy.conf import default_settings

base_arg_parser = argparse.ArgumentParser(add_help=False)

base_arg_parser.add_argument('-v', '--verbose', action='count',
                             dest='verbose', default=False,
                             help=("be verbose (use multiple times for "
                                   "more debugging information)"))
base_arg_parser.add_argument('-d', '--data_dir',
                             help='scraped data directory',
                             dest='BILLY_DATA_DIR')
base_arg_parser.add_argument('--votesmart_key',
                             help='the Project Vote Smart API key to use',
                             dest='VOTESMART_API_KEY')
base_arg_parser.add_argument('--sunlight_key',
                             help='the Sunlight API key to use',
                             dest='SUNLIGHT_SERVICES_KEY')
base_arg_parser.add_argument('--retries', type=int,
                             dest='SCRAPELIB_RETRY_ATTEMPTS')
base_arg_parser.add_argument('--retry_wait', type=int,
                             dest='SCRAPELIB_RETRY_WAIT_SECONDS')
base_arg_parser.add_argument('--cache_dir', dest='BILLY_CACHE_DIR')
base_arg_parser.add_argument('--error_dir', dest='BILLY_ERROR_DIR')


class Settings(object):
    def __init__(self):
        pass

    def update(self, module):
        for setting in dir(module):
            if setting.isupper():
                val = getattr(module, setting)
                if val is not None:
                    setattr(self, setting, val)

settings = Settings()
settings.update(default_settings)

try:
    import billy_settings
    settings.update(billy_settings)
except ImportError:
    pass
