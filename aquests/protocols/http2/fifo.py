from ...lib.athreads.fifo import await_ts_fifo

class http2_producer_fifo (await_ts_fifo):
	# Asyncore await_fifo replacement
	# For resorting, removeing by http2 priority, cacnel and reset features
	# Also can handle producers has 'ready' method
							
	def remove (self, stream_id):
		with self._lock:
			if self.l:
				for i in range (len (lst)):
					try:
						producer_stream_id = lst [0].stream_id
					except AttributeError:
						pass
					else:
						if producer_stream_id	== stream_id:
							lst.popleft ()							
					lst.rotate (1)				
				
	def insert_into (self, lst, index, item):		
		if index == 0:
			lst.appendleft (item)
		elif index == -1:
			lst.append (item)	
		else:
			r = len (self.l) - index
			lst.rotate (r)
			lst.append (item)
			lst.rotate (index + 1)
					
	def insert (self, index, item):
		if item is None:
			with self._lock:
				self.has_None = True
			return
		
		with self._lock:
			if self.has_None and index != 0:
				return # deny adding	
		
		if hasattr (item, "ready") and not item.ready:
			with self._lock:	
				return self.l.append (item)
					
		if index == 0:
			with self._lock:
				return self.l.appendleft (item)
		
		with self._lock:
			if not self.l:
				return self.l.append (item)
		
		# insert by priority
		try:
			w1 = item.weight
			d1 = item.depends_on
		except AttributeError:
			with self._lock:
				return self.l.append (item)
		
		with self._lock:				
			i = 0
			for each in self.l:
				try:
					w2 = each.weight
					d2 = each.depends_on
				except AttributeError:
					pass
				else:
					if d1 <= d2 and w2 < w1:
						self.insert_into (self.l, i, item)
						return			
				i += 1
			self.l.append (item)
				
