# -*- coding: utf-8 -*-
import requests, os, re, sys, time
from optparse import OptionParser
from threading import Thread
from time import sleep

reload(sys)
sys.setdefaultencoding('utf-8')

UPDATE_INTERVAL = 0.01
CONTENT_TYPES   = ('text/html', 'application/x-javascript', 'text/css')


# 线程类
class URLThread(Thread):

    def __init__(self, url, timeout = 10, allow_redirects = True):

        super(URLThread, self).__init__()
        self.url = url
        self.timeout = timeout
        self.response = None
        self.allow_redirects = allow_redirects


    def run(self):

        try:
            self.response = requests.get(self.url, timeout = self.timeout, allow_redirects = self.allow_redirects)

            if self.response.headers['content-type'] in CONTENT_TYPES:
                if self.response.encoding == 'ISO-8859-1':
                    self.response.encoding = self.response.apparent_encoding

        except Exception , what:
            print what
            pass

# 多线程
def multi_get(urls, timeout = 10, allow_redirects = True):

    def alive_count(lst):
        alive = map(lambda x : 1 if x.isAlive() else 0, lst)
        return reduce(lambda a, b : a + b, alive)

    threads = [ URLThread(url, timeout, allow_redirects) for url in urls ]

    for thread in threads:
        thread.start()

    while alive_count(threads) > 0:
        sleep(UPDATE_INTERVAL)

    return [ (x.url, x.response) for x in threads ]


# 主类
class Copyer(object):

    def __init__(self, r):
        self.response = r
        self.baseurl  = r[0]
        self.home     = self.baseurl.split('/')[2]
        self._create_dir()
        self.download()


    def download(self):
        _need = self.get_allthings_need_to_download()
        print 'Begin Write index.html'
        open('%s/index.html'%self.home, 'w').write((_need[1]))
        _responses = multi_get(_need[0])
        self._download_files(_responses)


    def get_allthings_need_to_download(self):
        _content = self.response[1].text.replace('"//', 'http://')
        _links = self._get_links_from_content(_content)
        return self._get_fullpath_links(_links, _content)


    def link_alias(self, link):
        link = self.full_link(link)
        name = link.rsplit('/',1)[1]

        if '.css' in name:
            name = name[:name.find('.css')+4]
            return '/assets/css/%s'%name
        elif '.js' in name:
            name = name[:name.find('.js')+3]
            return '/assets/js/%s'%name
        else:
            return '/assets/img/%s'%name


    def strip_link(self, link):
        if link and (link[0] in ['"',"'"]):
            link = link[1:]

        while link and (link[-1] in ['"',"'"]):
            link = link[:-1]

        while link.endswith('/'):
            link = link[:-1]

        if link and (link[0] not in ["<","'",'"']) and ('feed' not in link):
            return link
        else:
            return ''


    def full_link(self, link, baseurl=None):
        if not baseurl:
            baseurl = self.baseurl

        if '?' in link:
            link = link.rsplit('?',1)[0]

        if link.startswith('//'):
            link = 'http:'+link

        if not link.startswith('http://'):
            if link.startswith('/'):
                link = '/'.join(baseurl.split('/',3)[:3]) + link
            elif link.startswith('../'):

                while link.startswith('../'):
                    baseurl = baseurl.rsplit('/',2)[0]
                    link = link[3:]

                link = baseurl+'/'+link
            else:
                link = baseurl.rsplit('/',1)[0]+'/'+link

        return link


    def _download_files(self, responses, depth=3):
        for url, data in responses:
            if url.endswith('.css'):
                self._download_css(url, data, depth)
            else:
                try:
                    _filepath = '%s%s'%(self.home, self.link_alias(url))
                    print 'Writing %s'%_filepath
                    open(_filepath, "wb").write(data.content)
                except Exception,what:
                    print what


    def _download_css(self, url, data, depth):

        try:
            _content = data.content
        except Exception,what:
            print what
            return

        if depth>0:
            links = re.compile(r'url\([\'"]?(.*?)[\'"]?\)').findall(_content)
            _list = []
            templinks = []

            for link in links:
                slink = self.strip_link(link)

                if slink:
                    templinks.append(slink)

            links = templinks

            for link in set(links):
                _list.append(self.full_link(link, url))
                _content = _content.replace(link, self.link_alias(link)[1:].replace("assets", ".."))

            try:
                _filepath = '%s%s'%(self.home, self.link_alias(url))
                print 'Writing %s'%_filepath
                open(_filepath, "wb").write(_content)
            except Exception,what:
                print what

            if _list:
                self._download_files(multi_get(_list), depth - 1)


    def _create_dir(self):

        if os.path.exists(self.home):
            os.rename(self.home, '%s%s'%(self.home, time.time()))

        try:
            os.mkdir(self.home)
            os.mkdir(self.home + '/assets')
            os.mkdir(self.home + '/assets/js')
            os.mkdir(self.home + '/assets/css')
            os.mkdir(self.home + '/assets/img')
        except Exception,what:
            print what


    def _get_links_from_content(self, content):
        links = re.compile(r'<link[^>]*href=(.*?)[ >]', re.I).findall(content)
        links.extend( re.compile(r'<script[^>]*src=(.*?)[ >]',re.I).findall(content))
        links.extend( re.compile(r'<img[^>]*src=(.*?)[ >]',re.I).findall(content))
        return self._get_strip_links(links)


    def _get_strip_links(self, links):

        _templinks = []

        for link in links:
            slink = self.strip_link(link)

            if slink:
                _templinks.append(slink)

        return _templinks


    def _get_fullpath_links(self, links, content):

        _templinks = []

        for link in set(links):
            content = content.replace(link, self.link_alias(link)[1:])
            content = content.replace(u'charset=gb2312', 'charset=utf-8')
            content = content.replace(u'charset=GB2312', 'charset=utf-8')
            content = content.replace(u'charset=gbk', 'charset=utf-8')
            content = content.replace(u'charset=GBK', 'charset=utf-8')
            _templinks.append(self.full_link(link))

        return _templinks, content


def main():
    parser = OptionParser()
    parser.add_option("-d", "--dist", dest="dist", help="download dir", metavar="dist")
    parser.add_option("-u", "--url", dest="url", help="write report to URL", metavar="URL")
    parser.add_option("-f", "--file", dest="filename", help="write report to FILE", metavar="FILE")
    parser.add_option("-m", "--mirror", action="store_false", dest="mirror", default=True, help="don't print status messages to stdout")
    parser.add_option("-q", "--quiet", action="store_false", dest="verbose", default=True, help="don't print status messages to stdout")

    (options, args) = parser.parse_args()
    print options, type(options)
    r = multi_get([options.url])
    _copyer = Copyer(r[0])

if __name__ == '__main__':
    main()
    # r = multi_get([sys.argv[1]])
    # _copyer = Copyer(r[0])
