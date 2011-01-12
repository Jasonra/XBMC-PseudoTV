import xbmc, xbmcgui, xbmcaddon
import subprocess, os
import time, threading
import datetime

from Playlist import Playlist
from Globals import *
from Channel import Channel



class EPGWindow(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        self.focusRow = 0
        self.focuaIndex = 0
        self.focusTime = 0
        self.focusEndTime = 0
        self.shownTime = 0
        self.centerChannel = 0
        self.currentTimeBar = xbmcgui.ControlImage(322, 288, 2, 398, IMAGES_LOC + 'solid.png', colorDiffuse='0x99FF0000')
        self.channelButtons = [None] * 5
        self.actionSemaphore = threading.BoundedSemaphore()

        for i in range(5):
            self.channelButtons[i] = []


    def onFocus(self, controlid):
        pass


    # set the time labels
    def setTimeLabels(self, thetime):
        self.log('setTimeLabels')
        now = datetime.datetime.fromtimestamp(thetime)
        self.getControl(104).setLabel(now.strftime('%A, %b %d'))
        delta = datetime.timedelta(minutes=30)

        for i in range(3):
            self.getControl(101 + i).setLabel(now.strftime("%I:%M"))
            now = now + delta

        self.log('setTimeLabels return')


    def log(self, msg):
        log('EPG: ' + msg)


    def onInit(self):
        self.log('onInit')
        self.addControl(self.currentTimeBar)

        if self.setChannelButtons(time.time(), self.MyOverlayWindow.currentChannel) == False:
            self.log('Unable to add channel buttons')
            return

        curtime = time.time()
        self.focusIndex = 0

        # set the button that corresponds to the currently playing show
        for i in range(len(self.channelButtons[2])):
            left, top = self.channelButtons[2][i].getPosition()
            width = self.channelButtons[2][i].getWidth()
            left = left - 322
            starttime = self.shownTime + (left / 0.1774)
            endtime = starttime + (width / 0.1774)

            if curtime >= starttime and curtime <= endtime:
                self.focusIndex = i
                self.setFocus(self.channelButtons[2][i])
                self.focusTime = starttime + 30
                self.focusEndTime = endtime
                break

        self.focusRow = 2
        self.log('onInit return')


    # setup all channel buttons for a given time
    def setChannelButtons(self, starttime, curchannel):
        self.log('setChannelButtons ' + str(starttime) + ', ' + str(curchannel))
        self.removeControl(self.currentTimeBar)
        self.centerChannel = self.MyOverlayWindow.fixChannel(curchannel)
        curchannel = self.MyOverlayWindow.fixChannel(curchannel - 2)
        starttime = starttime // 1
        starttime = self.roundToHalfHour(starttime)
        self.setTimeLabels(starttime)
        self.shownTime = starttime

        for i in range(5):
            self.setButtons(starttime, curchannel, i)
            self.getControl(301 + i).setLabel(self.MyOverlayWindow.channels[curchannel - 1].name + '\n' + str(curchannel))
            curchannel = self.MyOverlayWindow.fixChannel(curchannel + 1)

        if time.time() >= starttime and time.time() < starttime + 5400:
            dif = (starttime + 5400 - time.time()) // 1
            self.currentTimeBar.setPosition(1278 - (dif * .1774), 288)
        else:
            if time.time() < starttime:
                self.currentTimeBar.setPosition(322, 288)
            else:
                self.currentTimeBar.setPosition(1278, 288)

        self.addControl(self.currentTimeBar)
        self.log('setChannelButtons return')


    # round the given time down to the nearest half hour
    def roundToHalfHour(self, thetime):
        n = datetime.datetime.fromtimestamp(thetime)
        delta = datetime.timedelta(minutes=30)

        if n.minute > 29:
            n = n.replace(minute=30, second=0, microsecond=0)
        else:
            n = n.replace(minute=0, second=0, microsecond=0)

        return time.mktime(n.timetuple())


    # create the buttons for the specified channel in the given row
    def setButtons(self, starttime, curchannel, row):
        self.log('setButtons ' + str(starttime) + ", " + str(curchannel) + ", " + str(row))
        curchannel = self.MyOverlayWindow.fixChannel(curchannel)

        if xbmc.Player().isPlaying() == False:
            self.log('No video is playing, not adding buttons')
            self.closeEPG()
            return False

        # go through all of the buttons and remove them
        for button in self.channelButtons[row]:
            self.removeControl(button)

        del self.channelButtons[row][:]

        # if the channel is paused, then only 1 button needed
        if self.MyOverlayWindow.channels[curchannel - 1].isPaused:
            self.channelButtons[row].append(xbmcgui.ControlButton(322, 288 + (row * 80), 958, 78, self.MyOverlayWindow.channels[curchannel - 1].getCurrentDescription()), alignment=8)
            self.addControl(self.channelButtons[row][0])
        else:
            # Find the show that was running at the given time
            # Use the current time and show offset to calculate it
            # At timedif time, channelShowPosition was playing at channelTimes
            # The only way this isn't true is if the current channel is curchannel since
            # it could have been fast forwarded or rewinded (rewound)?
            if curchannel == self.MyOverlayWindow.currentChannel:
                playlistpos = xbmc.PlayList(xbmc.PLAYLIST_VIDEO).getposition()
                videotime = xbmc.Player().getTime()
                reftime = time.time()
            else:
                playlistpos = self.MyOverlayWindow.channels[curchannel - 1].playlistPosition
                videotime = self.MyOverlayWindow.channels[curchannel - 1].showTimeOffset
                reftime = self.MyOverlayWindow.channels[curchannel - 1].lastAccessTime

            # normalize reftime to the beginning of the video
            reftime -= videotime

            while reftime > starttime:
                playlistpos -= 1
                # No need to check bounds on the playlistpos, the duration function makes sure it is correct
                reftime -= self.MyOverlayWindow.channels[curchannel - 1].getItemDuration(playlistpos)

            while reftime + self.MyOverlayWindow.channels[curchannel - 1].getItemDuration(playlistpos) < starttime:
                reftime += self.MyOverlayWindow.channels[curchannel - 1].getItemDuration(playlistpos)
                playlistpos += 1

            # create a button for each show that runs in the next hour and a half
            endtime = starttime + 5400
            totaltime = 0

            while reftime < endtime:
                xpos = int(322 + (totaltime * 0.1774))
                tmpdur = self.MyOverlayWindow.channels[curchannel - 1].getItemDuration(playlistpos)
                shouldskip = False

                # this should only happen the first time through this loop
                # it shows the small portion of the show before the current one
                if reftime < starttime:
                    tmpdur -= starttime - reftime
                    reftime = starttime

                    if tmpdur < 60 * 3:
                        shouldskip = True

                width = int(0.1774 * tmpdur)

                if width + xpos > 1280:
                    width = 1280 - xpos

                if shouldskip == False:
                    self.channelButtons[row].append(xbmcgui.ControlButton(xpos, 288 + (row * 80), width, 78, self.MyOverlayWindow.channels[curchannel - 1].getItemDescription(playlistpos), alignment=8))
                    self.addControl(self.channelButtons[row][-1])

                totaltime += tmpdur
                reftime += tmpdur
                playlistpos += 1

        self.log('setButtons return')
        return True


    def onAction(self, act):
        self.log('onAction ' + str(act.getId()))

        if self.actionSemaphore.acquire(False) == False:
            self.log('Unable to get semaphore')
            return

        action = act.getId()

        if action == ACTION_PREVIOUS_MENU:
            self.closeEPG()
        elif action == ACTION_MOVE_DOWN:
            self.GoDown()
        elif action == ACTION_MOVE_UP:
            self.GoUp()
        elif action == ACTION_MOVE_LEFT:
            self.GoLeft()
        elif action == ACTION_MOVE_RIGHT:
            self.GoRight()
        elif action == ACTION_STOP:
            self.closeEPG()
            self.MyOverlayWindow.end()

        self.actionSemaphore.release()
        self.log('onAction return')


    def closeEPG(self):
        self.log('closeEPG')

        try:
            self.removeControl(self.currentTimeBar)
            self.MyOverlayWindow.startSleepTimer()
        except:
            pass

        self.close()


    def onControl(self, control):
        self.log('onControl')


    # Run when a show is selected, so close the epg and run the show
    def onClick(self, controlid):
        self.log('onClick')

        if self.actionSemaphore.acquire(False) == False:
            self.log('Unable to get semaphore')
            return

        selectedbutton = self.getControl(controlid)

        for i in range(5):
            for x in range(len(self.channelButtons[i])):
                if selectedbutton == self.channelButtons[i][x]:
                    self.focusRow = i
                    self.focusIndex = x
                    self.selectShow()
                    self.closeEPG()
                    self.actionSemaphore.release()
                    self.log('onClick found button return')
                    return

        self.closeEPG()
        self.actionSemaphore.release()
        self.log('onClick return')


    def GoDown(self):
        self.log('goDown')

        # change controls to display the proper junks
        if self.focusRow == 4:
            self.setChannelButtons(self.shownTime, self.centerChannel + 1)
            self.focusRow = 3

        self.setProperButton(self.focusRow + 1)
        self.log('goDown return')


    def GoUp(self):
        self.log('goUp')

        # same as godown
        # change controls to display the proper junks
        if self.focusRow == 0:
            self.setChannelButtons(self.shownTime, self.centerChannel - 1)
            self.focusRow = 1

        self.setProperButton(self.focusRow - 1)
        self.log('goUp return')


    def GoLeft(self):
        self.log('goLeft')

        # change controls to display the proper junks
        if self.focusIndex == 0:
            self.setChannelButtons(self.shownTime - 1800, self.centerChannel)

        self.focusTime -= 60
        self.setProperButton(self.focusRow, True)
        self.log('goLeft return')


    def GoRight(self):
        self.log('goRight')

        # change controls to display the proper junks
        if self.focusIndex == len(self.channelButtons[self.focusRow]) - 1:
            self.setChannelButtons(self.shownTime + 1800, self.centerChannel)

        self.focusTime = self.focusEndTime + 30
        self.setProperButton(self.focusRow, True)
        self.log('goRight return')


    # based on the current focus row and index, find the appropriate button in
    # the new row to set focus to
    def setProperButton(self, newrow, resetfocustime = False):
        self.log('setProperButton ' + str(newrow))
        self.focusRow = newrow

        for i in range(len(self.channelButtons[newrow])):
            left, top = self.channelButtons[newrow][i].getPosition()
            width = self.channelButtons[newrow][i].getWidth()
            left = left - 322
            starttime = self.shownTime + (left / 0.1774)
            endtime = starttime + (width / 0.1774)

            if self.focusTime >= starttime and self.focusTime <= endtime:
                self.focusIndex = i
                self.setFocus(self.channelButtons[newrow][i])
                self.focusEndTime = endtime

                if resetfocustime:
                    self.focusTime = starttime + 30

                self.log('setProperButton found button return')
                return

        self.focusIndex = 0
        self.setFocus(self.channelButtons[newrow][0])
        self.log('setProperButton return')


    # using the currently selected button, play the proper shows
    def selectShow(self):
        self.log('selectShow')
        # use the selected time to set the video
        left, top = self.channelButtons[self.focusRow][self.focusIndex].getPosition()
        width = self.channelButtons[self.focusRow][self.focusIndex].getWidth()
        left = left - 322 + (width / 2)
        starttime = self.shownTime + (left / 0.1774)
        newchan = self.MyOverlayWindow.fixChannel(self.centerChannel + self.focusRow - 2)
        plpos = self.determinePlaylistPosAtTime(starttime, newchan)

        if plpos == -1:
            self.log('Unable to find the proper playlist to set from EPG')
            return

        if self.MyOverlayWindow.channels[newchan - 1].playlistPosition != plpos:
            self.MyOverlayWindow.channels[newchan - 1].setShowPosition(plpos)
            self.MyOverlayWindow.channels[newchan - 1].setShowTime(0)
            self.MyOverlayWindow.channels[newchan - 1].setAccessTime(time.time())

        self.MyOverlayWindow.newChannel = newchan
        self.log('selectShow return')


    def determinePlaylistPosAtTime(self, starttime, channel):
        self.log('determinePlaylistPosAtTime ' + str(starttime) + ', ' + str(channel))
        channel = self.MyOverlayWindow.fixChannel(channel)

        # if the channel is paused, then it's just the current item
        if self.MyOverlayWindow.channels[channel - 1].isPaused:
            self.log('determinePlaylistPosAtTime paused return')
            return self.MyOverlayWindow.channels[channel - 1].playlistPosition
        else:
            # Find the show that was running at the given time
            # Use the current time and show offset to calculate it
            # At timedif time, channelShowPosition was playing at channelTimes
            # The only way this isn't true is if the current channel is curchannel since
            # it could have been fast forwarded or rewinded (rewound)?
            if channel == self.MyOverlayWindow.currentChannel:
                playlistpos = xbmc.PlayList(xbmc.PLAYLIST_VIDEO).getposition()
                videotime = xbmc.Player().getTime()
                reftime = time.time()
            else:
                playlistpos = self.MyOverlayWindow.channels[channel - 1].playlistPosition
                videotime = self.MyOverlayWindow.channels[channel - 1].showTimeOffset
                reftime = self.MyOverlayWindow.channels[channel - 1].lastAccessTime

            # normalize reftime to the beginning of the video
            reftime -= videotime

            while reftime > starttime:
                playlistpos -= 1
                reftime -= self.MyOverlayWindow.channels[channel - 1].getItemDuration(playlistpos)

            while reftime + self.MyOverlayWindow.channels[channel - 1].getItemDuration(playlistpos) < starttime:
                reftime += self.MyOverlayWindow.channels[channel - 1].getItemDuration(playlistpos)
                playlistpos += 1

            self.log('determinePlaylistPosAtTime return')
            return self.MyOverlayWindow.channels[channel - 1].fixPlaylistIndex(playlistpos)
