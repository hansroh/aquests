from rs4 import producers, compressors
import struct
	
def get_messages (fp):
	decompressor = None	
	msgs = []
	byte = fp.read (1)
	while byte:
		iscompressed = struct.unpack ("!B", byte) [0]
		length = struct.unpack ("!I", fp.read (4)) [0]
		msg = fp.read (length)
		msg = decode_message (msg, iscompressed)
		byte = fp.read (1)
		msgs.append (msg)
	return msgs


def decode_message (msg, iscompressed):	
	if iscompressed:
		decompressor = compressors.GZipDecompressor ()
		msg = decompressor.decompress (msg)	+ decompressor.flush ()
	return msg
	
