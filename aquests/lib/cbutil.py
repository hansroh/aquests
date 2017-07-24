
def tuple_cb (default, callback):	
	if not callback:
		return
	
	if type (callback) is not tuple:
		return callback (default)
	
	lc = len (callback)
	if lc == 2:
		arg = callback [1]
		if type (arg) is dict:
			args, karg = (), arg
		else:
			args, karg = arg, {}
	elif lc == 3:
		args, karg = callback [1:]
	else:
		args, karg = (), {}
		
	callback [0] (default, *args, **karg)
	
