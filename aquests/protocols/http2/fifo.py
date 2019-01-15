from ...athreads.fifo import await_fifo, await_ts_fifo

class http2_producer_fifo (await_fifo):
	# asyncore await_fifo replacement
	# for resorting, removeing by http2 priority, cacnel and reset features
	# also can handle producers has 'ready' method
	# this class can be used only at single thread environment

	def remove (self, stream_id):
		if self.l:
			for i in range (len (self.l)):
				try:
					producer_stream_id = self.l [0].stream_id
				except AttributeError:
					pass
				else:
					if producer_stream_id	== stream_id:
						self.l.popleft ()							
				self.l.rotate (1)				
			
	def _insert_into (self, index, item):		
		if index == 0:
			self.l.appendleft (item)
		elif index == -1:
			self.l.append (item)	
		else:
			r = len (self.l) - index
			self.l.rotate (r)
			self.l.append (item)
			self.l.rotate (index + 1)
					
	def insert (self, index, item):
		if item is None:
			self.has_None = True
			return
		
		if self.has_None and index != 0:
			return # deny adding			
		if not self.l:
			return self.l.append (item)
				
		if index == 0:
			try:
				readyfunc = getattr (item, "ready")
			except AttributeError:
				pass
			else:		
				if not readyfunc ():
					return self.l.append (item)
						
			return self.l.appendleft (item)
		
		# insert by priority
		try:
			d1 = item.depends_on
			w1 = item.weight			
		except AttributeError:
			return self.l.append (item)
		
		if d1 == 0:
			return self.l.append (item)
		
		i = 0
		found_parent = 0			
		for each in self.l:
			try:
				s2 = each.stream_id					
			except AttributeError:
				pass
			else:
				if found_parent:
					d2 = each.depends_on
					w2 = each.weight					
					if d1 == d2 and w2 < w1:
						return self._insert_into (i, item)
				elif d1 == s2:
					found_parent = 1
			i += 1
			
		self.l.append (item)


class http2_producer_ts_fifo (http2_producer_fifo, await_ts_fifo):	
	# multin threads safe version	
	
	def remove (self, stream_id):
		with self._lock:			
			http2_producer_fifo.remove (self, stream_id)
					
	def insert (self, index, item):		
		with self._lock:			
			http2_producer_fifo.insert (self, index, item)
	