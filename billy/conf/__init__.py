import argparse

from billy.conf import default_settings

base_arg_parser = argparse.ArgumentParser(add_help=False)

base_arg_parser.add_argument('-v', '--verbose', action='count',
                             dest='verbose', default=False,
                             help=("be verbose (use multiple times for "
                                   "more debugging information)"))
base_arg_parser.add_argument('-d', '--data_dir', type=str,
                             help='scraped data directory',
                             dest='BILLY_DATA_DIR')
base_arg_parser.add_argument('--votesmart_key', type=str,
                             help='the Project Vote Smart API key to use',
                             dest='VOTESMART_API_KEY')
base_arg_parser.add_argument('--sunlight_key', type=str,
                             help='the Sunlight API key to use',
                             dest='SUNLIGHT_SERVICES_KEY')


class Settings(object):
    def __init__(self):
        pass

    def update(self, module):
        for setting in dir(module):
            if setting.isupper():
                setattr(self, setting, getattr(module, setting))

settings = Settings()
settings.update(default_settings)

try:
    import billy_settings
    settings.update(billy_settings)
except ImportError:
    pass
