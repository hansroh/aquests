import aquests

def test_rpcssl ():
    stub = aquests.rpc ("https://pypi.python.org/pypi")
    stub.package_releases('roundup')
    stub.package_releases('roundup')
    stub.package_releases('roundup')
    
    aquests.fetchall ()
