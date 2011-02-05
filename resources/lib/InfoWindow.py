import xbmc, xbmcgui, xbmcaddon
import subprocess, os
import time, threading
import datetime

from Playlist import Playlist
from Globals import *
from Channel import Channel



class InfoWindow(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        self.posOffset = 0
        self.channelOffset = 0
        self.actionSemaphore = threading.BoundedSemaphore()
        self.displayTimer = threading.Timer(10.0, self.displayTimerAction)


    def onFocus(self, controlid):
        pass


    def log(self, msg):
        log('Info: ' + msg)


    def onInit(self):
        self.log('onInit')
        self.posOffset = 0
        self.channelOffset = 0
        self.setShowInfo()
        self.startDisplayTimer()
        self.log('onInit return')


    def startDisplayTimer(self):
        # Cancel the timer if it is still running
        if self.displayTimer.isAlive():
            self.displayTimer.cancel()
            self.displayTimer = threading.Timer(10.0, self.displayTimerAction)

        self.displayTimer.start()


    def displayTimerAction(self):
        self.log("displayTimerAction")
        self.displayTimer = threading.Timer(10.0, self.displayTimerAction)
        self.actionSemaphore.acquire()
        self.closeInfoWindow()
        self.actionSemaphore.release()


    def onAction(self, act):
        self.log('onAction ' + str(act.getId()))
        action = act.getId()
        
        if self.actionSemaphore.acquire(False) == False:
            self.log('Unable to get semaphore')
            return

        if action == ACTION_PREVIOUS_MENU:
            self.closeInfoWindow()
        elif action == ACTION_MOVE_LEFT:
            self.posOffset = self.posOffset - 1
            self.setShowInfo()
        elif action == ACTION_MOVE_RIGHT:
            self.posOffset = self.posOffset + 1
            self.setShowInfo()
        elif action == ACTION_MOVE_UP:
            self.channelOffset -= 1
            self.setShowInfo()
        elif action == ACTION_MOVE_DOWN:
            self.channelOffset += 1
            self.setShowInfo()
        elif action == ACTION_SHOW_INFO:
            self.closeInfoWindow()
        elif action == ACTION_STOP:
            self.closeInfoWindow()
            self.MyOverlayWindow.end()

        self.startDisplayTimer()
        self.actionSemaphore.release()
        self.log('onAction return')


    def closeInfoWindow(self):
        self.log('closeInfoWindow')

        try:
            self.MyOverlayWindow.startSleepTimer()
        except:
            pass

        if self.displayTimer.isAlive():
            self.displayTimer.cancel()
            self.displayTimer = threading.Timer(10.0, self.displayTimerAction)

        self.close()


    def onControl(self, control):
        self.log('onControl')


    def setShowInfo(self):
        self.log('setShowInfo')

        if self.posOffset > 0:
            self.getControl(502).setLabel('COMING UP:')
        elif self.posOffset < 0:
            self.getControl(502).setLabel('ALREADY SEEN:')
        elif self.posOffset == 0:
            if self.channelOffset == 0:
                self.getControl(502).setLabel('NOW WATCHING:')
            else:
                self.getControl(502).setLabel('CURRENTLY ON:')

        position = self.MyOverlayWindow.channels[self.MyOverlayWindow.currentChannel - 1].playlistPosition + self.posOffset
        channel = self.MyOverlayWindow.fixChannel(self.MyOverlayWindow.currentChannel + self.channelOffset)
        self.getControl(503).setLabel(self.MyOverlayWindow.channels[channel - 1].getItemTitle(position))
        self.getControl(504).setLabel(self.MyOverlayWindow.channels[channel - 1].getItemEpisodeTitle(position))
        self.getControl(505).setLabel(self.MyOverlayWindow.channels[channel - 1].getItemDescription(position))
        self.getControl(506).setImage(IMAGES_LOC + self.MyOverlayWindow.channels[channel - 1].name + '.png')
        self.log('setShowInfo return')
