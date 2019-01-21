import dash
from dash.dependencies import Input, Output, State
import dash_core_components as dcc
import dash_html_components as html


class MultiDashFront(object):
    def __init__(self, tumblrsPath):
        self.path = tumblrsPath
        self.app = dash.Dash(__name__)
        self.Backend = multiTumDis.BackendManager(self.path)

        dataDict = self.Backend.currentBlogInfo.copy()
        dataDict['data-buttons'] = (0,0,0)
        dataDict['data-update'] = 0
