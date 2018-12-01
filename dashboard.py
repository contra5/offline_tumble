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

import tumdis
import dash_reusable_components as drc


app = dash.Dash(__name__)

#app.config['suppress_callback_exceptions']=True


AC = tumdis.AccountCollection(inDash = True)

startingAccountName = AC[random.randint(0, len(AC) - 1)].name


#bad form, but works in single user system
num_nexts = 0
num_prevs = 0
current_post_num = 0

def genPostSelectorMarks(A):
    maxVal = len(A) - 1
    if maxVal >= 10:
        #vals =  {(i * maxVal) // 10 : f"{(i * maxVal) // 10}" for i in range(10)}
        #print(vals)
        return {int(i) : str(i) for i in np.linspace(0, maxVal , 10, dtype = int)}
    else:
        return {i : f"{i}" for i in range(maxVal)}


def genTagOptions(A, withNum = True):
    ret = [{'value' : 'None', 'label' : f'{len(A)} None'}]
    for c, t in A.sortedTags(countTuple = True):
        ret.append({
            'value' : t,
            'label' : f"{c} {t}" if  withNum else t,
        })
    return ret

def genTypesDict(A):
    return [{'value' : t, 'label' : t } for t in A.postTypes]

app.layout = html.Div([
    html.Div(id='state_container', style={'display': 'none'},
                **{'data-account' : startingAccountName,
                    'data-post' : 0,
                    'data-type' : 'texts',
                    'data-tag' : 'None',
                    'data-buttons' : (0, 0, 0)}),
    html.Div([
        drc.NamedDropdown(
            name = 'Account',
            id = 'account_selector',
            options=[{'value' : n, 'label' : n} for n in AC.names],
            value=startingAccountName,
        ),
        drc.NamedDropdown(
            name = 'Tags',
            id = 'tags_selector',
            options=genTagOptions(AC[startingAccountName]),
            value='None',
        ),
        drc.NamedSlider(
            name = 'Post',
            id = 'post_selector',
            min = 0,
            max = len(AC[startingAccountName]) - 1,
            step = 1,
            value = 0,
            marks = genPostSelectorMarks(AC[startingAccountName]),
            updatemode = 'mouseup',
        ),
        drc.NamedRadioItems(
            name = 'Type',
            id = 'type_selector',
            options = genTypesDict(AC[startingAccountName]),
            value = 'texts' if 'texts' in AC[startingAccountName].postTypes else AC[startingAccountName].postTypes[0],
        ),
        html.Button(id='previous_button', n_clicks=0, children='Previous'),
        html.Button(id='next_button', n_clicks=0, children='Next'),
        drc.NamedDropdown(
            name = 'Current Tags',
            id = 'current_tags',
            options=genTagOptions(AC[startingAccountName], withNum = False),
            value=AC[startingAccountName][0].tags,
            multi = True,
        ),
        html.Div(
            style={'margin': '10px 0px'},
            children=[
                html.P(
                    children='url:',
                    style={'margin-left': '3px'}
                ),
                html.Div(
                html.A(AC[startingAccountName][0].get('Post url', ''),
                    href=AC[startingAccountName][0].get('Post url', ''))
                    , id = 'post_url'),
            ]
        ),
    ], className = 'sidenav'),
    html.Div([
        AC[startingAccountName](0),
    ], id = 'tumblr_entry')
])


#State

@app.callback(
    Output('state_container', 'data-account'),
    [Input('account_selector', 'value'),],
)
def update_post_value(new_account):
    print(f"new_account {new_account}")
    global startingAccountName
    startingAccountName = new_account
    return new_account

@app.callback(
    Output('state_container', 'data-type'),
    [Input('type_selector', 'value'),],
)
def update_post_value(new_type):
    print(f"new_type {new_type}")
    return new_type

@app.callback(
    Output('state_container', 'data-tag'),
    [Input('tags_selector', 'value')],
)
def update_tag_value(new_tag):
    print(f"new_tag {new_tag}")
    return new_tag

@app.callback(
    Output('state_container', 'data-buttons'),
    [Input('state_container', 'data-account'),
    Input('next_button', 'n_clicks'),
    Input('previous_button', 'n_clicks'),
    Input('state_container', 'data-type'),
    Input('state_container', 'data-tag'),],
    [State('state_container', 'data-buttons'),
    State('state_container', 'data-post')],
)
def update_post_index(account, next_presses, previous_presses, postType, postTag, button_state, currentPost):
    print("post update press: ", next_presses, previous_presses, *button_state)
    postIndex, num_nexts, num_prevs  = button_state
    postIndex = currentPost
    AC[account].currentType = postType
    AC[account].currentTag = postTag
    if next_presses > num_nexts:
        num_nexts = num_nexts + 1
        if postIndex < len(AC[account]) - 1:
            postIndex =  postIndex + 1
        else:
            postIndex = 0
    elif previous_presses > num_prevs:
        num_prevs = num_prevs + 1
        if postIndex > 0:
            postIndex = postIndex - 1
        else:
            postIndex =  len(AC[account]) - 1
    else:
        postIndex = 0
    return (postIndex, num_nexts, num_prevs)

