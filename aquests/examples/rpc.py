import aquests

stub = aquests.rpc ("https://pypi.python.org/pypi")
stub.package_releases('roundup')

stub2 = aquests.rpc ("http://blade-1.lufex.com:3424/rpc2")
stub2.bladese ("adsense.websearch", "computer", 0, 3)
stub2.bladese ("adsense.websearch", "computer monitor", 0, 3)

aquests.fetchall ()
