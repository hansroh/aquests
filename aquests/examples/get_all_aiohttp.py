import aiohttp
import asyncio
import timeit

started = 0
req_id = 0

@asyncio.coroutine
def fetch (url):
	global req_id
	req_id += 1
	r = yield from aiohttp.request ('GET', url)
	print ('2017.01.13 14:13:36 [info] REQ get-%d. HTTP/2.0 %s %s' % (req_id, r.status, r.reason), end = " ")
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

future = asyncio.ensure_future (fetch_all (1000))	
asyncio.get_event_loop ().run_until_complete (future)

print ('duration:', timeit.default_timer ()	- started)
