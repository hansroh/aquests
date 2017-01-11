import aquests
import route_guide_pb2

stub = aquests.grpc ("http://127.0.0.1:5000/routeguide.RouteGuide")
point = route_guide_pb2.Point (latitude=409146138, longitude=-746188906)
stub.GetFeature (point)
stub.GetFeature (point)
stub.GetFeature (point)

aquests.fetchall ()


