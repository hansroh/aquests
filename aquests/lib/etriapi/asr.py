from aquests.lib import siesta
import json
import base64
import librosa
from io import BytesIO

openApiURL = "http://aiopen.etri.re.kr:8000"
ACCESS_KEY = None
API = siesta.API (openApiURL)

def set_access_key (key):
    global ACCESS_KEY    
    ACCESS_KEY = key
    
# resampling to 16K
def resampling (audioFilePath):
    y, sr = librosa.load (audioFilePath, sr = 16000)
    output = BytesIO ()
    librosa.output.write_wav(output, y, 16000)
    return output.getvalue ()

def get_speech (audioFilePath, lang = "english"):
    audioContents = base64.b64encode (resampling (audioFilePath)).decode("utf8")
    requestJson = {
        "access_key": ACCESS_KEY,
        "argument": {"audio": audioContents, "language_code": lang},
        "request_id": "sns",
    }
    resp = API.WiseASR.Recognition.post (
        requestJson,
        {"Content-Type": "application/json; charset=UTF-8"}     
    )
    return resp
