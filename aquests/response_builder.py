from aquests.lib.attrdict import AttrDict

class HTTPResponse:
	def __init__ (self, handler):
		self.response = handler.response
		self.request = self.response.request
		self.meta = self.request.meta
		# compet with requests
		self.status_code = self.response.code
		self.status_msg = self.response.msg		
		
	def __getattr__ (self, name):
		return getattr (self.response, name)
	
	
class DBOResponse:
	def __init__ (self, description, expt_class, expt_str, data):
		self.description = description
		self.expt_class = expt_class
		self.expt_str = expt_str
		self.data = data
		self.code, self.msg = 200, "OK"
		
		if expt_class:
			self.code = 500
			self.msg = "%s %s" % (str (expt_class[1:-1], expt_str))
		
		if description:
			assert (len (description) == len (data [0]))		
			cols = [type (col) is tuple and col [0] or col.name for col in description]		
			d = []
			for row in data:
				i = 0
				drow = AttrDict ()
				for name in cols:
					drow [name] = row [i]
					i += 1
				d.append (drow)
			self.data = d
			
		else:
			if type (data) is dict:
				try:
					self.data = AttrDict ()
					for k, v in data.items ():
						self.data [k] = v
				except:
					self.data = data
			else:		
				self.data = data
		
		def read (self):
			return self.data
		
		