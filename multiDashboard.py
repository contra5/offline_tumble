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

logging.basicConfig(
                format='%(asctime)s Dash %(levelname)s: %(message)s',
                datefmt='%I:%M:%S',
                level=logging.INFO)


tumblrsPath = '../blogs/'
if __name__ == '__main__':
    app = dash.Dash(__name__)

    Backend = multiTumDis.BackendManager(tumblrsPath)

    dataDict = Backend.currentBlogInfo.copy()
    dataDict['data-buttons'] = (0,0,0)
    dataDict['data-update'] = 0

    app.layout = html.Div([
        html.Div(id='state_container',
                    style={'display': 'none'},
                    **dataDict,
                ),
        html.Div([
            drc.NamedDropdown(
                name = 'Blog',
                id = 'blog_selector',
                options=[{'value' : n, 'label' : n} for n in Backend.names],
                value=Backend['data-blogName'],
            ),
            drc.NamedDropdown(
                name = 'Tags',
                id = 'tags_selector',
                options=Backend.genCurrentTagOptions(withNum = True),
                value='None',
            ),
            drc.NamedSlider(
                name = 'Post',
                id = 'post_selector',
                min = 0,
                max = Backend['data-maxIndex'],
                step = 1,
                value = 0,
                marks = Backend.genPostSelectorMarks(),
                updatemode = 'mouseup',
            ),
            drc.NamedRadioItems(
                name = 'Type',
                id = 'type_selector',
                options = Backend.genTypesDict(),
                value = Backend['data-postType'],
            ),
            html.Button(id='previous_button', n_clicks=0, children='Previous'),
            html.Button(id='next_button', n_clicks=0, children='Next'),
            drc.NamedDropdown(
                name = 'Current Tags',
                id = 'current_tags',
                options=Backend.genCurrentTagOptions(withNum = False),
                value=Backend['data-postTag'],
                multi = True,
            ),
        ], className = 'sidenav'),
        html.Div([
            Backend.currentHTML(),
        ], id = 'tumblr_entry')
    ])

    #State

    @app.callback(
        Output('state_container', 'data-blogName'),
        [Input('blog_selector', 'value'),],
    )
    def update_blog_value(new_account):
        logging.info(f"new blog {new_account}")
        return new_account

    @app.callback(
        Output('state_container', 'data-postType'),
        [Input('type_selector', 'value'),],
    )
    def update_post_value(new_type):
        logging.info(f"new type {new_type}")
        return new_type

    @app.callback(
        Output('state_container', 'data-postTag'),
        [Input('tags_selector', 'value')],
    )
    def update_tag_value(new_tag):
        logging.info(f"new tag {new_tag}")
        return new_tag

    @app.callback(
        Output('state_container', 'data-buttons'),
        [Input('next_button', 'n_clicks'),
        Input('previous_button', 'n_clicks'),
        Input('state_container', 'data-maxIndex'),
        Input('state_container', 'data-postType'),
        Input('state_container', 'data-postTag'),],
        [State('state_container', 'data-buttons'),
        State('state_container', 'data-postIndex')],
    )
    def update_post_index(next_presses, previous_presses, maxIndex, postType, postTag, button_state, currentIndex):
        postIndex, num_nexts, num_prevs  = button_state
        logging.info("post update press: {} {} {}".format(next_presses, previous_presses, button_state))
        postIndex = currentIndex
        if next_presses > num_nexts:
            num_nexts = num_nexts + 1
            if postIndex < maxIndex:
                postIndex =  postIndex + 1
            else:
                postIndex = 0
        elif previous_presses > num_prevs:
            num_prevs = num_prevs + 1
            if postIndex > 0:
                postIndex = postIndex - 1
            else:
                postIndex =  maxIndex
        else:
            postIndex = 0
        return (postIndex, num_nexts, num_prevs)

    @app.callback(
        Output('state_container', 'data-postIndex'),
        [Input('post_selector', 'value'),],
    )
    def update_post_value(new_post):
        logging.info(f"new post {new_post}")
        return new_post

    #Draw
    @app.callback(
        Output('state_container', 'data-update'),
        [Input('state_container', 'data-blogName'),
        Input('state_container', 'data-postType'),
        Input('state_container', 'data-postTag'),
        Input('state_container', 'data-postIndex'),],
        [State('state_container', 'data-update')]
    )
    def update_internal_state(blogName, postType, postTag, postIndex, current_count):
        Backend['data-blogName'] = blogName
        Backend['data-postType'] = postType
        Backend['data-postTag'] = postTag
        Backend['data-postIndex'] = postIndex
        Backend['data-postTags'] = Backend.getCurrentTags()
        Backend['data-maxIndex'] = Backend.getCurrentMax()
        logging.info("updating: {} {}".format(current_count + 1, Backend.currentBlogInfo))
        return current_count + 1

    @app.callback(
        Output('tumblr_entry', 'children'),
        [Input('state_container', 'data-update')],
    )
    def update_output_div(current_count):
        logging.info(f"drawing: {current_count} {Backend['data-blogName']} {Backend['data-postType']} {Backend['data-postTag']} {Backend['data-postIndex']}")
        return Backend.currentHTML()

    #Options

    @app.callback(
        Output('type_selector', 'options'),
        [Input('state_container', 'data-update')],
    )
    def update_type_options(current_count):
        return Backend.genTypesDict()

    @app.callback(
        Output('tags_selector', 'options'),
        [Input('state_container', 'data-update')],
    )
    def update_tags_options(current_count):
        logging.info(f"tags updating: {current_count}")
        return Backend.genCurrentTagOptions()

    @app.callback(
        Output('current_tags', 'options'),
        [Input('state_container', 'data-update')],
    )
    def update_output_tag_options(current_count):
        logging.info(f"Draw tags: {current_count}")
        return  Backend.genCurrentTagOptions(withNum = False)

    @app.callback(
        Output('post_selector', 'max'),
        [Input('state_container', 'data-update')],
    )
    def update_post_max(current_count):
        return Backend['data-maxIndex']

    @app.callback(
        Output('post_selector', 'marks'),
        [Input('post_selector', 'max'),]
    )
    def update_post_marks(max):
        logging.info("marks updating" )
        return Backend.genPostSelectorMarks()

    #Values

    @app.callback(
        Output('type_selector', 'value'),
        [Input('state_container', 'data-update')],
    )
    def update_type_value(current_count):
        logging.info(f"reseting types")
        return Backend['data-postType']

    @app.callback(
        Output('tags_selector', 'value'),
        [Input('state_container', 'data-update')],
    )
    def update_tag_value(current_count):
        return Backend['data-postTag']

    @app.callback(
        Output('current_tags', 'value'),
        [Input('state_container', 'data-update')],
    )
    def update_output_tag_options(current_count):
        return Backend['data-postTags']
    """
    @app.callback(
        Output('post_selector', 'value'),
        [Input('state_container', 'data-buttons')],
    )
    def update_post_value(current_count):
        return Backend['data-postIndex']
    """

    #webbrowser.open('http://127.0.0.1:8050/', new=2)
    app.run_server(debug=True)
