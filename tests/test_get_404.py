import aquests
import route_guide_pb2

def test_get_404 ():
	for i in range (3):
		aquests.get ("http://127.0.0.1:5000/routeguide.RouteGuide_")
	aquests.fetchall ()
