import sys

if sys.version_info [:2] > (3, 4):
	from event_bus import EventBus
else:
	class EventBus:
		def add_event (self, event):
			raise SystemError ("Required Python 3.5+")

			