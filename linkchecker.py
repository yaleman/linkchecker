#!/usr/bin/env python

""" This does link checker stuff, eat a butt if you don't like it.
Started 2016-04-27 by jhodgkinson
"""

# content types to ignore content from
BAD_CONTENT_TYPES = [ 'image/jpeg', 'image/gif' ]
BAD_CONTENT_TYPE_ROOTS = ['application/', 'image/' ]
# ignore hrefs starting with these things
BAD_SCHEMAS = [ s.lower() for s in [ 'irc://', 'mailto:', '#', 'ftp://' ] ]


# imports!

import argparse, sys
from Queue import Queue
try:
	from bs4 import BeautifulSoup
except ImportError:
	print("Please install BeautifulSoup, package missing.")
	print("https://www.crummy.com/software/BeautifulSoup/")
	sys.exit()
try:
	import requests
except ImportError:
	print("Please install requests, package missing.")
	print("http://docs.python-requests.org/en/master/")
	sys.exit()

parser = argparse.ArgumentParser()
# these are the URLs we're going to parse
parser.add_argument("starturls", nargs='+')
# if you want to show all the things, add --debug
parser.add_argument("--debug", action='store_true', help="Output debugging text")

args = parser.parse_args()

if args.debug:
	DEBUG = True
else:
	DEBUG = False

def log(text):
	""" in case of debugging, print the log string. lazy """
	if DEBUG:
		print(text)


def checkproto(url, valid_protocols):
	""" checks against a list of valid protocols, in a really hacky way"""
	for proto in valid_protocols:
		if url.lower().startswith("{}:".format(proto.lower())):
			return True
	return False

class URLDb(object):
	""" does the link database/checker thing so you don't end up checking URLs twice"""

	def __init__(self, starturls):
		""" let's get this party started, feed it a list of base urls """
		# some basic variables
		self.starturls = starturls
		self.dontspider = []
		self.processed = 0
		self.urls = {}
		self.failedurls = {}

		# build the initial queue
		self.processqueue = Queue()
		for url in self.starturls:
			self.processqueue.put(url)
		# do the processing
		while self.processqueue.empty() == False:
			self.process(self.processqueue.get())
		# show a list of failed urls
		if( len(self.failedurls) > 0 ):
			print("FAILED URLS ({})".format(len(self.failedurls)))
			for url in self.failedurls:
				print( url, self.failedurls[url] )
			log("Processed: {} urls".format(self.processed))


	def fixlink(self, parent, test):
		""" takes a found link and cleans it up a bit"""
		#test = test.strip()
		log("Fixing: {},{}".format(parent, test))
		# kill things we don't care about.
		for badschema in BAD_SCHEMAS:
			# it's worth doing the lower just in case
			if test.lower().startswith( badschema ):
				return u''

		# relative links
		if test.startswith('..'):
			parent = "/".join(parent.split("/")[:-1])
			# if it's literally linking to the parent, we've already spidered it
			if len(test) < 3:
				return u''
			else:
				test = test[3:]
				log("found relative link, rewriting to fixlink({},{})".format(parent, test))
				return self.fixlink(parent, test)

		# remove anchor references
		if '#' in test:
			test = "".join(test.split("#")[:-1])

		# remove trailing slashes
		if test.endswith("/"):
			test = test[:-1]

		# protocol handling blah blah
		if parent.lower().startswith('https:'):
			proto = 'https'
		elif parent.lower().startswith('http:'):
			proto = 'http'
		elif parent.lower().startswith('ftp:'):
			proto = 'ftp'

		# protocol agnostic link
		if test.startswith('//'):
			retval = "{}:{}".format(proto, test)
		elif test.startswith('/'):
			# if it's a relative link
			if parent.endswith('/'):
				parent = parent[:-1]
			retval = '{}://{}{}'.format(proto, parent.replace('//','/').split("/")[1], test)
		elif checkproto(test, ('http', 'https', 'ftp' )):
			log("returning original test {}".format(test))
			retval = test
		else:
			if parent.endswith("/"):
				dirbreak = ""
			else:
				dirbreak = "/"
			retval = self.fixlink(parent, "{}{}{}".format(parent, dirbreak, test))
		log("Fixlink returning: '{}'".format(retval))
		return retval


	def process(self, test):
		""" handle a URL """
		self.processed += 1

		log("*"*20)
		log("Processing: {}".format(test))

		if test.lower().startswith("mailto:"):
			return
		if test in self.urls and self.urls[test] == True:
			log("Already tested, jackass")
			return
		elif test in self.failedurls:
			log("Already tested and failed, not retrying")
			return
		else:
			log("Grabbing: {}".format(test))
			# check if we're allowed to spider the URL
			dontspider = test in self.dontspider
			try:
				tmp = requests.get(test, stream=True)
				if dontspider == False:
					content = tmp.content
				else:
					content = ""
				tmp.close()
			except requests.exceptions.ConnectionError:
				# sometimes it just throws a connection error
				self.failedurls[test] = {'status_code' : 504, 'headers' : ''}
				self.urls[test] = True
				return
			except requests.exceptions.InvalidSchema:
				self.failedurls[test] = {'status_code' : 'invalid_schema', 'headers' : '' }
				self.urls[test] = True
				return
			# if it worked, and we're allowed to spider it
			if tmp.status_code < 400 and tmp.status_code > 199 and dontspider == False:
				# if it's not supposed to be used
				content_type = tmp.headers['content-type']
				if content_type.lower().startswith( "text/" ) == False:
					log("Ignoring content type {}".format(tmp.headers['content-type']))
					self.urls[test] = True
					return

				bsobject = BeautifulSoup(content, "html.parser")
				# find all the URLs
				for image in bsobject.find_all('img'):
					if 'src' in image.attrs and image.attrs['src'] != "":
						self.addurl(test, image.attrs['src'], 'image')
				for link in bsobject.find_all('a'):
					# if there's some href's
					if 'href' in link.attrs:
						self.addurl(test, link.attrs['href'], 'href')
			# this means it succeeded but we're not allowed to spider it
			elif dontspider:
				self.urls[test] = True
			# if for some reason it shat the bed, take a note.
			else:
				self.failedurls[test] = {'status_code' : tmp.status_code, 'headers' : tmp.headers}
				self.urls[test] = True

	def addurl(self, parent, newurl, typename):
		""" test a URL and put it in the queue if it's fine"""
		log("Attempting to add '{}'".format(newurl))
		if newurl.strip() == '.' or newurl.strip() == "#":
			return False

		newurl = self.fixlink(parent, newurl)
		if newurl == u'' or newurl == u'.':
			return False

		# if it's in the base site, spider it, if not just check for 404's and stuff
		canspider = False
		for base in self.starturls:
			if newurl.lower().startswith(base.lower()):
				canspider = True

		# if it's blocked by the isallowed thing, don't spider it
		if canspider == False and newurl not in self.dontspider:
			self.dontspider.append(newurl)
		# if it's not in the existing url set and is allowed
		elif newurl not in self.urls:
			# add it to the queue
			self.processqueue.put(newurl)
			log("Adding {}: {}".format(typename, newurl))
			self.urls[newurl] = False


if __name__ == '__main__':
	URLDB = URLDb(args.starturls)
