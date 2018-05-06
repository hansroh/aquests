
class tc:
    WHITE = '\033[97m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    OKBLUE = '\033[94m'
    WARNING = '\033[93m'
    OKGREEN = '\033[92m'
    FAIL = '\033[91m'
    GREY = '\033[90m'
    
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    ENDC = '\033[0m'
    
    @classmethod
    def _wrap (cls, s, c):
        return "{}{}{}".format (c, s, cls.ENDC)
    
    @classmethod
    def default (cls, s):
        return s
    
    @classmethod
    def warn (cls, s):
        return cls._wrap (s, cls.WARNING)
    
    @classmethod
    def expt (cls, s):
        return cls._wrap (s, cls.FAIL)
    
    @classmethod
    def fail (cls, s):
        return cls._wrap (s, cls.MAGENTA)
    
    @classmethod
    def error (cls, s):
        return cls._wrap (s, cls.FAIL)
    
    @classmethod
    def primary (cls, s):
        return cls._wrap (s, cls.OKBLUE)
    
    @classmethod
    def secondary (cls, s): 
        return cls._wrap (s, cls.CYAN)
    
    @classmethod
    def info (cls, s):
        return cls._wrap (s, cls.OKGREEN)
    
    @classmethod
    def white (cls, s):
        return cls._wrap (s, cls.WHITE)
    
    @classmethod
    def grey (cls, s):
        return cls._wrap (s, cls.GREY)
