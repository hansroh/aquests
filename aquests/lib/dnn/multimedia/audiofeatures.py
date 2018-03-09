import numpy as np
import sys
import os
import glob
import wave
import multiprocessing
from functools import partial
from scipy.fftpack import fft
from scipy.io import wavfile
from scipy import signal
from tqdm import tqdm
import librosa
import librosa.util
import random 
from scipy.stats import skew, kurtosis

SAMPLE_RATE = 22050
TIME_LAP = 0.2

def _save (data, wavfile, target_path):
    savedir = os.path.join (target_path, os.path.basename (os.path.dirname (os.path.dirname (wavfile))))
    if not os.path.isdir (savedir):
        os.mkdir (savedir)
    target_file = os.path.join(savedir, "%s.npy" % os.path.basename (wavfile))
    np.save(target_file, data)

def _featuring (data):
    deriv1 = skew (data, axis = 1)
    deriv2 = kurtosis (data, axis = 1)    
    features = np.array ([
        np.mean (data, axis = 1),
        np.max (data, axis = 1),
        np.min (data, axis = 1),
        np.median (data, axis = 1),
        np.var (data, axis = 1),    
        deriv1,
        deriv2,
        np.mean ([deriv1, deriv2], axis = 0),
        np.var ([deriv1, deriv2], axis = 0),
    ])
    # normalize
    features = features / np.max (np.abs (features))
    return features


def load (wavfile, sample_rate = SAMPLE_RATE, time_lap = 0.2, due_limit = (1, 5), time_stretch = False, pitch_shift = False, random_laps = False, add_noise = False):
    y, sr = librosa.load (wavfile, sample_rate, True)
    if add_noise:
        noise = np.random.normal (0, 1, y.shape)
        gain = max (0.02, random.random () * 0.1)        
        y = y + gain * noise

    if time_stretch:
        rate = 1.0
        if random.randrange (2):
            rate += max (0.05, random.random () / 4.)
        else:
            rate -= max (0.05, random.random () / 4.)    
        y = librosa.effects.time_stretch (y, rate)
        #print ("time_stretch", rate)
    
    if pitch_shift:
        n_step = random.choice ([-4,-3,-2,-1,1,2,3,4])
        y = librosa.effects.pitch_shift (y, sr, n_step)
        #print ("pitch_shift", n_step)
    
    if random_laps:
       time_lap += random.random () / 3
    
    removable = int (sample_rate * time_lap)
    y = y [removable:len (y) - removable]
    # Trim the beginning and ending silence
    y, index = librosa.effects.trim (y)    
    duration = librosa.get_duration(y)        
    if duration < due_limit [0] or duration > due_limit [1]:
        return None, sr    
    # normalize
    y = y / np.max (np.abs (y))
    
    return y, sr
 
def generate (y, sample_rate = SAMPLE_RATE, use_mel = True, use_stft = False):
    feature_stack = []
    numfeat = 0
    
    # stft ----------------------------------------------------
    stft = librosa.stft (y, n_fft=2048, win_length=1200, hop_length=256)
    if use_mel:
        # mel specrogram ------------------------------------------
        mel = librosa.feature.melspectrogram(S = stft, n_mels=80)
        mel = np.log(np.abs(mel) + 1e-8)
        feature_stack.extend (_featuring (mel))
        numfeat += 80 * 9
    
    if use_stft:    
        stft = np.log(np.abs(stft) + 1e-8)
        feature_stack.extend (_featuring (stft))
        numfeat += 1025 * 9    
        
    # mfcc -----------------------------------
    vec = librosa.feature.mfcc(S = stft, sr = sample_rate, n_mfcc=20, n_fft=512, hop_length = 256)
    feature_stack.extend (_featuring (vec))
    
    # chroma_cqt -----------------------------------
    cqt = librosa.feature.chroma_cqt (y=y, sr = sample_rate, n_chroma = 12, hop_length = 256)
    cqt = np.log(np.abs(cqt) + 1e-8) # to dB lebel 
    feature_stack.extend (_featuring (cqt))
    
    # chroma_cens -----------------------------------
    cens = librosa.feature.chroma_cens (y=y, sr = sample_rate, n_chroma = 12, hop_length = 256)
    cens = np.log(np.abs(cens) + 1e-8)
    feature_stack.extend (_featuring (cens))    
    numfeat += 44 * 9
    
    # zero_crossing_rate -----------------------------------
    vec = librosa.feature.zero_crossing_rate (y = y)
    feature_stack.extend (_featuring (vec))
    numfeat += vec.shape [0] * 9
    
    # tonnetz -----------------------------------
    vec = librosa.feature.tonnetz (y=y, sr = sample_rate)
    feature_stack.extend (_featuring (vec))
    numfeat += vec.shape [0] * 9

    vec = librosa.feature.rmse (S = stft, hop_length = 256)
    feature_stack.extend (_featuring (vec))
    numfeat += vec.shape [0] * 9
    
   # spectral_series -----------------------------------
    for ff in ("spectral_contrast", "poly_features", "chroma_stft", "spectral_centroid", "spectral_bandwidth", "spectral_rolloff"):
        vec = getattr (librosa.feature, ff) (y = y, sr = sample_rate, hop_length = 256)
        feature_stack.extend (_featuring (vec))
        numfeat += vec.shape [0] * 9
    
    features = np.hstack (tuple (feature_stack))
    assert features.shape == (numfeat,)
    return features

def make (wavfile, sample_rate = SAMPLE_RATE, time_lap = 0.2, due_limit = (1, 5), use_mel = True, use_stft = False, time_stretch = False, pitch_shift = False, random_laps = False, add_noise = False):
    y, sr = load (wavfile, sample_rate, time_lap, due_limit, time_stretch, pitch_shift, random_laps, add_noise)
    if y is None:
        return
    return generate (y, sr, use_mel, use_stft)

def save (wavfile, target_path, sample_rate = SAMPLE_RATE, time_lap = 0.2, due_limit = (1, 5), use_mel = False, use_stft = False):
    features = make (wavfile, sample_rate, time_lap, due_limit, use_mel, use_stft)
    if features is None:
        return False
    _save (features, wavfile, target_path)
    return True

def puff (wavfile, target_path, sample_rate = SAMPLE_RATE, time_lap = 0.2, due_limit = (1, 5), use_mel = False, use_stft = False, n_gen = 4):    
    _saved = save (wavfile, target_path, sample_rate, time_lap, due_limit, use_mel = use_mel, use_stft = use_stft)
    if not _saved:
         return 0
     
    n = 1
    for i in range (n_gen * 2):
        params = (random.randrange (2), random.randrange (2), random.randrange (2), random.randrange (2))
        if sum (params) == 0:
            continue
        features = make (wavfile, sample_rate, time_lap, due_limit, use_mel = use_mel, use_stft = use_stft, time_stretch = params [0], pitch_shift = params [1], random_laps = params [2], add_noise = params [3])
        if features is None:
            continue        
        _save (features, "{}.{}".format (wavfile, n), target_path)
        n += 1
        if n == n_gen:
            break
    
    return n    


if __name__ == '__main__':    
    y, sr = load  (os.path.join (os.path.dirname (__file__), "test.wav"))
    print (y.shape)   
    print (librosa.get_duration(y [:sr])) 
    stft = librosa.stft (y [:sr], n_fft=2048, win_length=1200, hop_length=256)
    print (stft.shape)
    ft = generate (y, sr)
    print (ft.shape)
    
    