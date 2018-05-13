# ------------------------------------------------
#	Python Siesta
# Siesta is a REST client for python
#
#	Copyright (c) 2008 Rafael Xavier de Souza
#
#	This program is free software: you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation, either version 3 of the License, or
#	(at your option) any later version.
#
#	This program is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with this program.  If not, see <http://www.gnu.org/licenses/>.
# ------------------------------------------------
#
# Modified at Sep 20, 2017 by Hans Roh
#
# ------------------------------------------------

__version__ = "0.5.2"
__author__ = "Sebastian Castillo <castillobuiles@gmail.com>"
__contributors__ = []

import re
import time
import logging
import json
import requests
import base64
from urllib.parse import urlparse, urlencode
from .attrdict import AttrDict
import html2text
import io
import pprint

USER_AGENT = "Python-siesta/%s" % __version__

class Auth(object):
	def encode_params(self, base_url, method, params):
		raise NotImplementedError()

	def make_headers(self):
		pass


class APIKeyAuth(Auth):
	def __init__(self, api_key, auth_header_name="Authorization"):
		self.api_key = api_key
		self.auth_header_name = auth_header_name

	def encode_params(self):
		pass

	def make_headers(self):
		return {self.auth_header_name: self.api_key, }


class BasicAuth(Auth):
	def __init__(self, api_username, api_password, auth_header_name="Authorization"):
		self.api_username = api_username
		self.api_password = api_password
		self.auth_header_name = auth_header_name
		
	def encode_params(self):
		basic_token = base64.encodestring('' + str(self.api_username) + ':' + str(self.api_password))
		basic_token = basic_token.replace('\n', '')
		return basic_token
	
	def make_headers(self):
		token = self.encode_params()
		return {self.auth_header_name: 'Basic ' + token, }

class Response (object):
	def __init__ (self, resource, respnose):
		self.__response = respnose
		self.resource = resource
		self.data = AttrDict ()
		self.set_data (respnose)		
	
	def __getattr__ (self, attr):
		return getattr (self.__response, attr)
	
	def __str__ (self):
		if not isinstance (self.data, str):			
			s = io.StringIO()
			pprint.pprint(self.data, s)
			d = s.getvalue()		
		else:
			d = self.data	
		return "%d %s\n%s" % (self.__response.status_code, self.__response.reason, d)
		
	def set_data (self, resp):
		if not resp.text.strip ():
			self.data = None
		
		else:	
			ct = resp.headers.get ('content-type')
			if ct is None or ct.find ('text/html') == 0:
				h = html2text.HTML2Text()
				h.ignore_links = True
				text = h.handle(resp.text)
				self.data = text
					
			elif ct is None or ct.find ('text/') == 0:
				self.data = resp.text.strip ()
			else:
				data = resp.json ()
				if isinstance (data, dict):
					self.data.update (data)
				else:
					self.data = data
			
		if not str(resp.status_code).startswith("2"):			
			raise AssertionError (self)
		

class Resource(object):
	def __init__(self, uri, api, logger):
		self._api = api
		self._uri = uri
		self._logger = logger
		self._scheme, self._host, self._url = urlparse (self._api.base_url + self._uri) [:3]
		self._headers = {'User-Agent': USER_AGENT, "Accept": 'application/json'}
		
	def __getattr__(self, name):	
		key = self._uri + '/' + name
		return Resource(uri=key, api=self._api, logger = self._logger)		

	def __call__(self, *ids):
		if not ids:
			return self		
		key = self._uri
		for id in ids:
			if key:
				key += '/' + str (id)
			else:
				key += str (id)	
		return Resource(uri=key, api=self._api, logger = self._logger)		
	
	def _request (self, method, data, **kwargs):
		url = self._url
		if len(kwargs) > 0:
			url = "%s?%s" % (url, urlencode(kwargs))		
		headers = {"Content-Type": "application/json"}
		return self._continue_request(method, url, data, headers)		
	
	def get(self, **kwargs):
		return self._request ('GET', None, **kwargs)
	
	def delete(self, **kwargs):
		return self._request ('DELETE', None, **kwargs)
	
	def options(self, **kwargs):
		return self._request ('OPTIONS', None, **kwargs)	
				
	def post(self, data, **kwargs):
		return self._request ('POST', data, **kwargs)
	
	def put(self, data, **kwargs):
		return self._request ('PUT', data, **kwargs)
	
	def patch(self, data, **kwargs):
		return self._request ('PATCH',data, **kwargs)

	def _continue_request(self, method, url, data, headers):
		if self._api.auth:
			headers.update(self._api.auth.make_headers())		
		if not 'User-Agent' in headers:
			headers['User-Agent'] = self._headers['User-Agent']
		if not 'Accept' in headers and 'Accept' in self._headers:
			headers['Accept'] = self._headers['Accept']
		
		url = "%s://%s%s" % (self._scheme, self._host, url)		
		if isinstance (data, dict):			
			data = json.dumps (data)
			
		func = getattr (self._api.session, method.lower ())
		if data is not None:
			if not isinstance (data, str):
				raise TypeError ("payload should be str or dic type")
			resp = func (url, data, headers = headers, timeout = self._api.REQ_TIMEOUT, verify = False)	
		else:
			resp = func (url, headers = headers, timeout = self._api.REQ_TIMEOUT, verify = False)
									
		return self._getresponse (resp)
		
	def _getresponse(self, resp):
		if resp.status_code == 202:
			status_url = resp.getheader('content-location')
			if not status_url:
				raise Exception('Empty content-location from server')

			status_uri = urlparse(status_url).path
			resource = Resource(uri=status_uri, api=self._api, logger = self._logger).get()
			retries = 0
			MAX_RETRIES = 3
			resp_status = resource.response.status_code
			
			while resp_status != 303 and retries < MAX_RETRIES:			
				retries += 1
				new_resp.get()
				time.sleep(5)
				
			if retries == MAX_RETRIES:
				raise Exception('Max retries limit reached without success')
			
			location = status.conn.getresponse().getheader('location')
			return Resource(uri=urlparse(location).path, api=self._api, logger = self._logger).get()			
		
		return Response (self, resp)
		

class API(object):
	REQ_TIMEOUT = 60
	def __init__(self, base_url, auth=None, logger = None):
		self.base_url = base_url + '/' if not base_url.endswith('/') else base_url
		self.api_path = urlparse(base_url).path
		self.session = requests.Session ()
		self.auth = auth
		self.logger = logger

	def __getattr__(self, name):
		if name in ('get', 'post', 'put', 'patch', 'delete', 'options'):
			r = Resource(uri='', api=self, logger = self.logger)
			return getattr (r, name)
		return Resource(uri=name, api=self, logger = self.logger)
	
	def __call__(self, id):
		r = Resource(uri='', api=self, logger = self.logger)
		return r (id)
