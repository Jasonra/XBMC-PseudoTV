#   Copyright (C) 2011 Jason Anderson
#
#
# This file is part of PseudoTV.
#
# PseudoTV is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PseudoTV is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PseudoTV.  If not, see <http://www.gnu.org/licenses/>.

import xbmc, xbmcgui, xbmcaddon
import subprocess, os
import time, threading
import datetime
import sys, re
import random

from Globals import *
from ChannelList import ChannelList



class AdvancedConfig(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        self.log("__init__")
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)


    def log(self, msg):
        log('AdvancedConfig: ' + msg)


    def onInit(self):
        self.log("onInit")


    def onFocus(self, controlId):
        pass


    def onAction(self, act):
        action = act.getId()


    def onClick(self, controlId):
        self.log("onClick " + str(controlId))

