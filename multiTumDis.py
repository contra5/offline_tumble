import os
import os.path
import re
import time
import random
import base64
import json
import multiprocessing
import queue

import logging

import collections.abc

import bs4
import dateutil.parser
import dash_html_components as html

import utils

sizedRE = re.compile(r'_\d\d\d\d?[.]')

tumblrsPath = '../blogs/'

unknowns = ['autoplay', 'allow', 'align', 'border', 'frameborder', 'imageanchor']

logging.basicConfig(
                format='%(asctime)s %(levelname)s: %(message)s',
                datefmt='%I:%M:%S',
                level=logging.INFO)


class BackendManager(object):
    def __init__(self, path = tumblrsPath):
        self.path = path

        self.writeQueue = multiprocessing.Queue()
        self.readQueue = multiprocessing.Queue()


        self.currentBlogInfo = None

        self.TumblrBlogs = MultiCollection(self.writeQueue, self.readQueue, self.path)

        self.TumblrBlogs.start()
        isReady = self.readQueue.get()
        if isReady != 'ready':
            raise RuntimeError(f"Worker had problems starting up: isReady {isReady}")

        self.names = self('getNames')

        logging.info(f"Worker started with: {len(self.names)} blogs found")

    def __call__(self, property, *args, **kwargs):
        self.writeQueue.put((property, args, kwargs))
        return self.getQue()

    def __repr__(self):
        return f"<BackendManager {self.path} with {len(self.names)} blogs>"

    def loadBlog(self, blogName):
        self.currentBlogInfo = self('loadBlog', blogName)

    def currentHTML(self):
        return self('getHTML',
                     blogName = self.currentBlogInfo['blogName'],
                     postType = self.currentBlogInfo['postType'],
                     postTag = self.currentBlogInfo['postTag'],
                     postIndex = self.currentBlogInfo['postIndex'],
                     )

    def startDisplay(self, startingBlog = None):
        if startingBlog is None:
            startingBlog = self.names[random.randint(0, len(self.names) - 1)]

        self.loadBlog(startingBlog)

        return self.currentHTML()

    def getQue(self):
        ret = self.readQueue.get()
        if ret == 'ERROR':
            raise RuntimeError("Error encountered in worker")
        return ret

    def getTags(self, blog):
        return self

    def end(self):
        logging.info("Ending worker")
        ended = self('end')
        if ended != 'done':
            raise RuntimeError(f"Something weird happend when quitting: {ended}")
        self.TumblrBlogs.join()

    def __del__(self):
        if self.TumblrBlogs.is_alive():
            self.end()

class MultiCollection(multiprocessing.Process):
    def __init__(self, inputQ, outputQ, path):
        super().__init__()
        self.daemon = False
        self.inputQ = inputQ
        self.outputQ = outputQ
        self.path = path

        self.names = utils.listBlogs(self.path)

        self.blogs = {}

    def checkQue(self):
        try:
            task = self.inputQ.get_nowait()
        except queue.Empty:
            return False
        else:
            return task

    def putQue(self, dat):
        self.outputQ.put(dat)

    def findNewTask(self):
        logging.info(f"finding new task, in queue: {self.inputQ.qsize()}, out queue: {self.outputQ.qsize()}")
        time.sleep(.5)
        return None

    def getNames(self, *args):
        logging.info(f'getname {args}')
        return self.names

    def loadBlog(self, blogName):
        if blogName not in self.blogs:
            self.blogs['blogName'] = Blog(os.path.join(self.path, blogName), blogName)
        return self.blogs['blogName'].getInfo()

    def getHTML(self, *, blogName, postType, postTag, postIndex):
        return self.blogs['blogName'].getPostHTML(postType, postTag, postIndex)

    def runTask(self, task, *args, **kwargs):
        logging.info(f"Running: ({task} {args} {kwargs})")
        try:
            f = getattr(self, task)
            ret = f(*args, **kwargs)
        except AttributeError:
            raise RuntimeError(f"Bad command passed: {task}")
        self.putQue(ret)

    def run(self):
        logging.info(f"Starting run with {self.name} for {self.path}")
        self.outputQ.put("ready")
        try:
            while True:
                newTask = self.checkQue()
                logging.info(f"New task: {newTask}")
                if not newTask:
                    newTask = self.findNewTask()
                elif newTask[0] == 'end':
                    logging.info("end received, exiting")
                    self.putQue('done')
                    break
                else:
                    logging.info(f"task received: {newTask}")
                    self.runTask(*newTask)
        except Exception as e:
            logging.error("Error occured in worker thread")
            logging.error(e)
            self.putQue("ERROR")
            raise


