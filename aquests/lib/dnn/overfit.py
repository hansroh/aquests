import sys
import numpy as np

class Overfit:
    def __init__ (self, threshold, keep_count = 100):      
        self.min_cost = sys.maxsize
        self.lowest_unseen = 0
        self.threshold = threshold
        self.keep_count = keep_count
        self.overfitted_count = 0
        self.cost_log = []
        self.cost_ma20 = sys.maxsize
        self.best_cost_ma20 = sys.maxsize
    
    def is_overfit (self, cost):
        return self.add_cost (cost) [0]
        
    def add_cost (self, cost):
        overfit, lowest = False, False
        if cost < self.min_cost: 
            self.min_cost = cost   
            lowest = True        
            self.lowest_unseen = 0
        else:
            self.lowest_unseen += 1
            if self.lowest_unseen == 200:
               overfit = True
        
        self.cost_log.append (cost)
        if len (self.cost_log) < 20:
            return overfit, lowest
        
        self.cost_ma20 = np.mean (self.cost_log)
        self.cost_log = self.cost_log [-20:] 
        
        self.best_cost_ma20 = min (self.cost_ma20, self.best_cost_ma20)
        if self.cost_ma20 > self.best_cost_ma20 + (self.best_cost_ma20 * self.threshold):
            self.overfitted_count += 1
            # if occured  5 times sequencially
            if self.overfitted_count > self.keep_count:
                overfit = True
        else:
            self.overfitted_count = 0
    
        return overfit, lowest
    