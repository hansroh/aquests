import numpy as np
import math
from sklearn.utils.extmath import softmax as softmax_

def softmax (x):
    return softmax_ ([x])[0].tolist ()

def sigmoid (x):   
    return [1 / (1 + np.exp(-e)) for e in x]

