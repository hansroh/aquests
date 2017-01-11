from aquests.lib.attrdict import AttrDict

class Request:
	def __init__ (self, dbtype, method, params, callback = None, meta = {}):
		self.method = method
		self.params = params
		self.meta = meta
		self.dbtype = dbtype
		self.callback = callback
		
		self.description = None
		self.data = None
		self.expt_class = None
		self.expt_str = None
		
		self.code, self.msg = 200, "OK"
		
	def handle_result (self, description, expt_class, expt_str, data):
		self.expt_class, self.expt_str = expt_class, expt_str
		if expt_class:
			self.code, self.msg = 500, "Error"

		if not data:
			self.data = data
			return self.callback (self)			
		
		self.description = description
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
		
		self.callback (self)
		
		