class Blog(object):
    def __init__(self, path, name):
        self.name = name
        self.path = path
        self.postTypes = [e.name.split('.')[0] for e in os.scandir(self.path) if (e.name.endswith('.txt') or e.name.endswith('.json')) and not e.name.startswith('video')]
        self.currentType = 'texts' if 'texts' in self.postTypes else self.postTypes[0]
        self.posts = {self.currentType : loadEntries(self._join(self.currentType)) }
        self._tags = {}

        self.currentTag = 'None'

    @property
    def entries(self):
        if self.currentType not in self.posts:
            self.posts[self.currentType] = loadEntries(self._join(self.currentType))
        return self.posts[self.currentType]

    @property
    def tags(self):
        if self.currentType not in self._tags:
            tags = {}
            for i,e in enumerate(self.entries):
                for t in e.tags:
                    try:
                        tags[t].append(e)
                    except KeyError:
                        tags[t] = [e]
            self._tags[self.currentType] = tags
        return self._tags[self.currentType]

    def __len__(self):
        return len(self.currentTagValues)

    def __repr__(self):
        return f"< Blog {self.name} {len(self)} entries >"

    def __getitem__(self, key):
        return self.currentTagValues[key]

    def _join(self, entry):
        return os.path.join(self.path, entry)

    def __call__(self, key):
        return self.localizeHTML(self[key].html)

    def sortedTags(self, countTuple = False, count = False):
        if count:
            return [f"{len(e)} {t}" for t, e in sorted(self.tags.items(), key = lambda x: len(x[1]), reverse = True)]
        elif countTuple:
            return [(len(e), t) for t, e in sorted(self.tags.items(), key = lambda x: len(x[1]), reverse = True)]
        else:
            return [t for t, e in sorted(self.tags.items(), key = lambda x: len(x[1]), reverse = True)]

    @property
    def currentTagValues(self):
        if self.currentTag == 'None':
            return self.entries
        else:
            return self.tags[self.currentTag]

    def localizeHTML(self, target):
        #Sreturn target
        target = str(target)
        soup = bs4.BeautifulSoup(target, 'lxml')
        for i in soup.findAll('img'):
            srcName = os.path.basename(i.get('src'))
            testPath = self._join(srcName)
            if os.path.isfile(testPath):
                i.replaceWith(soup.new_tag("img", src=encode_image(testPath), **{"width" : i.get('width')}))
            else:
                testPath = sizedRE.sub('_1280.', srcName)
                if os.path.isfile(testPath):
                    i.replaceWith(soup.new_tag("img", src=encode_image(testPath), **{"width" : i.get('width')}))
        if not self.inDash:
            return str(soup)
        else:
            dashed = toDashHTML(soup.body)
            return dashed

def loadEntries(entryPath):
    if not os.path.isfile(entryPath):
        if os.path.isfile(entryPath + '.json'):
            entryPath = entryPath + '.json'
        elif os.path.isfile(entryPath + '.txt'):
            entryPath = entryPath + '.txt'
        else:
            raise FileNotFoundError(entryPath)
    entryType, entryFormat = os.path.basename(entryPath).split('.')

    entries = []
    with open(entryPath, encoding = 'utf8') as f:
        entries = []
        dat = {}
        inBody = False
        for e in f:
            if inBody:
                if e.startswith('Tags:'):
                    k, *v = e.split(':')
                    dat[k] = ':'.join(v).strip()
                    inBody = False
                    entries.append(Entry(dat))
                    dat = {}
                else:
                    try:
                        dat['text'] += e
                    except KeyError:
                        dat['text'] = e
            elif len(e) == 1:
                pass
            else:
                k, *v = e.split(':')
                dat[k] = ':'.join(v).strip()
                if entryType == 'texts' and e.startswith('Title:'):
                    inBody = True
                elif entryType == 'images' and e.startswith('Photo caption:'):
                    inBody = True
                    dat['text'] = ':'.join(v).strip()
                elif entryType not in ['images', 'texts'] and e.startswith('Reblog name:'):
                    inBody = True
    return sorted(entries, key = lambda x : x.date, reverse = True)
