import sys
from google.protobuf import descriptor_pb2

cache = {}

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

discover ()

def find_type (uri):
	global cache	
	if not cache: discover ()
	return find_input (uri), find_output (uri)
	
def find_output (uri):
	global cache	
	if not cache: discover ()
	try:
		module, it, ot, opt = cache.get (uri)
	except TypeError:
		raise KeyError	
	return getattr (module, ot [0]), ot [1]

def find_input (uri):
	global cache	
	if not cache: discover ()
	try:
		module, it, ot, opt = cache.get (uri)
	except TypeError:
		raise KeyError	
	return getattr (module, it [0]), it [1]
	
