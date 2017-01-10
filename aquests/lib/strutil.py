import sys
PY_MAJOR_VERSION = sys.version_info.major

def is_str_like (thing):
	if PY_MAJOR_VERSION == 2 and type (thing) is unicode:
		return True
	return type (thing) is str

def is_encodable (thing):
	if PY_MAJOR_VERSION == 2:
		if type (thing) is unicode: 
			return True
	return type (thing) is str

def is_decodable (thing):
	if PY_MAJOR_VERSION == 2:
		if type (thing) is str:
			return True
	return type (thing) is bytes

