from . import asynmongo, asynpsycopg2, asynredis

DB_PGSQL = "*postgresql"
DB_POSTGRESQL = "*postgresql"
DB_SQLITE3 = "*sqlite3"
DB_REDIS = "*redis"
DB_MONGODB = "*mongodb"

def set_timeout (timeout):
	for each in (asynmongo.AsynConnect, asynpsycopg2.AsynConnect, asynredis.AsynConnect):
		each.zombie_timeout = timeout		

