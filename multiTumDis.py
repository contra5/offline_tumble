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
import numpy as np
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
        self.startDisplay()

        logging.info(f"Worker started with: {len(self.names)} blogs found")

    def __call__(self, property, *args):
        self.writeQueue.put((property, *args))
        return self.getQue()

    def __getitem__(self, key):
        return self.currentBlogInfo[key]

    def __setitem__(self, key, value):
        self.currentBlogInfo[key] = value

    def __repr__(self):
        return f"<BackendManager {self.path} with {len(self.names)} blogs>"

    def loadBlog(self, blogName):
        self.currentBlogInfo = self('loadBlog', blogName)

    def currentHTML(self):
        return self('getHTML',
                     self['data-blogName'],
                     self['data-postType'],
                     self['data-postTag'],
                     self['data-postIndex'],
                     )

    def getDerivedInfos(self):
        return self('getDerivedInfos',
                    self['data-blogName'],
                    self['data-postType'],
                    self['data-postTag'],
                    self['data-postIndex'],
                    )

    def getCurrentMax(self):
        self['data-maxIndex'] = self('getMaxIndex',
                                    self['data-blogName'],
                                    self['data-postType'],
                                    self['data-postTag'],
                                    )
        return self['data-maxIndex']

    def getCurrentTags(self):
        return self('getPostTags',
                                    self['data-blogName'],
                                    self['data-postType'],
                                    self['data-postTag'],
                                    self['data-postIndex'],
                                    )

    def currentURL(self):
        return self('getURL',
                     self['data-blogName'],
                     self['data-postType'],
                     self['data-postTag'],
                     self['data-postIndex'],
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

    def genCurrentTagOptions(self, withNum = True):
        ret = [{'value' : 'None', 'label' : f'{self["data-maxIndex"]} None'}]
        for c, t in self('getBlogTags', self['data-blogName'], self['data-postType']):
            ret.append({
                'value' : t,
                'label' : f"{c} {t}" if  withNum else t,
            })
        return ret

    def genPostSelectorMarks(self):
        maxVal = self['data-maxIndex']
        if maxVal >= 10:
            return {int(i) : str(i) for i in np.linspace(0, maxVal , 10, dtype = int)}
        else:
            return {i : f"{i}" for i in range(maxVal)}

    def genTypesDict(self):
        return [{'value' : t, 'label' : t } for t in self['data-postTypes']]

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
            task = self.inputQ.get()
        except queue.Empty:
            return False
        else:
            return task

    def putQue(self, dat):
        self.outputQ.put(dat)

    def findNewTask(self):
        logging.debug(f"finding new task, in queue: {self.inputQ.qsize()}, out queue: {self.outputQ.qsize()}")
        #time.sleep(.5)
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

    def getDerivedInfos(self, blogName, postType, postTag, postIndex):
        return self.blogs['blogName'].getDerivedInfos(postType, postTag, postIndex)

    def getMaxIndex(self, blogName, postType, postTag):
        return len(self.blogs['blogName'].getEntries(postType, postTag)) - 1

    def getPostTags(self, blogName, postType, postTag, postIndex):
        return self.blogs['blogName'].getPostTags(postType, postTag, postIndex)

    def getURL(self, blogName, postType, postTag, postIndex):
        return self.blogs['blogName'].getPostURL(postType, postTag, postIndex)

    def getBlogTags(self, blogName, postType):
        return self.blogs['blogName'].getSortedTags(postType, withCounts = True)

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
                logging.debug(f"New task: {newTask}")
                if not newTask:
                    newTask = self.findNewTask()
                elif newTask[0] == 'end':
                    logging.info("end received, exiting")
                    self.putQue('done')
                    break
                else:
                    #logging.info(f"task received: {newTask}")
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

    def getEntries(self, postType, postTag):
        if postTag == 'None':
            entries = self.getTypeEntries(postType)
        else:
            entries = self.genTypeTagsDict(postType)[postTag]
        return entries

    def getPostHTML(self, postType, postTag, postIndex):
        entry = self.getEntries(postType, postTag)[postIndex]
        if entry.localizedHTML is None:
            entry.localizedHTML= self.localizeHTML(entry.html)
        return entry.localizedHTML

    def getPostURL(self, postType, postTag, postIndex):
        entry = self.getEntries(postType, postTag)[postIndex]
        return entry.get('Post url', '')

    def getPostTags(self, postType, postTag, postIndex):
        entry = self.getEntries(postType, postTag)[postIndex]
        return entry.tags

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
            'data-blogName' : self.name,
            'data-postTypes' : self.postTypes,
            'data-postType' : 'texts' if 'texts' in self.postTypes else self.postTypes[0],
            'data-postTag' : 'None',
            'data-postIndex' : 0,
        }
        infosDict.update(self.getDerivedInfos(infosDict['data-postType'],infosDict['data-postTag'],infosDict['data-postIndex']))
        return infosDict

    def getDerivedInfos(self, postType, postTag, postIndex):
        infosDict = {}
        infosDict['data-typeTags'] = self.getSortedTags(postType, withCounts = False)
        infosDict['data-maxIndex'] = len(self.getEntries(postType, postTag)) - 1
        infosDict['data-postTags'] = self.getPostTags(postType, postTag, postIndex)
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
