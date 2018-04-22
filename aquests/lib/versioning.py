import warnings
from functools import wraps

def deprecated (f):
    @wraps(f)
    def wrapper (was, *args, **kwargs):
        warnings.simplefilter ('default')
        warnings.warn (
           "{} will be deprecated".format (f.__name__),
            DeprecationWarning
        )
        return f (was, *args, **kwargs)
    return wrapper