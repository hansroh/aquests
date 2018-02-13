import re
import string

class NGram:
    def __init__ (self, t):
        self._alnums, self.t = self.filter (t)        
        
    rx_splt = re.compile ('[\s%s]' % re.escape('!"#$%&\'()*+,:;<=>?@[\\]^_`{|}~'))        
    rx_force_space = re.compile('(?P<alnum>[0-9a-z]+)', re.I)
    
    def filter (self, t):
        t = self.rx_force_space.sub (" \g<alnum> ", t)
        alnums = []
        for each in self.rx_splt.split (t):
            if self.rx_alnum.search (each):
                alnums.append (each)
        replaced = re.sub ("(%s)" % "|".join (alnums), '', t)
        return [each for each in alnums if not each.isdigit ()], replaced
    
    def alnums (self):
        return self._alnums
    
    def ngram (self, n = 2):        
        sentance = []
        for phrase in self.make_phrases (n):                
            for each in zip (*[phrase[i:] for i in range (n)]):
                each = list (each)
                if n == 2 and (each [0] == " " or each [-1] == " "):
                    continue                
                if each [0] == " ":
                    each [0] = "<"
                elif each [-1] == " ":
                    each [-1] = ">"    
                sentance.append ("".join (each))
        if n == 2:
            return sentance [:-1]
        return sentance    
    
    rx_punct = re.compile('[%s]' % re.escape(string.punctuation))
    rx_space = re.compile('\s+')
    rx_alnum = re.compile('[0-9a-z]{2,}', re.I)
        
    def preprocess (self, t):
        return [" " + self.rx_space.sub (" ", each).strip () + " " for each in self.rx_punct.split (t)]                
    
    def make_phrases (self, n):
        return self.preprocess (self.t)
    
    def analyze (self):
        return self.alnums () + self.ngram (2) + self.ngram (3)


class NGramV2 (NGram):
    # V2: if n is 2, ignoring all spaces    
    def preprocess_nospace (self, t):
        return [self.rx_space.sub ("", each).strip () for each in self.rx_punct.split (t)]

    def make_phrases (self, n = 2):        
        if n == 2:
            return self.preprocess_nospace (self.t)
        return self.preprocess (self.t)
        