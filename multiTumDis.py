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

    def __call__(self, property, *args):
        self.writeQueue.put((property, *args))
        return self.getQue()

    def __repr__(self):
        return f"<BackendManager {self.path} with {len(self.names)} blogs>"

    def loadBlog(self, blogName):
        self.currentBlogInfo = self('loadBlog', blogName)

    def currentHTML(self):
        return self('getHTML',
                     self.currentBlogInfo['blogName'],
                     self.currentBlogInfo['postType'],
                     self.currentBlogInfo['postTag'],
                     self.currentBlogInfo['postIndex'],
                     )

    def startDisplay(self, startingBlog = None):
        if startingBlog is None:
            startingBlog = self.names[random.randint(0, len(self.names) - 1)]
        logging.info(f"Starting display with: {startingBlog}")
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
        return self.blogs['blogName'].setupInfoDict()

    def getHTML(self, blogName, postType, postTag, postIndex):
        return self.blogs['blogName'].getPostHTML(postType, postTag, postIndex)

    def runTask(self, task, *args):
        logging.info(f"Running: {task}({args})")
        try:
            f = getattr(self, task)
            ret = f(*args)
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
        self.postTypes = self.getPostTypes()
        #self.currentType = 'texts' if 'texts' in self.postTypes else self.postTypes[0]
        self.tags = {}
        self.posts = {}
        self.images = {}

    def getPostTypes(self):
        pTypes = []
        for e in os.scandir(self.path):
            if e.name.endswith('.txt') and not e.name.startswith('video'):
                pTypes.append(e.name.split('.')[0])
        return tuple(sorted(pTypes))

    def getTypeEntries(self, postType):
        if postType not in self.posts:
            self.posts[postType] = utils.loadEntries(self.path, postType)
        return self.posts[postType]

    def genTypeTagsDict(self, postType):
        if postType not in self.tags:
            typeTags = {}
            for i,e in enumerate(self.getTypeEntries(postType)):
                for t in e.tags:
                    try:
                        typeTags[t].append(e)
                    except KeyError:
                        typeTags[t] = [e]
            self.tags[postType] = typeTags
        return self.tags[postType]

    def getPostHTML(self, postType, postTag, postIndex):
        if postTag is None:
            entry = self.getTypeEntries(postType)[postIndex]
        else:
            entry = self.genTypeTagsDict(postType)[postTag][postIndex]
        if entry.localizedHTML is None:
            entry.localizedHTML= self.localizeHTML(entry.html)
        return entry.localizedHTML 

    def __repr__(self):
        return f"<Blog {self.name} {self.postTypes}>"

    def _join(self, entry):
        return os.path.join(self.path, entry)

    def getSortedTags(self, postType, withCounts = True):
        if withCounts:
            return tuple([(len(e), t) for t, e in sorted(self.genTypeTagsDict(postType).items(), key = lambda x: len(x[1]), reverse = True)])
        else:
            return tuple([t for t, e in sorted(self.genTypeTagsDict(postType).items(), key = lambda x: len(x[1]), reverse = True)])

    def setupInfoDict(self):
        infosDict =  {
            'blogName' : self.name,
            'postTypes' : self.postTypes,
            'postType' : 'texts' if 'texts' in self.postTypes else self.postTypes[0],
            'postTag' : None,
            'postIndex' : 0,
        }
        infosDict['typeTags'] = self.getSortedTags(infosDict['postType'], withCounts = False)
        infosDict['numPosts'] = len(self.genTypeTagsDict(infosDict['postType']))
        return infosDict

    def updateImage(self, img):
        srcName = os.path.basename(img.get('src'))
        if srcName in self.images:
            return self.images[srcName]
        testPath = self._join(srcName)
        if os.path.isfile(testPath):
            self.images[srcName] = utils.encode_image(testPath)
            return self.images[srcName]
        else:
            testPath2 = sizedRE.sub('_1280.', srcName)
            if os.path.isfile(testPath2):
                self.images[srcName] = utils.encode_image(testPath2)
                return self.images[srcName]
            if os.path.isfile(testPath):
                i.replaceWith(soup.new_tag("img", src=encode_image(testPath), **{"width" : i.get('width')}))
        return None

    def localizeHTML(self, target):
        target = str(target)
        soup = bs4.BeautifulSoup(target, 'lxml')
        for i in soup.findAll('img'):
            newImg = self.updateImage(i)
            if newImg is not None:
                i.replaceWith(soup.new_tag("img", src=newImg, **{"width" : i.get('width')}))
        return utils.toDashHTML(soup.body)
