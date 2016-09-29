import html5lib
import re
import lxml.etree
import lxml.html
import lxml.html.clean
import re
import traceback
from copy import deepcopy
import sys
from skitai.lib import strutil
from cssselect import GenericTranslator, SelectorError

TABSSPACE = re.compile(r'[\s\t]+')
SIMPLIFIED_CHILD_CSS = re.compile (r"\s*([<\[])(\-?)([0-9]+)[>\]]")

def innerTrim(value):
	if strutil.is_str_like (value):
		# remove tab and white space
		value = re.sub(TABSSPACE, ' ', value)
		value = ''.join(value.splitlines())
		return value.strip()
	return ''


def filter_by_text (element, text):
	if text [0] == "=":
		if text [1:] == "":
			return [each for each in element if not Parser.get_text (each)]
		return [each for each in element if each.text and each.text.strip () == text [1:]]
	else:
		op, text = text [:2], text [2:].strip ()
		if op == "/=":
			rx = eval ("re.compile ('%s')" % text)
			return [each for each in element if each.text and rx.search (each.text.strip ())]
		elif op == "!=":
			return [each for each in element if each.text and each.text.strip () != text]
		elif op == "*=":
			return [each for each in element if each.text and each.text.find (text) != -1]
		elif op == "^=":	
			return [each for each in element if each.text and each.text.strip ().startswith (text)]
		elif op == "$=":	
			return [each for each in element if each.text and each.text.strip ().endswith (text)]
		elif op == "~=":	
			return [each for each in element if each.text and text in each.text.split ()]		
		else:
			raise AssertionError ("unknown operator %s" % op)	
				