@app.callback(
    Output('state_container', 'data-post'),
    [Input('post_selector', 'value'),],
)
def update_post_value(new_post):
    print(f"new_post {new_post}")
    return new_post

#Draw

@app.callback(
    Output('tumblr_entry', 'children'),
    [Input('state_container', 'data-account'),
    Input('state_container', 'data-type'),
    Input('state_container', 'data-tag'),
    Input('state_container', 'data-post'),],
)
def update_output_div(account, postType, postTag, postNum):
    print("Draw:", account, postType, postTag, postNum)
    AC[account].currentType = postType
    AC[account].currentTag = postTag
    return AC[account](postNum)

@app.callback(
    Output('post_url', 'children'),
    [Input('state_container', 'data-account'),
    Input('state_container', 'data-type'),
    Input('state_container', 'data-tag'),
    Input('state_container', 'data-post'),],
)
def update_output_div(account, postType, postTag, postNum):
    print("Draw:", account, postType, postTag, postNum)
    AC[account].currentType = postType
    AC[account].currentTag = postTag
    return html.A(AC[account][postNum].get('Post url', ''),
        href=AC[account][postNum].get('Post url', ''))


#Options


@app.callback(
    Output('type_selector', 'options'),
    [Input('state_container', 'data-account'),]
)
def update_type_options(account):
    return genTypesDict(AC[account])

@app.callback(
    Output('tags_selector', 'options'),
    [Input('state_container', 'data-account'),
    Input('state_container', 'data-type'),]
)
def update_tags_options(account, aType):
    print(f"tags {AC[account].sortedTags(countTuple = True)[:5]}")
    return genTagOptions(AC[account])

@app.callback(
    Output('current_tags', 'options'),
    [Input('state_container', 'data-account'),
    Input('state_container', 'data-type'),
    Input('state_container', 'data-tag'),
    Input('state_container', 'data-post'),],
)
def update_output_tag_options(account, postType, postTag, postNum):
    AC[account].currentType = postType
    AC[account].currentTag = postTag
    print("Draw tags:", AC[account][postNum].tags)
    return  genTagOptions(AC[account], withNum = False)


@app.callback(
    Output('post_selector', 'max'),
    [Input('state_container', 'data-account'),
    Input('state_container', 'data-type'),
    Input('state_container', 'data-tag'),]
)
def update_post_max(account, postType, postTag):
    print("max", len(AC[account]) - 1)
    AC[account].currentType = postType
    AC[account].currentTag = postTag
    return len(AC[account]) - 1

@app.callback(
    Output('post_selector', 'marks'),
    [Input('state_container', 'data-account'),
    Input('state_container', 'data-type'),
    Input('state_container', 'data-tag'),]
)
def update_post_marks(account, postType, postTag):
    print("marks", genPostSelectorMarks(AC[account]))
    AC[account].currentType = postType
    AC[account].currentTag = postTag
    return genPostSelectorMarks(AC[account])

#Values

@app.callback(
    Output('type_selector', 'value'),
    [Input('state_container', 'data-account'),],
    [State('type_selector', 'options')]
)
def update_type_value(account, options):
    print("zeroing types", options)
    avail = [t['value'] for t in options]
    return 'texts' if 'texts' in avail else avail[0]

@app.callback(
    Output('tags_selector', 'value'),
    [Input('state_container', 'data-account'),],
)
def update_tag_value(account):
    print("zeroing tags")
    return 'None'

@app.callback(
    Output('current_tags', 'value'),
    [Input('state_container', 'data-account'),
    Input('state_container', 'data-type'),
    Input('state_container', 'data-tag'),
    Input('state_container', 'data-post')],
)
def update_output_tag_options(account, postType, postTag, postNum):
    AC[account].currentType = postType
    AC[account].currentTag = postTag
    print("Draw tags:", AC[account][postNum].tags)
    return  AC[account][postNum].tags

@app.callback(
    Output('post_selector', 'value'),
    [Input('state_container', 'data-account'),
    Input('state_container', 'data-buttons')],
)
def update_post_value(account, button_vals):
    print("updating post: ",  button_vals[0])
    return button_vals[0]



if __name__ == '__main__':
    webbrowser.open('http://127.0.0.1:8050/', new=2)
    app.run_server(debug=True)
