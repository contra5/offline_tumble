import dash
from dash.dependencies import Input, Output, State
import dash_core_components as dcc
import dash_html_components as html

import bs4
import numpy as np

import os
import os.path
import json
import random
import webbrowser
import logging

import multiTumDis
import dash_reusable_components as drc

class MultiDashFront(multiTumDis.BackendManager):
    def __init__(self, tumblrsPath):
        super().__init__(tumblrsPath)
        self.app = dash.Dash('tumdis')

        self.app.layout = self.genMainNav()

        self.addStateCallbacks()

        self.addUpdateCallbacks()

        self.addDrawCallbacks()

        self.addButtonCallbacks()

    def addButtonCallbacks(self):
        def buttonPress(next_presses, previous_presses, intialState, currentLoc, maxVal):
            postIndex, num_nexts, num_prevs  = intialState
            if next_presses > num_nexts:
                postIndex = (currentLoc + 1) % maxVal
                num_nexts += 1
            else:
                postIndex = (currentLoc - 1) % maxVal
                num_prevs += 1
            return (postIndex, num_nexts, num_prevs)

        self.app.callback(
                        Output('state_container', 'data-buttons'),
                        inputs = [
                                Input('next_button', 'n_clicks'),
                                Input('previous_button', 'n_clicks'),
                        ],
                        state = [
                                State('state_container', 'data-buttons'),
                                State('post_selector', 'value'),
                                State('post_selector', 'max'),
                                ],
                        )(buttonPress)

    def addDrawCallbacks(self):
        self.addDraw('tumblr_entry', 'children', self.currentHTML, ('blog', 'type', 'tag', 'index'))

        self.addDraw('type_selector', 'options', self.genTypesDict, ('blog',))
        self.addDraw('type_selector', 'value', lambda : self['data-postType'], ('blog',))
        self.addDraw('tags_selector', 'options', lambda : self.genCurrentTagOptions(withNum = True), ('blog', 'type'))
        self.addDraw('tags_selector', 'value', lambda : self['data-postTag'], ('blog', 'type'))
        self.addDraw('current_tags', 'options', lambda : self.genCurrentTagOptions(withNum = False), ('blog', 'type', 'tag', 'index'))
        self.addDraw('current_tags', 'value', lambda : self['data-postTags'], ('blog', 'type', 'tag', 'index'))
        self.addDraw('post_selector', 'max', lambda : self['data-maxIndex'], ('blog', 'type', 'tag'))
        self.addDraw('post_selector', 'marks', self.genPostSelectorMarks, ('blog', 'type', 'tag'))
        self.addDraw('post_selector', 'value', lambda : self['data-postIndex'], ('blog', 'type', 'tag', 'button'))
        """
        def positionUpdate(button_state, *otherStates):
            if button_state[2] != self['data-postIndex']:
                return button_state[2]

        self.app.callback(
                    Output('post_selector', 'value'),
                    inputs = [Input('state_container', 'data-buttons')]
                    )(positionUpdate)
        """
    def addDraw(self, outputName, outputValue, func, inputTargets):
        def drawFunc(*updateVals):
            return func()
        inputsMap ={
            'blog' : Input('state_container','data-updateBlog'),
            'type' : Input('state_container','data-updateType'),
            'tag' : Input('state_container','data-updateTag'),
            'index' : Input('state_container','data-updateIndex'),
            'button' : Input('state_container','data-updateButtonIndex'),
        }

        self.app.callback(
                        Output(outputName, outputValue),
                        inputs=[inputsMap[i] for i in inputTargets],
                        )(drawFunc)

    def addUpdateCallbacks(self):
        def changeBlog(new_blogName, current_count):
            self.loadBlog(new_blogName)
            logging.debug(f"Update blog: {current_count + 1} loading new blog: {new_blogName}")
            return current_count + 1

        def changePostType(new_postType, current_count):
            self['data-postType'] = new_postType
            self['data-postTag'] = 'None'
            self['data-postIndex'] = 0
            self.currentBlogInfo.update(self.getDerivedInfos())
            logging.debug(f"Update postType: {current_count + 1}")
            return current_count + 1

        def changePostTag(new_postTag, current_count):
            self['data-postTag'] = new_postTag
            self['data-postIndex'] = 0
            self.currentBlogInfo.update(self.getDerivedInfos())
            logging.debug(f"Update postTag: {current_count + 1}")
            return current_count + 1

        def changePostIndex(new_postIndex, current_count):
            self['data-postIndex'] = new_postIndex
            self.currentBlogInfo.update(self.getDerivedInfos())
            logging.debug(f"Update postIndex: {current_count + 1}")
            return current_count + 1

        def changePostButtonIndex(new_buttonsPresses, current_count):
            self['data-postIndex'] = new_buttonsPresses[0]
            self.currentBlogInfo.update(self.getDerivedInfos())
            logging.debug(f"Update PostButtonIndex: {current_count + 1}")
            return current_count + 1

        self.app.callback(
                Output('state_container', 'data-updateBlog'),
                inputs=[Input('state_container','data-blogName')],
                state=[State('state_container', 'data-updateBlog')],
                )(changeBlog)

        self.app.callback(
                Output('state_container', 'data-updateType'),
                inputs=[Input('state_container','data-postType')],
                state=[State('state_container', 'data-updateType')],
                )(changePostType)

        self.app.callback(
                Output('state_container', 'data-updateTag'),
                inputs=[Input('state_container','data-postTag')],
                state=[State('state_container', 'data-updateTag')],
                )(changePostTag)

        self.app.callback(
                Output('state_container', 'data-updateIndex'),
                inputs=[Input('state_container','data-postIndex')],
                state=[State('state_container', 'data-updateIndex')],
                )(changePostIndex)

        self.app.callback(
                Output('state_container', 'data-updateButtonIndex'),
                inputs=[Input('state_container','data-buttons')],
                state=[State('state_container', 'data-updateButtonIndex')],
                )(changePostButtonIndex)

    def addStateCallbacks(self):
        self.addState('data-blogName', 'blog_selector')
        self.addState('data-postType', 'type_selector')
        self.addState('data-postTag', 'tags_selector')
        self.addState('data-postIndex', 'post_selector')

    def addState(self, valueName, selectorName):

        outputDep = Output('state_container', valueName)
        inputDep = Input(selectorName, 'value')

        def stateChange(new_val):
            logging.info(f"User changed {selectorName} to {new_val}")
            return new_val

        self.app.callback(outputDep, inputs=[inputDep])(stateChange)

    def genMainNav(self):
        dataDict = self.currentBlogInfo.copy()
        dataDict['data-buttons'] = (0,0,0)
        for k in ['data-updateIndex', 'data-updateTag', 'data-updateType', 'data-updateBlog', 'data-updateButtonIndex']:
            dataDict[k] = 0
        nav = html.Div([
            html.Div(id='state_container',
                        style={'display': 'none'},
                        **dataDict,
                    ),
            html.Div([
                drc.NamedDropdown(
                    name = 'Blog',
                    id = 'blog_selector',
                    options=[{'value' : n, 'label' : n} for n in self.names],
                    value=self['data-blogName'],
                ),
                drc.NamedDropdown(
                    name = 'Tags',
                    id = 'tags_selector',
                    options=self.genCurrentTagOptions(withNum = True),
                    value='None',
                ),
                drc.NamedSlider(
                    name = 'Post',
                    id = 'post_selector',
                    min = 0,
                    max = self['data-maxIndex'],
                    step = 1,
                    value = 0,
                    marks = self.genPostSelectorMarks(),
                    updatemode = 'mouseup',
                ),
                drc.NamedRadioItems(
                    name = 'Type',
                    id = 'type_selector',
                    options = self.genTypesDict(),
                    value = self['data-postType'],
                ),
                html.Button(id='previous_button', n_clicks=0, children='Previous'),
                html.Button(id='next_button', n_clicks=0, children='Next'),
                drc.NamedDropdown(
                    name = 'Current Tags',
                    id = 'current_tags',
                    options=self.genCurrentTagOptions(withNum = False),
                    value=self['data-postTag'],
                    multi = True,
                ),
            ], className = 'sidenav'),
            html.Div([
                self.currentHTML(),
            ], id = 'tumblr_entry')
        ])
        return nav

    def run(self, debug = True):
        #webbrowser.open('http://127.0.0.1:8050/', new=2, autoraise=False)
        self.app.run_server(debug=debug)

def main():
    logging.basicConfig(
                    format='%(asctime)s Dash %(levelname)s: %(message)s',
                    datefmt='%I:%M:%S',
                    level=logging.DEBUG)
    App = MultiDashFront( '../blogs/')
    App.run()

if __name__ == '__main__':
    main()
