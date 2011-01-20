from billy.conf import default_settings

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
