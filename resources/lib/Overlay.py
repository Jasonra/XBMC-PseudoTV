import xbmc, xbmcgui, xbmcaddon
import subprocess, os
import time, threading
import datetime

from Playlist import Playlist
from Globals import *
from Channel import Channel



# overlay window to catch events and change channels
class TVOverlay(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)
        self.log('__init__')
        # initialize all variables
        self.channels = []
        self.inputChannel = -1
        self.channelLabel = []
        self.lastActionTime = 0
        self.actionSemaphore = threading.BoundedSemaphore()
        self.setCoordinateResolution(1)

        for i in range(3):
            self.channelLabel.append(xbmcgui.ControlImage(50 + (50 * i), 50, 50, 50, IMAGES_LOC + 'solid.png', colorDiffuse='0xAA00ff00'))
            self.addControl(self.channelLabel[i])
            self.channelLabel[i].setVisible(False)

        self.doModal()
        self.log('__init__ return')


    def resetChannelTimes(self):
        curtime = time.time()

        for i in range(self.maxChannels):
            self.channels[i].setAccessTime(curtime)


    def onFocus(self, controlId):
        pass


    # override the doModal function so we can setup everything first
    def onInit(self):
        self.log('onInit')
        self.channelLabelTimer = threading.Timer(5.0, self.hideChannelLabel)
        self.myEPG = EPGWindow("script.PseudoTV.EPG.xml", ADDON_INFO, "Default")
        self.myEPG.MyOverlayWindow = self
        self.background = self.getControl(101)
        self.findMaxChannels()

        if self.maxChannels == 0:
            self.message('Unable to find any channels. Create smart\nplaylists with file names Channel_1, Chanbel_2, etc.')
            return

        # Don't allow any actions during initialization
        self.actionSemaphore.acquire()

        if self.readConfig() == False:
            return

        self.sleepTimer = threading.Timer(self.sleepTimeValue, self.sleepAction)
        self.resetChannelTimes()
        self.setChannel(self.currentChannel)
        self.background.setVisible(False)
        self.sleepTimer.start()
        self.actionSemaphore.release()
        self.log('onInit return')


    # Determine the maximum number of channels by opening consecutive
    # playlists until we don't find one
    def findMaxChannels(self):
        self.log('findMaxChannels')
        notfound = False
        channel = 1

        while notfound == False:
            try:
                fl = open(xbmc.translatePath('special://profile/playlists/video') + '/Channel_' + str(channel) + '.xsp', 'r')
            except IOError:
                break

            channel += 1
            fl.close

        self.maxChannels = channel - 1
        self.log('findMaxChannels return')


    # setup all basic configuration parameters, including creating the playlists that
    # will be used to actually run this thing
    def readConfig(self):
        self.log('readConfig')
        self.updateDialog = xbmcgui.DialogProgress()
        self.sleepTimeValue = int(ADDON_SETTINGS.getSetting('AutoOff')) * 60
        self.log('Auto off is ' + str(self.sleepTimeValue))
        self.updateDialog.create("XBMC TV", "Updating channel list")
        self.updateDialog.update(0, "Updating channel list")
        self.background.setVisible(True)

        # Go through all channels, create their arrays, and setup the new playlist
        for i in range(self.maxChannels):
            self.channels.append(Channel())

            if self.makeChannelList(i + 1) == False:
                return False

            self.channels[-1].setPlaylist(CHANNELS_LOC + 'channel_' + str(i + 1) + '.m3u')
            self.channels[-1].name = self.getSmartPlaylistName(xbmc.translatePath("special://profile/playlists/video") + "/Channel_" + str(i + 1) + ".xsp")

        self.currentChannel = 1
        xbmc.Player().stop()
        self.updateDialog.close()
        self.log('readConfig return')
        return True


    def getSmartPlaylistName(self, filename):
        self.log('getSmartPlaylistName ' + filename)

        try:
            fl = open(filename, "r")
        except:
            self.log("Unable to open the smart playlist " + filename)
            return ''

        line = fl.readline()
        thename = ''

        while len(line) > 0:
            index = line.find('<name>')

            if index >= 0:
                index2 = line.find('</name>')

                if index2 >= 0:
                    thename = line[index + 6:index2]
                    break

            line = fl.readline()
            
        fl.close()
        self.log('getSmartPlaylistName return ' + thename)
        return thename


    # handle fatal errors: log it, show the dialog, and exit
    def Error(self, message):
        self.log('FATAL ERROR: ' + message)
        dlg = xbmcgui.Dialog()
        dlg.ok('Error', message)
        del dlg
        self.end()


    # Based on a smart playlist, create a normal playlist that can actually be used by us
    def makeChannelList(self, channel):
        self.log('makeChannelList ' + str(channel))
        xbmc.executebuiltin('XBMC.Playlist.clear()')

        if self.startPlaylist("XBMC.PlayMedia(special://profile/playlists/video/Channel_" + str(channel) + ".xsp)") == False:
             self.Error('Unable to process channel ' + str(channel))
             return False

        xbmc.Player().pause()
        channelplaylist = open(CHANNELS_LOC + "channel_" + str(channel) + ".m3u", "w")
        channelplaylist.write("#EXTM3U\n")
        updatebase = (channel - 1) * 100.0 / self.maxChannels
        totalchanrange = 100.0 / self.maxChannels
        itemsize = totalchanrange / xbmc.PlayList(xbmc.PLAYLIST_VIDEO).size()
        lastval = 0

        # Write each entry into the new playlist
        for i in range(xbmc.PlayList(xbmc.PLAYLIST_VIDEO).size()):
            try:
                duration = int(xbmc.PlayList(xbmc.PLAYLIST_VIDEO)[i].getduration()) * 60
            except:
                duration = self.getDurationForFile(xbmc.PlayList(xbmc.PLAYLIST_VIDEO)[i].getfilename())

            if duration > 0:
                title = self.getTitleForFile(xbmc.PlayList(xbmc.PLAYLIST_VIDEO)[i].getfilename())

                if len(title) == 0:
                    title = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)[i].getdescription()

                channelplaylist.write("#EXTINF:" + str(duration) + "," + title + "\n")
                channelplaylist.write(xbmc.PlayList(xbmc.PLAYLIST_VIDEO)[i].getfilename() + "\n")
            else:
                self.log("Can't get duration: " + xbmc.PlayList(xbmc.PLAYLIST_VIDEO)[i].getfilename())

            if (i + 1) * itemsize // 1 > lastval:
                self.updateDialog.update(updatebase + ((i + 1) * itemsize), "Updating channel list")
                lastval = (i + 1) * itemsize // 1

        channelplaylist.close()
        self.log('makeChannelList return')
        return True


    # We need to get the title for tv shows
    def getTitleForFile(self, filename):
        # determine the filename and path
        path, name = filename.rsplit('/', 1)
        path = path + '/'
        # Get past a bug in the http api that turns all commas into semi-colons
        name = name.replace(',', '%2C')
        path = path.replace(',', '%2C')
        # construct the query
        query = 'select tvshow.c00 from tvshow where tvshow.idShow in (select tvshowlinkepisode.idShow from tvshowlinkepisode where tvshowlinkepisode.idEpisode in' \
            '(select episode.idEpisode from episode where episode.idFile in (select files.idFile from files where files.strFilename="' + name + '" and files.idPath in ' \
            '(select path.idPath from path where path.strPath="' + path + '"))))'
        #run the query
        data = xbmc.executehttpapi('QueryVideoDatabase(' + query + ')')

        if len(data) > 15:
            # parse the result
            if data[:7] == '<field>':
                index = data.find('</field>')

                if index > 0:
                    return data[7:index]

        return ''


    # since the playlist isn't properly returning the duration, get it from the database
    def getDurationForFile(self, filename):
        # determine the filename and path
        path, name = filename.rsplit('/', 1)
        path = path + '/'
        # Get past a bug in the http api that turns all commas into semi-colons
        name = name.replace(',', '%2C')
        path = path.replace(',', '%2C')
        # construct the query
        query = 'select streamdetails.iVideoDuration from streamdetails where streamdetails.iStreamType=0 and streamdetails.idFile in' \
            '(select files.idFile from files where files.strFilename="' + name + '" and files.idPath in' \
            '(select path.idPath from path where path.strPath="' + path + '"))'
        #run the query
        data = xbmc.executehttpapi('QueryVideoDatabase(' + query + ')')

        if len(data) > 15:
            # parse the result
            if data[:7] == '<field>':
                index = data.find('</field>')

                if index > 0:
                    return int(data[7:index])

        return 0


    def channelDown(self):
        self.log('channelDown')
        self.background.setVisible(True)
        channel = self.currentChannel
        channel -= 1

        if channel < 1:
            channel = self.maxChannels

        self.setChannel(channel)
        self.background.setVisible(False)
        self.log('channelDown return')


    def channelUp(self):
        self.log('channelUp')
        self.background.setVisible(True)
        channel = self.currentChannel
        channel += 1

        if channel > self.maxChannels:
            channel = 1

        self.setChannel(channel)
        self.background.setVisible(False)
        self.log('channelUp return')


    def message(self, data):
        self.log('Dialog message: ' + data)
        dlg = xbmcgui.Dialog()
        dlg.ok('Info', data)
        del dlg


    def log(self, msg):
        log('TVOverlay: ' + msg)


    # set the channel, the proper show offset, and time offset
    def setChannel(self, channel):
        self.log('setChannel ' + str(channel))

        if channel < 1 or channel > self.maxChannels:
            self.log('setChannel invalid channel')
            return

        self.lastActionTime = 0
        timedif = 0
        forcestart = True
        samechannel = False

        # first of all, save playing state, time, and playlist offset for
        # the currently playing channel
        if xbmc.Player().isPlaying():
            if channel != self.currentChannel:
                self.channels[self.currentChannel - 1].setPaused(xbmc.getCondVisibility('Player.Paused'))
                self.channels[self.currentChannel - 1].setShowTime(xbmc.Player().getTime())
                self.channels[self.currentChannel - 1].setShowPosition(xbmc.PlayList(xbmc.PLAYLIST_VIDEO).getposition())
                self.channels[self.currentChannel - 1].setAccessTime(time.time())
            else:
                samechannel = True

            forcestart = False

        if self.currentChannel != channel or forcestart:
            self.currentChannel = channel
            # now load the proper channel playlist
            xbmc.PlayList(xbmc.PLAYLIST_VIDEO).clear()

            if self.startPlaylist('XBMC.PlayMedia(' + CHANNELS_LOC + 'channel_' + str(channel) + '.m3u)') == False:
                self.Error('Unable to set channel ' + str(channel))
                return

        timedif += (time.time() - self.channels[self.currentChannel - 1].lastAccessTime)

        # adjust the show and time offsets to properly position inside the playlist
        while self.channels[self.currentChannel - 1].showTimeOffset + timedif > self.channels[self.currentChannel - 1].getCurrentDuration():
            self.channels[self.currentChannel - 1].addShowPosition(1)
            timedif -= self.channels[self.currentChannel - 1].getCurrentDuration() - self.channels[self.currentChannel - 1].showTimeOffset
            self.channels[self.currentChannel - 1].setShowTime(0)

        # if needed, set the show offset
        if self.channels[self.currentChannel - 1].playlistPosition != xbmc.PlayList(xbmc.PLAYLIST_VIDEO).getposition():
            if samechannel == False:
                if self.startPlaylist('XBMC.Playlist.PlayOffset(' + str(self.channels[self.currentChannel - 1].playlistPosition) + ')') == False:
                    self.Error('Unable to set offset for channel ' + str(channel))
                    return
            else:
                if self.startPlaylist('XBMC.Playlist.PlayOffset(' + str(self.channels[self.currentChannel - 1].playlistPosition - xbmc.PlayList(xbmc.PLAYLIST_VIDEO).getposition()) + ')') == False:
                    self.Error('Unable to set offset for channel ' + str(channel))
                    return

        # set the time offset
        self.channels[self.currentChannel - 1].setAccessTime(time.time())

        if self.channels[self.currentChannel - 1].isPaused:
            try:
                xbmc.Player().seekTime(self.channels[self.currentChannel - 1].showTimeOffset)
                xbmc.Player().pause()

                if self.waitForVideoPaused() == False:
                    return
            except:
                self.log('Exception during seek on paused channel')
        else:
            seektime = self.channels[self.currentChannel - 1].showTimeOffset + timedif

            try:
                xbmc.Player().seekTime(seektime)
            except:
                self.log('Exception during seek')

        self.showChannelLabel(self.currentChannel)
        self.lastActionTime = time.time()
        self.log('setChannel return')


    def waitForVideoPaused(self):
        self.log('waitForVideoPaused')
        sleeptime = 0

        while sleeptime < TIMEOUT:
            xbmc.sleep(100)

            if xbmc.Player().isPlaying():
                if xbmc.getCondVisibility('Player.Paused'):
                    break

            sleeptime += 100
        else:
            self.Error('Timeout waiting for pause')
            return False

        self.log('waitForVideoPaused return')
        return True


    def waitForVideoStop(self):
        self.log('waitForVideoStop')
        sleeptime = 0

        while sleeptime < TIMEOUT:
            xbmc.sleep(100)

            if xbmc.Player().isPlaying() == False:
                break

            sleeptime += 100
        else:
            self.Error('Timeout waiting for video to stop')
            return False

        self.log('waitForVideoStop return')
        return True


    # run a built-in command and wait for it to take effect
    def startPlaylist(self, command):
        self.log('startPlaylist ' + command)

        if xbmc.Player().isPlaying():
            if xbmc.getCondVisibility('Player.Paused') == False:
                self.log('Pausing')
                xbmc.Player().pause()

                if self.waitForVideoPaused() == False:
                    return

        self.log('Executing command')
        xbmc.executebuiltin(command)
        sleeptime = 0
        self.log('Waiting for video')

        while sleeptime < TIMEOUT:
            xbmc.sleep(100)

            if xbmc.Player().isPlaying():
                try:
                    if xbmc.getCondVisibility('!Player.Paused') and xbmc.Player().getTime() > 0.0:
                        break
                except:
                    self.log('Exception waiting for video to start')
                    pass

            sleeptime += 100

        if sleeptime >= TIMEOUT:
            self.Error('Timeout waiting for video to start')
            return False

        self.log('startPlaylist return')
        return True


    # Display the current channel based on self.currentChannel.
    # Start the timer to hide it.
    def showChannelLabel(self, channel):
        self.log('showChannelLabel ' + str(channel))

        if self.channelLabelTimer.isAlive():
            self.channelLabelTimer.cancel()
            self.channelLabelTimer = threading.Timer(5.0, self.hideChannelLabel)

        tmp = self.inputChannel
        self.hideChannelLabel()
        self.inputChannel = tmp
        curlabel = 0

        if channel > 99:
            self.channelLabel[curlabel].setImage(IMAGES_LOC + 'label_' + str(channel // 100) + '.png')
            self.channelLabel[curlabel].setVisible(True)
            curlabel += 1

        if channel > 9:
            self.channelLabel[curlabel].setImage(IMAGES_LOC + 'label_' + str((channel % 100) // 10) + '.png')
            self.channelLabel[curlabel].setVisible(True)
            curlabel += 1

        self.channelLabel[curlabel].setImage(IMAGES_LOC + 'label_' + str(channel % 10) + '.png')
        self.channelLabel[curlabel].setVisible(True)
        self.channelLabelTimer.start()
        self.log('showChannelLabel return')


    # Called from the timer to hide the channel label.
    def hideChannelLabel(self):
        self.log('hideChannelLabel')
        self.channelLabelTimer = threading.Timer(5.0, self.hideChannelLabel)
        self.inputChannel = -1

        for i in range(3):
            self.channelLabel[i].setVisible(False)

        self.log('hideChannelLabel return')


    # return a channel in the proper range
    def fixChannel(self, channel):
        while channel < 1 or channel > self.maxChannels:
            if channel < 1: channel = self.maxChannels + channel
            if channel > self.maxChannels: channel -= self.maxChannels

        return channel


    # Handle all input while videos are playing
    def onAction(self, act):
        action = act.getId()
        self.log('onAction ' + str(action))

        # Since onAction isnt always called from the same thread (weird),
        # ignore all actions if we're in the middle of processing one
        if self.actionSemaphore.acquire(False) == False:
            self.log('Unable to get semaphore')
            return

        lastaction = time.time() - self.lastActionTime

        # during certain times we just want to discard all input
        if lastaction < 2:
            self.log('Not allowing actions')
            action = ACTION_INVALID

        self.startSleepTimer()

        if action == ACTION_MENU:
            # set the video to upper right
            if self.sleepTimer.isAlive():
                self.sleepTimer.cancel()
                self.sleepTimer = threading.Timer(self.sleepTimeValue, self.sleepAction)

            self.newChannel = 0
            self.myEPG.doModal()

            if self.newChannel != 0:
                self.background.setVisible(True)
                self.setChannel(self.newChannel)
                self.background.setVisible(False)

        elif action == ACTION_PAGEUP:
            # read the configuration and set initial params
            # potentially go through all channels, start the smart playlist,
            # and create a regular playlist out of it.
            self.channelUp()
        elif action == ACTION_PAGEDOWN:
            self.channelDown()
        elif action == ACTION_STOP:
            self.end()
        elif action == ACTION_SELECT_ITEM:
            if self.inputChannel > 0:
                if self.inputChannel != self.currentChannel:
                    self.setChannel(self.inputChannel)

                self.inputChannel = -1
        elif action == ACTION_PLAYER_FORWARD:
            xbmc.executebuiltin("XBMC.PlayerControl(forward)")
        elif action == ACTION_PLAYER_REWIND:
            xbmc.executebuiltin("XBMC.PlayerControl(rewind)")
        elif action == ACTION_NEXT_ITEM:
            xbmc.executebuiltin("XBMC.PlayerControl(next)")
        elif action == ACTION_PREV_ITEM:
            xbmc.executebuiltin("XBMC.PlayerControl(previous)")
        elif action == ACTION_STEP_FOWARD:
           xbmc.executebuiltin("XBMC.PlayerControl(smallskipforward)")
        elif action == ACTION_STEP_BACK:
            xbmc.executebuiltin("XBMC.PlayerControl(smallskipbackward)")
        elif action == ACTION_BIG_STEP_FORWARD:
            xbmc.executebuiltin("XBMC.PlayerControl(bigskipforward)")
        elif action == ACTION_BIG_STEP_BACK:
            xbmc.executebuiltin("XBMC.PlayerControl(bigskipbackward)")
        elif action >= ACTION_NUMBER_0 and action <= ACTION_NUMBER_9:
            if self.inputChannel < 0:
                self.inputChannel = action - ACTION_NUMBER_0
            else:
                if self.inputChannel < 100:
                    self.inputChannel = self.inputChannel * 10 + action - ACTION_NUMBER_0

            self.showChannelLabel(self.inputChannel)

        self.actionSemaphore.release()
        self.log('onAction return')


    def startSleepTimer(self):
        if self.sleepTimer.isAlive():
            self.sleepTimer.cancel()
            self.sleepTimer = threading.Timer(self.sleepTimeValue, self.sleepAction)

        self.sleepTimer.start()


    def sleepAction(self):
        xbmc.log("sleep!!!")
        self.sleepTimer = threading.Timer(self.sleepTimeValue, self.sleepAction)
        # TODO: show some dialog, allow the user to cancel the sleep
        # perhaps modify the sleep time based on the current show
#        self.end()


    # cleanup and end
    def end(self):
        self.log('end')

        if self.channelLabelTimer.isAlive():
            self.channelLabelTimer.cancel()

        if self.sleepTimer.isAlive():
            self.sleepTimer.cancel()

        if xbmc.Player().isPlaying():
            xbmc.Player().stop()

        self.background.setVisible(False)
        self.close()



class EPGWindow(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        self.focusRow = 0
        self.focuaIndex = 0
        self.focusTime = 0
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
            starttime = self.focusTime + (left / 0.1774)
            endtime = starttime + (width / 0.1774)

            if curtime >= starttime and curtime <= endtime:
                self.focusIndex = i
                self.setFocus(self.channelButtons[2][i])
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
        self.focusTime = starttime

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
            self.channelButtons[row].append(xbmcgui.ControlButton(322, 288 + (row * 80), 958, 78, self.MyOverlayWindow.channels[curchannel - 1].getCurrentDescription()))
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
                xpos = 322 + ((totaltime * 0.1774) // 1)
                tmpdur = self.MyOverlayWindow.channels[curchannel - 1].getItemDuration(playlistpos)
                shouldskip = False

                # this should only happen the first time through this loop
                # it shows the small portion of the show before the current one
                if reftime < starttime:
                    tmpdur -= starttime - reftime
                    reftime = starttime

                    if tmpdur < 60 * 3:
                        shouldskip = True

                width = 0.1774 * tmpdur // 1

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
#                     self.hide()
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
            self.setChannelButtons(self.focusTime, self.centerChannel + 1)
            self.focusRow = 3

        self.setProperButton(self.focusRow + 1)
        self.log('goDown return')


    def GoUp(self):
        self.log('goUp')

        # same as godown
        # change controls to display the proper junks
        if self.focusRow == 0:
            self.setChannelButtons(self.focusTime, self.centerChannel - 1)
            self.focusRow = 1

        self.setProperButton(self.focusRow - 1)
        self.log('goUp return')


    def GoLeft(self):
        self.log('goLeft')

        # change controls to display the proper junks
        if self.focusIndex == 0:
            self.setChannelButtons(self.focusTime - 1800, self.centerChannel)
            self.focusIndex = 1

        self.focusIndex -= 1
        self.setFocus(self.channelButtons[self.focusRow][self.focusIndex])
        self.log('goLeft return')


    def GoRight(self):
        self.log('goRight')

        # change controls to display the proper junks
        if self.focusIndex == len(self.channelButtons[self.focusRow]) - 1:
            self.setChannelButtons(self.focusTime + 1800, self.centerChannel)
            self.focusIndex = len(self.channelButtons[self.focusRow]) - 2

        self.focusIndex += 1
        self.setFocus(self.channelButtons[self.focusRow][self.focusIndex])
        self.log('goRight return')


    # based on the current focus row and index, find the appropriate button in
    # the new row to set focus to
    def setProperButton(self, newrow):
        self.log('setProperButton ' + str(newrow))
        left, down = self.channelButtons[self.focusRow][self.focusIndex].getPosition()
        self.focusRow = newrow

        for i in range(len(self.channelButtons[newrow])):
            bleft, bup = self.channelButtons[newrow][i].getPosition()
            width = self.channelButtons[newrow][i].getWidth()

            if left >= bleft and left <= bleft + width:
                self.focusIndex = i
                self.setFocus(self.channelButtons[newrow][i])
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
        starttime = self.focusTime + (left / 0.1774)
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

