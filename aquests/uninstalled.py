
class Uninstalled:
    def __init__ (self, name, *args, **kargs):
        self.name = name

    def __call__ (self, *args, **kargs):
        raise ImportError ('cannot import {}, install first'.format (self.name))

