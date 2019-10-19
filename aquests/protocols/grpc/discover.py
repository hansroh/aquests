import sys
cache = {}
ocache = {}
all = []

try:
	from google.protobuf import descriptor_pb2

except ImportError:
	from ...uninstalled import Uninstalled
	find_object = discover = Uninstalled ('protobuf')

else:
	def discover ():
		global cache
		cache = {}
		for k, v in sys.modules.items ():
			if k.endswith ("_pb2") and not k.startswith ("google."):
				desriptor = v.DESCRIPTOR
				proto = descriptor_pb2.FileDescriptorProto.FromString(desriptor.serialized_pb)
				for service in proto.service:
					for method in service.method:
						cache ["%s.%s/%s" % (desriptor.package, service.name, method.name)] = (
							v,
							(method.input_type.split (".")[-1], method.client_streaming),
							(method.output_type.split (".")[-1], method.server_streaming),
							method.options
						)
				all.append (v)
	discover ()

	def find_object (module, name_stream):
		global all, ocache

		name, isstream = name_stream
		if name in ocache:
			return ocache [name]

		res = None
		if hasattr (module, name):
			res = getattr (module, name), isstream
		else:
			for each in all:
				if hasattr (each, name):
					res = getattr (each, name), isstream
					break

		if res:
			ocache [name] = res

		return res

def find_type (uri):
	global cache, ocache
	if not ocache: discover ()
	return find_input (uri), find_output (uri)

def find_output (uri):
	global cache, ocache
	if not ocache: discover ()
	try:
		module, it, ot, opt = cache.get (uri)
	except TypeError:
		raise KeyError
	return find_object (module, ot)

def find_input (uri):
	global cache, ocache
	if not ocache: discover ()
	try:
		module, it, ot, opt = cache.get (uri)
	except TypeError:
		raise KeyError
	return find_object (module, it)


