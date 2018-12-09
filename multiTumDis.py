import os
import os.path
import re
import time
import random
import base64
import json
import multiprocessing
import queue

import collections.abc

import bs4
import dateutil.parser
import dash_html_components as html

import utils

sizedRE = re.compile(r'_\d\d\d\d?[.]')

tumblrsPath = '../blogs/'

unknowns = ['autoplay', 'allow', 'align', 'border', 'frameborder', 'imageanchor']


class BackendManager(object):
    def __init__(self, path = tumblrsPath):
        self.path = path

        self.writeQueue = multiprocessing.Queue()
        self.readQueue = multiprocessing.Queue()


        self.TumblrAccounts = MultiCollection(self.writeQueue, self.readQueue, self.path)

        self.TumblrAccounts.start()
        isReady = self.readQueue.get()
        if isReady != 'ready':
            raise RuntimeError(f"Worker had problems starting up: isReady {isReady}")

        self.names = self('getNames')

        print(f"Worker started with: {len(self.names)} accounts found")

    def __call__(self, property, *args, **kwargs):
        self.writeQueue.put((property, args, kwargs))

        return self.getQue()

    def getQue(self):
        ret = self.readQueue.get()
        if ret == 'ERROR':
            raise RuntimeError("Error encountered in worker")
        return ret

    def getTags(self, account):
        return self

    def end(self):
        print("Ending worker")
        ended = self('end')
        if ended != 'done':
            raise RuntimeError(f"Something weird happend when quitting: {ended}")
        self.TumblrAccounts.join()

    def __del__(self):
        if self.TumblrAccounts.is_alive():
            self.end()



class MultiCollection(multiprocessing.Process):
    def __init__(self, inputQ, outputQ, path):
        super().__init__()
        self.daemon = False
        self.inputQ = inputQ
        self.outputQ = outputQ
        self.path = path

        self.names = utils.listAccounts(self.path)

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
        print(f"finding new task, in queue: {self.inputQ.qsize()}, out queue: {self.outputQ.qsize()}")
        time.sleep(.5)
        return None

    def getNames(self, *args):
        print('getname', args)
        return self.names

    def runTask(self, task, *args, **kwargs):
        print(f"Running: ({task} {args} {kwargs})")
        try:
            f = getattr(self, task)
            ret = f(*args, **kwargs)
        except AttributeError:
            raise RuntimeError(f"Bad command passed: {task}")
        self.putQue(ret)

    def run(self):
        print(f"Starting run with {self.name} for {self.path}")
        self.outputQ.put("ready")
        try:
            while True:
                newTask = self.checkQue()
                print(f"New task: {newTask}")
                if not newTask:
                    newTask = self.findNewTask()
                elif newTask[0] == 'end':
                    print("end received, exiting")
                    self.putQue('done')
                    break
                else:
                    print(f"task received: {newTask}")
                    self.runTask(*newTask)
        except Exception as e:
            print("Error occured in worker thread")
            print(e)
            self.putQue("ERROR")
            raise
