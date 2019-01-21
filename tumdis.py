import os
import os.path
import re
import time
import random
import base64
import json

import collections.abc

import bs4
import dateutil.parser
from IPython.core.display import display
from ipywidgets import widgets, HBox, VBox

import dash_html_components as html

sizedRE = re.compile(r'_\d\d\d\d?[.]')

tumblrsPath = '../blogs/'

class DashDis(object):
    def __init__(self, path = tumblrsPath):
        self.path = path
        self.AC = AccountCollection(path, inDash = True)
        self.A = self.AC[random.randint(0, len(self.AC))]

class TumDisplay(object):
    def __init__(self, path = tumblrsPath):
        self.path = path
        self.AC = AccountCollection(path)
        self.A = self.AC[random.randint(0, len(self.AC))]


        self.accountSelector  = widgets.Dropdown(
                    options=self.AC.names,
                    value=self.A.name,
                    description='Account:',
                    )

        self.tagsSelector = widgets.Dropdown(
            options=[f'{len(self.A)} None'] + self.A.sortedTags(count = True),
            value=f'{len(self.A)} None',
            description='tags:',
        )

        self.typesSelector = widgets.RadioButtons(
                options=self.A.postTypes,
                value = self.A.currentType,
                description='Post type:',
        )

        self.postSlider = widgets.IntSlider(min=0, max=len(self.A) - 1, value=0, description=str(len(self.A)) + ' posts')

        self.mainCaption = widgets.HTML(
            value=self.A(0)
        )

        self.nextButton = widgets.Button(description="Next")

        self.previousButton = widgets.Button(description="Previous")

        self.tagSearchEnable = widgets.Button(description="Enable tag search")

        self.globalTagSelector = widgets.RadioButtons(
                options=['None'],
                value = 'None',
                description='Global tag filter:',
                disabled = True,
                display = False,
        )

        self.controls = HBox([VBox([HBox([self.accountSelector, self.tagsSelector]), HBox([self.postSlider, self.previousButton, self.nextButton])]), self.typesSelector])


    def account_change(self, change):
        self.A = self.AC[self.accountSelector.value]
        self.A.currentTag = 'None'
        self.mainCaption.value = self.A(0)
        self.postSlider.value = 0
        self.postSlider.max=len(self.A) - 1
        self.postSlider.description = str(len(self.A)) + ' posts'
        self.tagsSelector.options= [f'{len(self.A)} None'] + self.A.sortedTags(count = True)
        self.tagsSelector.value = f'{len(self.A)} None'

        self.typesSelector.options = self.A.postTypes
        self.typesSelector.value = 'texts'

    def tag_change(self, change):
        self.A.currentTag = ' '.join(self.tagsSelector.value.split(' ')[1:])
        self.mainCaption.value = self.A(0)
        self.postSlider.value = 0
        self.postSlider.max=len(self.A) - 1
        self.postSlider.description = str(len(self.A)) + ' posts'

    def type_change(self, value):
        #if  self.typesSelector.value not in ['texts', 'images']:
        #    self.A.currentType = 'texts'
        #else:
        self.A.currentType = self.typesSelector.value
        self.tagsSelector.options= [f'{len(self.A)} None'] + self.A.sortedTags(count = True)
        self.tagsSelector.value = f'{len(self.A)} None'
        self.tag_change('None')

    def slider_change(self, change):
        self.mainCaption.value = self.A(self.postSlider.value)

    def go_next(self, b):
        if self.postSlider.value < len(self.A) - 1:
            self.postSlider.value += 1
        else:
            self.postSlider.value = 0
        self.mainCaption.value = self.A(self.postSlider.value)

    def go_previous(self, b):
        if self.postSlider.value > 0:
            self.postSlider.value -= 1
        else:
            self.postSlider.value = len(self.A) - 1
        self.mainCaption.value = self.A(self.postSlider.value)

    def enable_global_tags(self, b):
        self.tagSearchEnable.disabled = True
        self.tagSearchEnable.layout.display = False
        self.globalTagSelector.disabled = False
        self.globalTagSelector.layout.display = True

    def _ipython_display_(self):
        display(self.controls)
        time.sleep(.1)
        self.accountSelector.observe(self.account_change, names='value')

        self.tagsSelector.observe(self.tag_change, names='value')

        self.typesSelector.observe(self.type_change, names='value')

        self.postSlider.observe(self.slider_change, names='value')

        self.nextButton.on_click(self.go_next)
        self.previousButton.on_click(self.go_previous)

        self.tagSearchEnable.on_click(self.enable_global_tags)

        display(self.mainCaption, self.controls)

    def display(self):
        return display(self)

class AccountCollection(collections.abc.Mapping):
    def __init__(self, path = tumblrsPath, inDash = False):
        self.path = path
        self.names = listAccounts(self.path)
        self.loaded = {}
        self.inDash = inDash

    def __getitem__(self, key):
        if isinstance(key, int):
            return self[self.names[key]]
        if key not in self.loaded:
            try:
                self.loaded[key] = Account(key, inDash = self.inDash)
            except FileNotFoundError:
                raise KeyError
        return self.loaded[key]

    def __iter__(self):
        for n in self.names:
            yield n
        return

    def __len__(self):
        return len(self.names)

    def __repr__(self):
        return f"< AccountCollection {len(self)} accounts {len(self.loaded)} loaded >"

    def load_all(self):
        for n in self:
            a = self[n]

    def tags(self):
        tags = {}
        for n in self:
            a = self[n]
            for t in a.sortedTags()[:20]:
                try:
                    tags[t] += len(a.tags[t])
                except KeyError:
                    tags[t] = len(a.tags[t])
        return tags

class Entry(object):
    def __init__(self, dat):
        self.dat = dat

    def __getitem__(self, key):
        return self.dat[key]

    def get(self, key, *args, **kwargs):
        return self.dat.get(key,*args, **kwargs)

    def _repr_html_(self):
        return self.html

    def __str__(self):
        return self['text']

    @property
    def html(self):
        s = ''
        if 'Photo url' in self.dat:
            if len(self.get('text', '').split('<img ')) < 3:
                s += f"<div class=\"image\"><img src=\"{self.get('Photo url')}\" align=\"middle\" width=\"600px\" ></div>\n"
                s += f"<div class=\"text\"><h1>{self.get('Title', '')}</h1>\n{self.get('text', '')}<\div>"
                return f"<div class=\"row\">{s}<\div>"
            else:
                s += f"<div ><img src=\"{self.get('Photo url')}\" align=\"middle\" width=\"600px\" ></div>\n"
        if 'Title' in self.dat:
            s = f"<h1>{self.get('Title', '')}</h1>\n" + s
        s += self.get('text', '')
        return f"<div class=\"main\">{s}<\div>"

    @property
    def tags(self):
        return [t for t in self.get('Tags', '').strip().split(', ') if len(t) > 0]

    @property
    def date(self):
        return dateutil.parser.parse(self['Date'])

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

def listAccounts(path = tumblrsPath):
    targets = []
    for e in os.scandir(path):
        for v in ['texts', 'images', 'answers', 'links']:
            if os.path.isfile(os.path.join(e.path, f'{v}.txt')) or os.path.isfile(os.path.join(e.path, f'{v}.json')):
                targets.append(e.name)
                break
    return targets

class Account(object):
    def __init__(self, name, inDash = False):
        self.name = name
        self.path = os.path.join(tumblrsPath, name)
        self.inDash = inDash
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
        return f"< Account {self.name} {len(self)} entries >"

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
