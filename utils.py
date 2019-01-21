import os
import os.path
import dateutil
import bs4
import base64

import dash_html_components

unknowns = ['autoplay', 'allow', 'align', 'border', 'frameborder', 'imageanchor']

def listBlogs(path):
    targets = []
    for e in os.scandir(path):
        for v in ['texts', 'images', 'answers', 'links']:
            if os.path.isfile(os.path.join(e.path, f'{v}.txt')) or os.path.isfile(os.path.join(e.path, f'{v}.json')):
                targets.append(e.name)
                break
    return targets

def loadEntries(blogPath, entryType):
    entryPath = os.path.join(blogPath, entryType + '.txt')

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

class Entry(object):
    def __init__(self, dat):
        self.dat = dat
        self.localizedHTML = None

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
        return tuple([t for t in self.get('Tags', '').strip().split(', ') if len(t) > 0])

    @property
    def date(self):
        return dateutil.parser.parse(self['Date'])

def encode_image(path):
    extension = path.split('.')[-1]
    with open(path, 'rb') as f:
        return 'data:image/{};base64,{}'.format(extension,base64.b64encode(f.read()).decode('utf-8'))
        S

def filterAttributes(a):
    ret = {}
    for k, v in a.items():
        if k == 'class':
            k = 'className'
        elif k in unknowns:
            continue
        ret[k] = v
    return ret

def toDashHTML(t):
    children = []
    if isinstance(t, bs4.NavigableString):
        return str(t)
    else:
        for c in t.children:
            children.append(toDashHTML(c))
    return getattr(dash_html_components, t.name.title(), dash_html_components.Div)(children, **filterAttributes(t.attrs))
