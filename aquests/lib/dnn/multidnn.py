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
        
    def write_summary (self, writer, epoch, feed_dict, verbose = True):
        for i in range (len (list (feed_dict.values ())[0])):
            feed_dict_ = {}
            for k, v in feed_dict.items ():
                feed_dict_ [k] = v [i]
            self.dnns [i].write_summary (writer, epoch, feed_dict_, verbose)
                    
    def measure_accuracy (self, preds, xs, ys):
        results = []
        for i in range (len (self.y_div) - 1):   
            dnn = self.dnns [i]
            results.append (dnn.measure_accuracy (preds [i], xs, self._get_segment (i, ys)))
        return np.array (results)
        
    def run (self, *ops, **kargs):
        ys = kargs.pop ("y")        
        results = []
        for i in range (len (self.y_div) - 1):
            dnn = self.dnns [i]
            kargs ["y"] = self._get_segment (i, ys)    
            results.append (dnn.run (*tuple ([getattr (dnn, op.attr) for op in ops]), **kargs))
        return np.array (results).transpose ()
        