import re
import sys
from rs4 import strutil
HAS_SKILLSET = True
try:
	import html5lib	
	import lxml.etree
	import lxml.html	
except ImportError:
	HAS_SKILLSET = False
import warnings
warnings.filterwarnings("ignore")

def remove_control_characters (html):
	def str_to_int(s, default, base=10):
		if int(s, base) < 0x10000:
			if strutil.PY_MAJOR_VERSION == 2:
				return unichr(int(s, base))
			else:	
				return chr(int(s, base))				
		return default

	html = re.sub(r"&#(\d+);?", lambda c: str_to_int(c.group(1), c.group(0)), html)
	html = re.sub(r"&#[xX]([0-9a-fA-F]+);?", lambda c: str_to_int(c.group(1), c.group(0), base=16), html)
	html = re.sub(r"[\x00-\x08\x0b\x0e-\x1f\x7f]", "", html)		
	return html
	
def remove_non_asc (html):	
	html = re.sub(br"&#(\d+);?", "", html)
	html = re.sub(br"&#[xX]([0-9a-fA-F]+);?", "", html)
	html = re.sub(br"[\x00-\x08\x80-\xff]", "", html)	
	return html
	
RX_CAHRSET = re.compile (br"[\s;]+charset\s*=\s*['\"]?([-a-z0-9]+)", re.M) #"
RX_META = re.compile (br"<meta\s+.+?>", re.I|re.M)

def get_charset (html):	
	encoding = None
	pos = 0	
	while 1:	
		match = RX_META.search (html, pos)
		if not match: break
		#print (match.group ())	
		charset = RX_CAHRSET.findall (match.group ().lower ())
		if charset:			
			encoding = charset [0].decode ("utf8")			
			#print (encoding)
			break
		pos = match.end ()		
	return encoding

def to_str (body, encoding = None):
	def try_generic_encoding (html):
		try:
			return html.decode ("utf8")
		except UnicodeDecodeError:	
			try:
				return html.decode ("iso8859-1")
			except UnicodeDecodeError:
				return remove_non_asc (html).decode ("utf8")
	
	if type (body) is bytes:	
		if encoding:
			try:
				body = body.decode (encoding)
			except (UnicodeDecodeError, LookupError):
				inline_encoding = get_charset (body)
				if inline_encoding and encoding != inline_encoding:				
					try:
						body = body.decode (inline_encoding)
					except (UnicodeDecodeError, LookupError):
						body = try_generic_encoding (body)			
				else:
					body = try_generic_encoding (body)
		else:
			body = try_generic_encoding (body)
	
	return remove_control_characters (body)
	
def html (html, baseurl, encoding = None):
	# html5lib rebuilds possibly mal-formed html	
	try:		
		if type (html) is str:
			return lxml.html.fromstring (lxml.etree.tostring (html5lib.parse (html, treebuilder="lxml")), baseurl)
		else:	
			return lxml.html.fromstring (lxml.etree.tostring (html5lib.parse (html, likely_encoding = encoding, treebuilder="lxml")), baseurl)
	except ValueError:
		return lxml.html.fromstring (lxml.etree.tostring (html5lib.parse (to_str (html, encoding), treebuilder="lxml")), baseurl)

def etree (html, encoding = None):
	try:
		return html5lib.parse (html, encoding = encoding, treebuilder="lxml")	
	except ValueError:	
		return html5lib.parse (to_str (html, encoding), treebuilder="lxml")	


if __name__ == "__main__":	
	from urllib.request import urlopen
	from contextlib import closing
	
	with closing(urlopen("http://www.drugandalcoholrehabhouston.com")) as f:
		build (f.read ())

