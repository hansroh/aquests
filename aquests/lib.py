import warnings

warnings.simplefilter('default')
warnings.warn (
   "aquests.lib will be deprecated, use rs4",
    DeprecationWarning
)

from rs4 import (
    attrdict,
    confparse,
    logger,
    pathtool,
    siesta,
    termcolor
)
