from rs4.attrdict import AttrDict
from rs4.cbutil import tuple_cb

class Request:
	reauth_count = 0
	retry_count = 0		
	def __init__ (self, dbtype, server, dbname, auth, method, params, callback = None, meta = {}):
		self.server = server
		self.dbname = dbname
		self.auth = auth
		self.method = method
		self.params = params		
		self.meta = meta
		self.dbtype = dbtype
		self.callback = callback
		
		self.expt = None		
		self.description = None
		self.__data = None
		self.__content = None		
		self.code, self.msg, self.version = 200, "OK", None		
	
	def set_callback (self, callback):
		self.callback = callback
	
	def raise_for_status (self):		
		if self.expt:
			raise self.expt
	reraise = raise_for_status
	
	def get_error_as_string (self):
		if self.expt:
			return "%s %s" % (self.expt.__class__, str (self.expt))
		return ""
	
	def __nonzero__ (self):
		return self.data and True or False
			
	@property
	def status_code (self):		
		return self.code
	
	@property
	def reason (self):
		return self.msg
	
	def handle_callback (self):
		tuple_cb (self, self.callback)
					
	def handle_result (self, description, expt, data):
		self.expt = expt
		if expt:
			self.code, self.msg = 500, "Database Error"			
		self.description = description
		self.__content = data
		self.handle_callback ()
	
	@property
	def content (self):
		return self.__content
		
	@property
	def data (self):
		if self.__data:
			return self.__data
			
		if not self.__content:
			return self.__content	
			
		data = self.__content
		if self.description:
			assert (len (self.description) == len (data [0]))		
			cols = [type (col) is tuple and col [0] or col.name for col in self.description]
			d = []
			for row in data:
				i = 0
				drow = AttrDict ()
				for name in cols:
					drow [name] = row [i]
					i += 1
				d.append (drow)
			self.__data = d
		
		else:
			if type (data) is dict:
				self.__data = AttrDict ()
				for k, v in data.items ():
					self.__data [k] = v				
			else:		
				self.__data = data
		
		return self.__data
		
		