class Parser:
	@classmethod
	def from_string (cls, html):
		if strutil.is_str_like (html) and html.startswith('<?'):
			html = re.sub(r'^\<\?.*?\?\>', '', html, flags=re.DOTALL)				
		try:
			return lxml.html.fromstring(html)			
		except Exception:
			traceback.print_exc()
			return None
		
	@classmethod
	def to_string (cls, node, encoding = "utf8", method='html', doctype = "<!DOCTYPE html>"):
		return lxml.html.tostring(node, encoding)
	
	@classmethod
	def by_xpath (cls, node, expression):
		items = node.xpath(expression)
		return items
	
	@classmethod
	def by_xpath_re (cls, node, expression):
		regexp_namespace = "http://exslt.org/regular-expressions"
		items = node.xpath(expression, namespaces={'re': regexp_namespace})
		return items
		
	@classmethod
	def by_css (cls, node, selector):
		def repl (m):
			index = int (m.group (3))
			if m.group (2) == "-":
				index -= 1
				if m.group (1) == "<":
					ss = ":nth-child(%d)"
				else:	
					ss = ":nth-last-of-type(%d)"
			else:
				index += 1
				if m.group (1) == "<":
					ss = ":nth-last-child(%d)"				
				else:	
					ss = ":nth-of-type(%d)"			
			return ss % index
		
		selector = SIMPLIFIED_CHILD_CSS.sub (repl, selector)
		return cls.by_xpath (node, GenericTranslator().css_to_xpath(selector))
		#return node.cssselect(selector)
	
	@classmethod
	def by_id (cls, node, idd):
		selector = '//*[@id="%s"]' % idd
		elems = node.xpath(selector)
		if elems:
			return elems[0]
		return None

	@classmethod
	def by_tag_attr (cls, node, tag=None, attr=None, value=None, childs=False):
		NS = "http://exslt.org/regular-expressions"
		# selector = tag or '*'
		selector = 'descendant-or-self::%s' % (tag or '*')
		if attr and value:
			selector = '%s[re:test(@%s, "%s", "i")]' % (selector, attr, value)		
		elems = node.xpath(selector, namespaces={"re": NS})
		# remove the root node
		# if we have a selection tag
		if node in elems and (tag or childs):
			elems.remove(node)
		return elems
	
	@classmethod
	def by_tag (cls, node, tag):
		return cls.by_tags (node, [tag])
	
	@classmethod
	def by_tags (cls, node, tags):
		selector = ','.join(tags)
		elems = cls.by_css (node, selector)
		# remove the root node
		# if we have a selection tag
		if node in elems:
			elems.remove(node)
		return elems
	
	@classmethod
	def by_lt (cls, node, text):
		text = text.strip ()
		return [a for a in cls.by_tag (node, "a") if a.get_text () == text]			
	
	@classmethod
	def by_plt (cls, node, text):
		text = text.strip ()
		return [a for a in cls.by_tag (node, "a") if a.get_text ().find (text) != -1]
	
	@classmethod
	def by_csstext (cls, node, text):
		css, text = text.split (":text", 1)
		css = css.strip ()
		text = text.strip ()
		element = cls.by_css (node, css)
		return filter_by_text (element, text)
	
	@classmethod
	def by_tint (cls, node, text):
		tag, text = text.split ("=", 1)
		text = "=" + text.strip ()
		tag = tag.strip ()
		if not tag [-1].isalpha ():
			text = tag [-1] + text
			tag = tag [:-1]
		text = text.strip ()
		element = cls.by_tag (node, tag)
		return filter_by_text (element, text)
								
	@classmethod
	def prev_siblings (cls, node):
		nodes = []
		for c, n in enumerate (node.itersiblings(preceding=True)):
			nodes.append(n)
		return nodes
		
	@classmethod
	def prev_sibling (cls, node):
		nodes = []
		for c, n in enumerate (node.itersiblings(preceding=True)):
			nodes.append(n)
			if c == 0:
				break
		return nodes[0] if nodes else None
	
	@classmethod
	def next_siblings (cls, node):
		nodes = []
		for c, n in enumerate (node.itersiblings(preceding=False)):
			nodes.append(n)
		return nodes
		
	@classmethod
	def next_sibling (cls, node):
		nodes = []
		for c, n in enumerate (node.itersiblings(preceding=False)):
			nodes.append(n)
			if c == 0:
				break
		return nodes[0] if nodes else None
	
	@classmethod
	def get_siblings (cls, node):
		return cls.prev_siblings (node) + cls.next_siblings (node)
		
	@classmethod
	def new (self, tag):			
		return lxml.etree.Element(tag)
		
	@classmethod
	def get_attr (cls, node, attr=None):
		if attr:
			return node.attrib.get(attr, None)
		return node.attrib
	
	@classmethod
	def has_attr (cls, node, attr = None):		
		if attr:
			return attr in node.attrib
		return len (node.attrib) != 0
		
	@classmethod
	def del_attr (cls, node, attr=None):
		if attr:
			_attr = node.attrib.get(attr, None)
			if _attr:
				del node.attrib[attr]

	@classmethod
	def set_attr (cls, node, attr=None, value=None):
		if attr and value:
			node.set(attr, value)
					
	@classmethod
	def append_child (cls, node, child):
		node.append(child)
	
	@classmethod
	def insert_child (cls, index, node, child):
		node.insert (index, child)
		
	@classmethod
	def child_nodes (cls, node):
		return list(node)

	@classmethod
	def child_nodes_with_text (cls, node):
		root = node
		# create the first text node
		# if we have some text in the node
		if root.text:
			t = lxml.html.HtmlElement()
			t.text = root.text
			t.tag = 'text'
			root.text = None
			root.insert(0, t)
		# loop childs
		for c, n in enumerate(list(root)):
			idx = root.index(n)
			# don't process texts nodes
			if n.tag == 'text':
				continue
			# create a text node for tail
			if n.tail:
				t = cls.create_element(tag='text', text=n.tail, tail=None)
				root.insert(idx + 1, t)
		return list(root)

	@classmethod
	def get_children (cls, node):
		return node.getchildren()
	
	@classmethod
	def get_parent (cls, node):
		return node.getparent()
		
	@classmethod
	def get_text (cls, node):
		txts = [i for i in node.itertext()]		
		return innerTrim(u' '.join(txts).strip())
	
	@classmethod
	def get_texts (cls, node, trim = True):
		return cls.get_text_list (node, trim)
	
	@classmethod
	def get_text_list (cls, node, trim = True):
		if trim:
			return [i.strip () for i in node.itertext()]
		else:	
			return [i for i in node.itertext()]
	
	@classmethod
	def iter_text (cls, node):
		def collect (node, container):
			children = cls.get_children (node)
			if not children:
				return
				
			for child in children:
				if child.tag not in (
					"head", "meta", "link", "input", "hr", "br", "img", 
					"table", "tr", "thead", "tbody", "ol", "ul", "dl"
				):
					text = child.text
					if text is not None:
						text = text.strip ()
					else:
						text = ""
					container.append (text)
				collect (child, container)

		container = []
		collect (node, container)
		return container

	@classmethod
	def is_text_node (cls, node):
		return True if node.tag == 'text' else False
	
	@classmethod
	def get_tag (cls, node):
		return node.tag
	
	@classmethod
	def replace_tag (cls, node, tag):
		node.tag = tag

	@classmethod
	def strip_tags (cls, node, *tags):
		lxml.etree.strip_tags(node, *tags)
			
	@classmethod
	def drop_node (cls, node):
		try: 
			node.drop_tag ()
		except AttributeError:
			node.getparent ().remove (node)
	
	@classmethod
	def drop_tree (cls, node):
		def recursive (node):
			for child in node.getchildren ():
				if child.getchildren ():
					recursive (child)
				else:
					node.remove (child)
										
		try: 
			node.drop_tree ()
		except AttributeError:
			recursive (node)
			node.getparent ().remove (node)
	
	@classmethod
	def create_element (cls, tag='p', text=None, tail=None):
		t = lxml.html.HtmlElement()
		t.tag = tag
		t.text = text
		t.tail = tail
		return t

	@classmethod
	def get_comments (cls, node):
		return node.xpath('//comment()')
	
	@classmethod
	def remove_comments (cls, node):
		for item in cls.get_comments (node):
			try:
				item.drop_tree ()
			except AssertionError: # out of root node
				pass
				
	@classmethod
	def text_to_para (cls, text):
		return cls.create_element ('p', text)
	
	@classmethod
	def outer_html (cls, node):
		e0 = node
		if e0.tail:
			e0 = deepcopy(e0)
			e0.tail = None
		return cls.to_string(e0)
			
	@classmethod
	def clean_html (cls, node):
		article_cleaner = lxml.html.clean.Cleaner()
		article_cleaner.javascript = True
		article_cleaner.style = True
		article_cleaner.allow_tags = [
			'a', 'span', 'p', 'br', 'strong', 'b',
			'em', 'i', 'tt', 'code', 'pre', 'blockquote', 'img', 'h1',
			'h2', 'h3', 'h4', 'h5', 'h6']
		article_cleaner.remove_unknown_tags = False
		return article_cleaner.clean_html (node)
	
	@classmethod
	def get_param (cls, node, attr, name):
		name = name.lower ()
		params = cls.get_attr (node, attr)
		for param in params.split (";"):
			param = param.strip ()
			if not param.lower ().startswith (name):
				continue
			
			val = param [len (name):].strip ()
			if not val: return ""
			if val [0] == "=":
				val = val [1:].strip ()
				if not val: return ""
			if val [0] in "\"'":
				return val [1:-1]
			return val		
		
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
		return lxml.html.fromstring (lxml.etree.tostring (html5lib.parse (html, encoding = encoding, treebuilder="lxml")), baseurl)
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

