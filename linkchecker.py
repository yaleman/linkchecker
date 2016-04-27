#!/usr/bin/env python

""" This does link checker stuff, eat a butt if you don't like it.
Started 2016-04-27 by jhodgkinson
"""
from Queue import Queue
from bs4 import BeautifulSoup
import requests

class URLDb(object):
    """ does the link database/checker thing so you don't end up checking URLs twice"""

    def __init__(self, starturls={}):
        """ let's get this party started """
        self.processqueue = Queue()
        self.urls = {}
        self.dontspider = []
        for url in starturls:
            self.processqueue.put(url)
        self.failedurls = {}
        self.processed = 0

    def fixlink(self, parent, test):
        """ takes a found link and cleans it up a bit"""
        dudlink = u''
        # kill anchor refs and mailtos
        if test.lower().startswith("mailto:") or test.lower().startswith('#'):
            return dudlink

        # protocol handling blah blah
        if parent.lower().startswith( 'https:' ):
            proto = 'https'
        elif parent.lower().startswith( 'http:' ):
            proto = 'http'
        elif parent.lower().startswith('ftp:' ):
            proto = 'ftp'
            
        # protocol agnostic link
        if test.startswith('//'):
            return "{}:{}".format(proto,test)
        elif test.startswith('/'):
            # if it's a relative link
            if parent.endswith('/'):
                parent = parent[:-1]
            return '{}://{}{}'.format(proto,parent.replace('//','/').split("/")[1],test)
        else:
            return test
    
    def start( self ):
        while self.processqueue.empty() == False:
            self.process(self.processqueue.get())

    def process(self, test):
        """ handle a URL """
        self.processed += 1
        
        print "*"*20
        print "Processing: {}".format(test)
        
        if test.lower().startswith("mailto:"):
            pass
        if test in self.urls and self.urls[test] == True:
            print("Already tested, jackass")
        elif test in self.failedurls:
            print("Already tested and failed, not retrying")
        else:
            print("Grabbing: {}".format(test))
            try:
                tmp = requests.get(test)
            except requests.exceptions.ConnectionError:
                # sometimes it just throws a connection error
                self.failedurls[test] = { 'status_code' : 504, 'headers' : '' }
                self.urls[test] = True
                return
            # check if we're allowed to spider the URL
            dontspider = test in self.dontspider
            # if it worked, and we're allowed to spider it
            if tmp.status_code < 400 and tmp.status_code > 199 and dontspider == False:
                # if it's not supposed to be used
                if tmp.headers['content-type'] in BAD_CONTENT_TYPES or tmp.headers['content-type'].startswith('image/'):
                    print "Ignoring content type {}".format(tmp.headers['content-type'])
                    self.urls[test] = True
                    return
                bs = BeautifulSoup(tmp.content,"html.parser")
                # find all the URLs
                for image in bs.find_all('img'):
                    if 'src' in image.attrs and image.attrs['src'] != "":
                        self.addurl(test, image.attrs['src'],'image')
                for link in bs.find_all('a'):
                    newurl = self.fixlink(test,link.attrs['href'])
                    # if there's some href's
                    if 'href' in link.attrs and newurl != u'':
                        self.addurl(test, link.attrs['href'], 'href' )
            # this means it succeeded but we're not allowed to spider it
            elif dontspider:
                self.urls[test] = True
            # if for some reason it shat the bed, take a note.
            else:
                self.failedurls[test] = { 'status_code' : tmp.status_code, 'headers' : tmp.headers }
                self.urls[test] = True

    def addurl(self, parent, newurl ,type):
        """ test a URL and put it in the queue if it's fine"""
        newurl = self.fixlink(parent, newurl)

        # if it's in the base site, spider it, if not just check for 404's and stuff
        canspider = False
        for base in STARTURLS:
            if newurl.lower().startswith(base.lower()):
                canspider = True

        # if it's blocked by the isallowed thing, don't spider it
        if canspider == False and newurl not in self.dontspider:
            self.dontspider.append(newurl)
        # if it's not in the existing url set and is allowed
        elif newurl not in self.urls:
            # add it to the queue
            self.processqueue.put(newurl)
            print( "Adding {}: {}".format( type, newurl))
            self.urls[newurl] = False


STARTURLS = ['https://sca.yaleman.org', 'https://threegoldbees.com', 'https://travelling.boryssnorc.com']
BAD_CONTENT_TYPES = []
URLDB = URLDb(STARTURLS)

URLDB.start()
print "#"*20
print "FAILED URLS"
for url in URLDB.failedurls:
    print url, URLDB.failedurls[url]

print "Processed: {} urls".format(URLDB.processed)
