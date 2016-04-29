#!/usr/bin/env python

""" This does link checker stuff, eat a butt if you don't like it.
Started 2016-04-27 by jhodgkinson
"""

import argparse
from Queue import Queue
from bs4 import BeautifulSoup
import requests

# content types to ignore content from
BAD_CONTENT_TYPES = []

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
        lf len(failedurls) > 0:
			print "FAILED URLS ({})".format(len(self.failedurls))
			for url in self.failedurls:
				print url, self.failedurls[url]
		log("Processed: {} urls".format(self.processed))

    def fixlink(self, parent, test):
        """ takes a found link and cleans it up a bit"""
        dudlink = u''
        # kill anchor refs and mailtos
        if test.lower().startswith("mailto:") or test.lower().startswith('#'):
            return dudlink

        # protocol handling blah blah
        if parent.lower().startswith('https:'):
            proto = 'https'
        elif parent.lower().startswith('http:'):
            proto = 'http'
        elif parent.lower().startswith('ftp:'):
            proto = 'ftp'

        # protocol agnostic link
        if test.startswith('//'):
            return "{}:{}".format(proto, test)
        elif test.startswith('/'):
            # if it's a relative link
            if parent.endswith('/'):
                parent = parent[:-1]
            return '{}://{}{}'.format(proto, parent.replace('//','/').split("/")[1], test)
        else:
            return test

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
            # if it worked, and we're allowed to spider it
            if tmp.status_code < 400 and tmp.status_code > 199 and dontspider == False:
                # if it's not supposed to be used
                content_type = tmp.headers['content-type']
                if content_type in BAD_CONTENT_TYPES or content_type.startswith('image/'):
                    log("Ignoring content type {}".format(tmp.headers['content-type']))
                    self.urls[test] = True
                    return
                bsobject = BeautifulSoup(content, "html.parser")
                # find all the URLs
                for image in bsobject.find_all('img'):
                    if 'src' in image.attrs and image.attrs['src'] != "":
                        self.addurl(test, image.attrs['src'], 'image')
                for link in bsobject.find_all('a'):
                    newurl = self.fixlink(test, link.attrs['href'])
                    # if there's some href's
                    if 'href' in link.attrs and newurl != u'':
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
        newurl = self.fixlink(parent, newurl)

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
