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

elif sys.argv[-1] == 'develop':
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
	'aquests.protocols',
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
	'aquests.lib.pmaster',
	'aquests.lib.nets',
	'aquests.lib.awsapi',
	'aquests.lib.googleapi',	
]

package_dir = {'aquests': 'aquests'}

package_data = {
	"aquests": [
		"protocols/dns/*.txt",
		"protocols/dns/pydns/*.txt",		
	]
}

install_requires = [
	"h2==3.0.1",
	"psycopg2==2.7.3.1",
	"redis==2.10", 
	"pymongo==3.4.0", 
	"event_bus==1.0.2",
	"protobuf==3.5.2.post1",
	"psutil",
	"html2text",	
]
if os.name == "posix":
	install_requires.append ("psutil")
	install_requires.append ("setproctitle")

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
	license='MIT',
	platforms = ["posix", "nt"],
	download_url = "https://pypi.python.org/pypi/aquests",
	install_requires = install_requires,
	classifiers=classifiers
)
