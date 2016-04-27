#!/usr/bin/env python

""" This does link checker stuff, eat a butt if you don't like it.
Started 2016-04-27 by jhodgkinson
"""

from bs4 import BeautifulSoup
import requests

class URLDb(object):
    """ does the link database/checker thing so you don't end up checking URLs twice"""
    urls = {}

    def fixlink(self, parent, test):
        """ takes a found link and cleans it up a bit"""
        if parent.lower().startswith( 'https:' ):
            proto = 'https'
        elif parent.lower().startswith( 'http:' ):
            proto = 'http'
            
        if test.startswith('//'):
            return "{}{}".format(proto,test)
        elif test.startswith('/'):
            if parent.endswith('/'):
                return '{}{}'.format(parent[:-1],test)
            else:
                return '{}{}'.format(parent,test)
        else:
            return test

    def process(self, test):
        """ handle a URL, this should probably be in a queue or something? """
        if test in self.urls:
            print("Already here, jackass")
        else:
            newurls = []
            self.urls[test] = None
            print("Trying {}".format(test))
            tmp = requests.get(test)
            # if it worked
            if tmp.status_code < 400 and tmp.status_code > 199:
                bs = BeautifulSoup(tmp.content,"html.parser")
                # find all the URLs
                for link in bs.find_all('a'):
                    if 'href' in link.attrs:
                        newurl = self.fixlink(test,link.attrs['href'])
                        if newurl not in newurls:
                            newurls.append(newurl)
                            print '{}'.format(newurl)

STARTURLS = ['http://localhost:1313/']

URLDB = URLDb()

for url in STARTURLS:
    URLDB.process(url)
