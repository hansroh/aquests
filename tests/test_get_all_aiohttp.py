import aiohttp
import asyncio
import timeit

@asyncio.coroutine
def fetch (url):
	r = yield from aiohttp.request ('GET', url)
	print ('%s %s' % (r.status, r.reason), end = " ")
	return (yield from r.read ())
	
@asyncio.coroutine
def bound_fetch (sem, url):
	with (yield from sem):
		page = yield from fetch (url)
	print ('%d bytes received' % len (page))

@asyncio.coroutine
def fetch_all (r):
	global started	
	sem = asyncio.Semaphore (10)
	tasks = []
	for i in range (r):
		task = asyncio.ensure_future (bound_fetch (sem, "http://127.0.0.1:5000/"))
		tasks.append (task)	
	started = timeit.default_timer ()	
	yield from asyncio.gather (*tasks)

def test_get_all_aiohttp ():
	future = asyncio.ensure_future (fetch_all (1000))	
	asyncio.get_event_loop ().run_until_complete (future)
	
	_duration = timeit.default_timer ()	- started
	
	print ('* 1000 tasks during %1.2f seconds, %1.2f tasks/sec' % (_duration, 1000 / _duration))
