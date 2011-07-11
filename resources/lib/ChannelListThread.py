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

from ChannelList import ChannelList
from Channel import Channel
from Globals import *



class ChannelListThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.myOverlay = None
        self.shouldExit = False
        sys.setcheckinterval(25)
        self.chanlist = ChannelList()
        self.paused = False


    def log(self, msg, level = xbmc.LOGDEBUG):
        log('ChannelListThread: ' + msg, level)


    def run(self):
        self.log("Starting")
        self.shouldExit = False
        self.chanlist.exitThread = False
        self.chanlist.readConfig()
        self.chanlist.sleepTime = 0.1

        if self.myOverlay == None:
            self.log("Overlay not defined. Exiting.")
            return

        for i in range(self.myOverlay.maxChannels):
            self.chanlist.channels.append(Channel())

            if self.myOverlay.channels[i].isValid == False:
                while True:
                    if self.shouldExit == True:
                        self.log("Closing thread")
                        return

                    time.sleep(1)

                    if self.paused == False:
                        break

                self.chanlist.channels[i].setAccessTime(self.myOverlay.channels[i].lastAccessTime)

                if self.chanlist.setupChannel(i + 1, True, True) == True:
                    while self.paused == True:
                        if self.shouldExit == True:
                            return
                            
                        time.sleep(1)

                    self.myOverlay.channels[i] = self.chanlist.channels[i]
                    xbmc.executebuiltin("Notification(PseudoTV, Channel " + str(i + 1) + " Added, 4000)")

        REAL_SETTINGS.setSetting('ForceChannelReset', 'false')
        self.chanlist.sleepTime = 0.3

        while True:
            for i in range(self.myOverlay.maxChannels):
                modified = True

                while modified == True and self.myOverlay.channels[i].getTotalDuration() < PREP_CHANNEL_TIME:
                    modified = False

                    if self.shouldExit == True:
                        self.log("Closing thread")
                        return

                    time.sleep(2)
                    curtotal = self.myOverlay.channels[i].getTotalDuration()
                    self.chanlist.appendChannel(i + 1)

                    # A do-while loop for the paused state
                    while True:
                        if self.shouldExit == True:
                            self.log("Closing thread")
                            return

                        time.sleep(2)

                        if self.paused == False:
                            break

                    if self.myOverlay.channels[i].setPlaylist(CHANNELS_LOC + "channel_" + str(i + 1) + ".m3u") and self.myOverlay.channels[i].isValid == False:
                        self.myOverlay.channels[i].totalTimePlayed = 0
                        self.myOverlay.channels[i].isValid = True
                        self.myOverlay.channels[i].fileName = CHANNELS_LOC + 'channel_' + str(i + 1) + '.m3u'
                        ADDON_SETTINGS.setSetting('Channel_' + str(i + 1) + '_time', '0')
                        ADDON_SETTINGS.setSetting('Channel_' + str(i + 1) + '_changed', 'False')

                    if self.myOverlay.channels[i].getTotalDuration() > curtotal:
                        modified = True

                timeslept = 0

            while timeslept < 1800:
                if self.shouldExit == True:
                    return

                time.sleep(2)
                timeslept += 2

        self.log("All channels up to date.  Exiting thread.")


    def pause(self):
        self.paused = True
        self.chanlist.threadPaused = True


    def unpause(self):
        self.paused = False
        self.chanlist.threadPaused = False
