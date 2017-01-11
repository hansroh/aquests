from . import asynmongo, asynpsycopg2, asynredis

def set_timeout (timeout):
	for each in (asynmongo.AsynConnect, asynpsycopg2.AsynConnect, asynredis.AsynConnect):
		each.zombie_timeout = timeout		

