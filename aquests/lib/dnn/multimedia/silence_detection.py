# Default libraries
import os

try:
    import numpy as np
    import librosa    # Library for finding silence interval.
except ImportError:
    print("Please install numpy and librosa packages.")
    
def read(filename):
    # Read file and then return wave sequence and its frequency.
    try:
        wave, fq = librosa.load(filename)
    except FileNotFoundError:
        print("File {} is not found.".format(filename))
        wave, fq = None, None
    return (wave, fq)

def detect(wave, threshold=20):
    # Find the non_silence windows.
    # Return value is a list of Boolean data.
    # If the energy of ith interval of wave file is less then threshold then
    # it returns False at the ith component and vice versa. 
    return librosa.effects._signal_to_frame_nonsilent(wave, top_db=threshold)

def false_count(detection):
    # Input is the list of Boolean data.
    # It returns starting window of silent interval and how long it lasts.
    # For example if in put is [T T T F F F F T T F F T T F], then it returns
    # [[3,4],[9,2],[13,1]]
    i = 0
    detect_list = []
    while i < len(detection):
        if detection[i] == True:
            i += 1
        else:
            j = 0
            while (i + j) < len(detection) and detection[i + j] == False:
                j += 1
            detect_list.append((i, j))
            i += j
    return detect_list

def silence_index(wave, threshold=20, min_silence_frames=50):
    # Input is a wave file and threshold and nim_silence_frames.
    # Using false_count, we get the the silent information of wave file.
    # It returns the silent interval larger than min_silence_frames.
    index = []
    detect_list = false_count(detect(wave, threshold))
    for (i, j) in detect_list:
        if j >= min_silence_frames:
            index.append((i * 512, (i+j-1)*512+2048-1))
    return index

def clip_cut(wave, threshold=20, min_silence_frames=50):
    # Using the result of silence_index, we can find the non_silence interval.
    index = []
    wave_len = len(wave)//512*512
    silence_list=silence_index(wave, threshold, min_silence_frames)
    if not silence_list:
        return index 
    if silence_list[0][0] > 0:
        index.append((0,silence_list[0][0]-1))
    for k in range(len(silence_list)-1):
        index.append((silence_list[k][1]+1,silence_list[k+1][0]-1))
    if silence_list[-1][1] < wave_len-1:
        index.append((silence_list[-1][1]+1, wave_len-1))
    return index

def frame_to_time(frame_stamp, frequency, wave_len, time_laps=0.2):
    # It returns lists of time_interval from frame_interval.
    # We will add time_laps at each starting and end point of time_interval.
    stamp = []
    for k in range(len(frame_stamp)):
        if (k == 0) and (frame_stamp[k][0]/frequency < time_laps):
            stamp.append((0, frame_stamp[k][1]/frequency+time_laps))
        elif (k == len(frame_stamp) - 1) and (frame_stamp[k][0]/frequency + time_laps > wave_len/frequency):
            stamp.append((frame_stamp[k][0]/frequency-time_laps, wave_len/frequency))
        else:
            stamp.append((frame_stamp[k][0]/frequency-time_laps, frame_stamp[k][1]/frequency+time_laps))
    return stamp
