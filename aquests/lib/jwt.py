from base64 import b64decode, b64encode
from hmac import new as hmac
import json
import hashlib

def add_padding (s):
	paddings = 4 - (len (s) % 4)
	if paddings != 4:
		s += "=" * paddings
	return s	
			
def get_claim (secret_key, token):
	header, claim, sig = token.split (".")	
	jheader = json.loads (b64decode (add_padding (header)).decode ("utf8"))
	alg = jheader.get ("alg")
	if not alg or alg [:2] != "HS":
		raise TypeError ("Unknown Algorithm")
	hash_method = getattr (hashlib, "sha" + alg [2:])	
	mac = hmac (secret_key, None, hash_method)
	mac.update (("%s.%s" % (header, claim)).encode ("utf8"))
	if mac.digest() != b64decode (add_padding (sig)):
		raise ValueError ("Verificationn Failed")
	return json.loads (b64decode (add_padding (claim)).decode ("utf8"))
	
def gen_token (secret_key, claim, alg = "HS256"):
	header = b64encode (json.dumps ({"alg": alg, "typ": "JWT"}).encode ("utf8")).rstrip (b'=')
	claim = b64encode (json.dumps (claim).encode ("utf8")).rstrip (b'=')
	hash_method = getattr (hashlib, "sha" + alg [2:])	
	mac = hmac (secret_key, None, hash_method)
	mac.update (header + b"." + claim)	
	sig = b64encode (mac.digest()).rstrip (b'=')
	return (header + b"." + claim + b"." + sig).decode ("utf8")


if __name__ == "__main__":
	sk = b"8fa06210-e109-11e6-934f-001b216d6e71"
	token = gen_token (sk, {'user': 'Hans Roh', 'roles': ['user']}, "HS256")
	
	# eyJhbGciOiAiSFMyNTYiLCAidHlwIjogIkpXVCJ9.eyJyb2xlcyI6IFsidXNlciJdLCAidXNlciI6ICJIYW5zIFJvaCJ9.ls7R30APuI9QkeI0nVa0YOV3fBo2SlFg0ESzdyPzuv0
	print (token)
	print (get_claim (sk, token))
	
	"""
	import requests
	f = requests.get (
		"http://127.0.0.1:5000/lufex",
		headers ={"Authorization": "Bearer %s" % token}
	)
	print (f)
	"""