"""
Hans Roh 2015 -- http://osp.skitai.com
License: BSD
"""

import aquests
__VER__ = aquests.VERSION

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
  'Development Status :: 4 - Beta',
  'Topic :: Internet :: WWW/HTTP',
	'Topic :: Internet :: WWW/HTTP :: HTTP Servers',				
	'Environment :: Console',	
	'Topic :: Software Development :: Libraries :: Python Modules',
	'Intended Audience :: Developers',
	'Intended Audience :: Science/Research',
	'Programming Language :: Python',
	'Programming Language :: Python :: 2.7',
	'Programming Language :: Python :: 3'
]

packages = [
	'aquests'	
]

package_dir = {
	'aquests': 'aquests'	
}
data_files = []
package_data = {}

setup(
	name='aquests',
	version=__VER__,
	description='Asynchronous Parallel Requests',	
	url = 'https://github.com/hansroh/aquests',
	author='Hans Roh',
	author_email='hansroh@gmail.com',	
	packages=packages,
	package_dir=package_dir,
	package_data = package_data,
	license='BSD',
	platforms = ["posix", "nt"],
	download_url = "https://pypi.python.org/pypi/aquests",
	install_requires = ["skitai>=0.17", "lxml<=3.4.4", "cssselect", "html5lib"],
	classifiers=classifiers
)
