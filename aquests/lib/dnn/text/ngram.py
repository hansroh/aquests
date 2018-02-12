import re
import string

class NGram:
    def __init__ (self, t):
        self._alnums, self.t = self.filter (t)        
        
    rx_splt = re.compile ('[\s%s]' % re.escape('!"#$%&\'()*+,:;<=>?@[\\]^_`{|}~'))        
    def filter (self, t):
        alnums = []
        for each in self.rx_splt.split (t):
            if self.rx_alnum.match (each):
                alnums.append (each)
        return alnums, re.sub ("(%s)" % "|".join (alnums), '', t)
    
    def alnums (self):
        return self._alnums
       
    def ngram (self, n = 2):        
        sentance = []
        for phrase in self.preprocess (self.t):                
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
