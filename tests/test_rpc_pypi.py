import aquests

def test_rpc_pypi ():
    stub = aquests.rpc ("https://pypi.python.org/pypi/")
    stub.package_releases('roundup')
    stub.prelease_urls('roundup', '1.4.10')
    
    aquests.fetchall ()
