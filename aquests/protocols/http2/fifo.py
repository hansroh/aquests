from ...lib.athreads.fifo import await_ts_fifo
			
class http2_producer_fifo (await_ts_fifo):
	# Asyncore await_fifo replacement
	# For resorting, removeing by http2 priority, cacnel and reset features
	# Also can handle producers has 'ready' method
		
	def remove_from (self, stream_id, lst):
		deleted = 0
		for i in range (len (lst)):
			try:
				producer_stream_id = lst [0].stream_id
			except AttributeError:
				pass
			else:
				if producer_stream_id	== stream_id:
					lst.popleft ()
					deleted += 1
			lst.rotate (1)
		return deleted
							
	def remove (self, stream_id):
		with self._lock:
			if self.l:
				self.remove_from (stream_id, self.l)
			if self.r:
				self.remove_from (stream_id, self.r)
			
	def insert (self, index, item):
		if item is None:
			with self._lock:
				self.has_None = True
			return
		
		with self._lock:	
			if self.has_None:
				return # deny adding	
		
		if hasattr (item, 'ready'):
			with self._lock:
				return self.r.append (item)
		
		# insert by priority
		try:
			w1 = item.weight
			d1 = item.depends_on
		except AttributeError:
			with self._lock:
				return self.insert_into (self.l, index, item)
		
		index = 0
		inserted = False
		with self._lock:
			for each in self.l:
				try:
					w2 = each.weight
					d2 = each.depends_on
				except AttributeError:
					pass
				else:
					if d2 >= d1 and w2 < w1:
						self.insert_into (self.l, index, item)
						inserted = True
						break
				index += 1
				
			if not inserted:
				self.l.append (item)
				
