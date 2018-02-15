import os
import wave
import sys
from google.cloud import speech
from google.cloud import translate

CREDENTIAL = 'credential.json'
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.path.join (os.path.dirname (__file__), CREDENTIAL)

translate_client = translate.Client()
speech_client = speech.SpeechClient ()

class OverSizeError (Exception):
    pass


def get_translate (text, lang = 'en'):
    translation = translate_client.translate(text, target_language=target)
    # translation = {'translatedText': 'Hello', 'detectedSourceLanguage': 'ko', 'input': '안녕'}
    return translation['translatedText']

def get_speech (audio_clip_path, lang = 'en-US'):
    if os.path.getsize(audio_clip_path) > 100000000:
        raise OverSizeError
        
    with wave.open(audio_clip_path,'rb') as temp:
        frequency = temp.getframerate()
    with open(audio_clip_path,'rb') as audio_file:
        content = audio_file.read()

    audio = speech.types.RecognitionAudio(content = content)
    config = speech.types.RecognitionConfig (
        encoding = speech.enums.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz = frequency,
        language_code = lang
    )
    response=speech_client.recognize(config, audio)
    
    if not response.results:
        return ''             
    for result in response.results:
        # Applying Google cloud speech api and recording its result on the database.
        alternatives =result.alternatives
        alternative = alternatives[0].transcript
        if alternative:
            return alternative    
    return ''

    
if __name__ == '__main__':
    #print (get_translate ("안녕"))
    print (get_speech ("test-music.wav"))
    print (get_speech ("test-voice.wav"))
    
    