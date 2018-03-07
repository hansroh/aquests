import tensorflow as tf
import numpy as np
import sys
import os, shutil
import random
from aquests.lib import pathtool
from . import overfit

class Task:
    def __init__ (self, dnns, attr):
        self.dnns = dnns
        self.attr = attr
        
    def __call__ (self, *args, **karg):
        results = []
        for dnn in self.dnns:
            results.append (getattr (dnn, self.attr) (*args, **karg))
        return np.array (results).transpose ()


class MultiDNN:
    def __init__ (self, *args):
        self.dnns = []
        self.y_div = [0]
        for i, arg in enumerate (args):
            if i % 2 == 0:
                self.dnns.append (arg)
                assert arg.name is not None
            else:
                self.y_div.append (sum (self.y_div) + arg)
        self.verbose_turned_offs = []
                        
    def __getattr__ (self, attr):
        return Task (self.dnns, attr)  
    
    def _get_segment (self, i, ys):
        return ys [:,self.y_div [i]:self.y_div [i+1]]
    
    def reset_dir (self, target):
        self.dnns [0].reset_dir (target)
    
    def reset_tensor_board (self, summaries_dir):
        for i, dnn in enumerate (self.dnns):
            dnn.reset_tensor_board (summaries_dir, i == 0)
        
    def is_overfit (self, cost, path, filename = None):
        results = []
        for i, dnn in enumerate (self.dnns):
            results.append (int (dnn.is_overfit (cost [i], path, filename)))
        return sum (results) == len (self.dnns)
            
    def write_summary (self, writer, feed_dict):
        for i in range (len (list (feed_dict.values ())[0])):
            feed_dict_ = {}
            for k, v in feed_dict.items ():
                feed_dict_ [k] = v [i]
            dnn = self.dnns [i]     
            dnn.write_summary (writer, feed_dict_)
                    
    def calculate_complex_accuracy (self, preds, ys, *args, **karg):
        results = []
        for i in range (len (self.y_div) - 1):   
            dnn = self.dnns [i]
            results.append (dnn.calculate_complex_accuracy (preds [i], self._get_segment (i, ys), *args, **karg))
        return np.array (results)     
    measure_accuracy = calculate_complex_accuracy
        
    def run (self, *ops, **kargs):
        ys = kargs.pop ("y")
        results = []
        for i in range (len (self.y_div) - 1):
            dnn = self.dnns [i]
            kargs ["y"] = self._get_segment (i, ys)            
            result = list (dnn.run (*tuple ([getattr (dnn, op.attr) for op in ops]), **kargs))
            results.append (result)                    
        return np.array (results, np.object).transpose ()
        