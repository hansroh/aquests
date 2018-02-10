import sys
import numpy as np

class Overfit:
    def __init__ (self, threshold, keep_count = 5):      
        self.threshold = threshold  
        self.keep_count = keep_count
        self.overfitted_count = 0
        self.cost_log = []
        self.cost_ma20 = sys.maxsize
        self.best_cost_ma20 = sys.maxsize
    
    def add_cost (self, cost):
        self.cost_log.append (cost)   
        if len (self.cost_log) > 20:
             self.cost_ma20 = np.mean (self.cost_log)
             self.cost_log = self.cost_log [-20:] 
        
        self.best_cost_ma20 = min (self.cost_ma20, self.best_cost_ma20)
        if self.cost_ma20 > self.best_cost_ma20 + (self.best_cost_ma20 * self.threshold):
            self.overfitted_count += 1
            # if occured  5 times sequencially
            if self.overfitted_count > self.keep_count:
                return True
        else:
            self.overfitted_count = 0
            
