"""
Hans Roh 2015 -- http://osp.skitai.com
License: BSD
"""
import re
import sys
import os
import shutil, glob
from warnings import warn
try:
	from setuptools import setup
except ImportError:
	from distutils.core import setup

if sys.argv[-1] == 'publish':
	if os.name == "nt":
		os.system('python setup.py sdist upload') # bdist_wininst --target-version=2.7
	else:
		os.system('python setup.py sdist upload')
	sys.exit()

classifiers = [
  'License :: OSI Approved :: BSD License',
  'Development Status :: 3 - Alpha',
  'Topic :: Internet :: WWW/HTTP',
  'Topic :: Database :: Front-Ends',
	'Environment :: Console',	
	'Topic :: Software Development :: Libraries :: Python Modules',
	'Intended Audience :: Developers',
	'Intended Audience :: Science/Research',
	'Programming Language :: Python',	
	'Programming Language :: Python :: 3'
]

PY_MAJOR_VERSION = sys.version_info [0]
if PY_MAJOR_VERSION == 3:
	if os.path.isfile ("aquests/lib/py2utils.py"):
		os.remove ("aquests/lib/py2utils.py")
		try: os.remove ("aquests/lib/py2utils.pyc")
		except OSError: pass		
else:
	if not os.path.isfile ("aquests/lib/py2utils.py"):
		with open ("aquests/lib/py2utils.py", "w") as f:
			f.write ("def reraise(type, value, tb):\n\traise type, value, tb\n")			

packages = [
	'aquests',
	'aquests.client',
	'aquests.dbapi',	
	'aquests.protocols.dns',
	'aquests.protocols.dns.pydns',
	'aquests.protocols.http',	
	'aquests.protocols.http2',
	'aquests.protocols.ws',	
	'aquests.protocols.smtp',
	'aquests.protocols.grpc',
	'aquests.protocols.proxy',
	'aquests.lib',
	'aquests.lib.athreads',
	'aquests.lib.nets'
]

package_dir = {'aquests': 'aquests'}

package_data = {
	"aquests": [
		"protocols/dns/*.txt",
		"protocols/dns/pydns/*.txt"	
	]
}

install_requires = [
	"redis==2.10", "pymongo==3.4.0", 
	"h2==2.5.1", "protobuf==3.1.0.post1", 
	"psycopg2==2.6.2"
]

with open('aquests/__init__.py', 'r') as fd:
	version = re.search(r'^__version__\s*=\s*"(.*?)"',fd.read(), re.M).group(1)

setup(
	name='aquests',
	version=version,
	description='Asynchronous HTTP2/DBO Requests',
	url = 'https://gitlab.com/hansroh/aquests',
	author='Hans Roh',
	author_email='hansroh@gmail.com',	
	packages=packages,
	package_dir=package_dir,
	package_data = package_data,
	license='BSD',
	platforms = ["posix", "nt"],
	download_url = "https://pypi.python.org/pypi/aquests",
	install_requires = install_requires,
	classifiers=classifiers
)
