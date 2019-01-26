try:
	from urllib.parse import urlparse, quote_plus	
except ImportError:
	from urlparse import urlparse
	from urllib import quote_plus	
from rs4 import attrdict

def normheader (headers):
    nheader = attrdict.CaseInsensitiveDict ({})
    if not headers:
        return nheader
    for k, v in type (headers) is dict and headers.items () or headers:
        nheader [k] = v
    return nheader

def set_content_types (headers, data, defaults):    
    no_accept_header = True
    no_content_type_header = True        
    for k, v in headers.items ():
        if k.lower () == "accept":
            no_accept_header = False
        elif k.lower () == "content-type":
            no_content_type_header = False
    
    if data and no_content_type_header:
        headers ['Content-Type'] = defaults [0]        
    if no_accept_header:
        headers ['Accept'] = defaults [1]

def dictencode (data):
	cdata = []
	for k, v in list (data.items ()):
		cdata.append ("%s=%s" % (k, quote_plus (v)))
	return "&".join (cdata)
	
def strencode (data):
	if not data: return data

	if data.find ('%') != -1 or (data.find ('+') != -1 and data.find (' ') == -1):
		return data
	
	d = []
	for x in data.split('&'):
		try: k, v = x.split('=', 1)
		except ValueError: d.append ((k, None))
		else:
			v = quote_plus (v)
			d.append ((k, v))
	d2 = []
	for k, v in d:
		if v == None:
			d2.append (k)
		else:
			d2.append ('%s=%s' % (k, v))

	return '&'.join (d2)


def strdecode (data, value_quote = 0):
	if not data: return []
	do_quote = 1
	if data.find('%') > -1 or data.find('+') > -1:
		do_quote = 0
	if not value_quote:
		do_quote = 0

	d = []
	for x in data.split(';'):
		try: k, v = x.split('=', 1)
		except ValueError: pass
		else:
			if do_quote:
				v = quote_plus (v.strip())
			d.append((k.strip(), v.strip()))
	return d