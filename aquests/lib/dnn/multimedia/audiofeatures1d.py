from . import audiofeatures as af
import os
import numpy as np
import random

def make (wavfile, sample_rate = af.SAMPLE_RATE, time_lap = 0.2, due_limit = (1, 5), use_mel = True, use_stft = False, time_stretch = False, pitch_shift = False, random_laps = False, add_noise = False, seqs = 12):
    y, sr = af.load (wavfile, sample_rate, time_lap, due_limit)
    if y is None:
        return    
    seg = int (len (y) / seqs) + 1
    features = []
    for i in range (0, len (y), seg):
        ft = af.generate (y [i:i + seg], sr, use_mel, use_stft)
        features.append (ft)
    assert len (features) == seqs   
    return np.array (features)    

def save (wavfile, target_path, sample_rate = af.SAMPLE_RATE, time_lap = 0.2, due_limit = (1, 5), use_mel = False, use_stft = False, seqs = 12):
    features = make (wavfile, sample_rate, time_lap, due_limit, use_mel, use_stft, seqs)
    if features is None:
        return False
    af._save (features, wavfile, target_path)
    return True

def puff (wavfile, target_path, sample_rate = af.SAMPLE_RATE, time_lap = 0.2, due_limit = (1, 5), use_mel = False, use_stft = False, n_gen = 4, seqs = 12):    
    if not save (wavfile, target_path, sample_rate, time_lap, due_limit, use_mel = use_mel, use_stft = use_stft, seqs = seqs):
        return 0
    
    n = 1
    for i in range (n_gen * 2):
        params = (random.randrange (2), random.randrange (2), random.randrange (2), random.randrange (2))
        if sum (params) == 0:
            continue
        features = make (wavfile, sample_rate, time_lap, due_limit, use_mel = use_mel, use_stft = use_stft, time_stretch = params [0], pitch_shift = params [1], random_laps = params [2], add_noise = params [3], seqs = seqs)
        if features is None:
            continue        
        af._save (features, "{}.{}".format (wavfile, n), target_path)
        n += 1
        if n == n_gen:
            break
    return n    

        
if __name__ == '__main__':    
    ft = make  (os.path.join (os.path.dirname (__file__), "test.wav"), seqs = 12)
    print (ft.shape)
    print (ft)
    