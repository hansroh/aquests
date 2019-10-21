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

with open('aquests/__init__.py', 'r') as fd:
	version = re.search(r'^__version__\s*=\s*"(.*?)"',fd.read(), re.M).group(1)

if sys.argv[-1] == 'publish':
	buildopt = ['sdist', 'upload']
	if os.name == "nt":
		buildopt.insert (0, 'bdist_wheel')
	os.system('python setup.py %s' % " ".join (buildopt))
	#os.system('twine upload dist/aquests-%s*' % version)
	for each in os.listdir ("dist"):
		os.remove (os.path.join ('dist', each))
	sys.exit()

elif sys.argv[-1] == 'link':
	import site
	if os.name == "nt":
		linkdir = [each for each in site.getsitepackages() if each.endswith ("-packages")][0]
	else:
		linkdir = [each for each in site.getsitepackages() if each.find ("/local/") !=- 1 and each.endswith ("-packages")][0]
	target = os.path.join (os.path.join (os.getcwd (), os.path.dirname (__file__)), "aquests")
	link = os.path.join (linkdir, "aquests")
	if os.name == "nt":
		os.system ("mklink /d {} {}".format (link, target))
	else:
		os.system ("ln -s {} {}".format (target, link))
	sys.exit ()

classifiers = [
  'License :: OSI Approved :: MIT License',
  'Development Status :: 4 - Beta',
  'Topic :: Internet :: WWW/HTTP',
  'Topic :: Database :: Front-Ends',
	'Environment :: Console',
	'Topic :: Software Development :: Libraries :: Python Modules',
	'Intended Audience :: Developers',
	'Intended Audience :: Science/Research',
	'Programming Language :: Python',
	'Programming Language :: Python :: 3'
]

packages = [
	'aquests',
	'aquests.client',
	'aquests.dbapi',
	'aquests.protocols',
	'aquests.protocols.dns',
	'aquests.protocols.dns.pydns',
	'aquests.protocols.http',
	'aquests.protocols.http2',
	'aquests.protocols.http2.hyper',
	'aquests.protocols.http2.hyper.common',
	'aquests.protocols.http2.hyper.http11',
	'aquests.protocols.http2.hyper.http20',
	'aquests.protocols.http2.hyper.http20.h2',
	'aquests.protocols.http2.hyper.packages',
	'aquests.protocols.http2.hyper.packages.rfc3986',
	'aquests.protocols.ws',
	'aquests.protocols.smtp',
	'aquests.protocols.grpc',
	'aquests.protocols.proxy',
	'aquests.athreads'
]

package_dir = {'aquests': 'aquests'}

package_data = {
	"aquests": [
		"protocols/dns/*.txt",
		"protocols/dns/pydns/*.txt",
		"protocols/http2/hyper/*.txt",
		"protocols/http2/hyper/*.pem",
	]
}

install_requires = [
	"rs4",
	"h2",
	#"protobuf",
	#"redis",
	#"pymongo",
	#"psycopg2-binary" # becasue of bson, install last
]

with open ('README.rst', encoding='utf-8') as f:
	long_description = f.read()

setup(
	name='aquests',
	version=version,
	description='Asynchronous Multiplexing HTTP2/DBO Requests',
	long_description = long_description,
	url = 'https://gitlab.com/hansroh/aquests',
	author='Hans Roh',
	author_email='hansroh@gmail.com',
	packages=packages,
	package_dir=package_dir,
	package_data = package_data,
	entry_points = {},
	license='MIT',
	platforms = ["posix", "nt"],
	download_url = "https://pypi.python.org/pypi/aquests",
	install_requires = install_requires,
	classifiers=classifiers
)
