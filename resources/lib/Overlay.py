import xbmc, xbmcgui, xbmcaddon
import subprocess, os
import time, threading
import datetime
import sys, re

from Playlist import Playlist
from Globals import *
from Channel import Channel
from EPGWindow import EPGWindow



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
        self.timeStarted = 0

        for i in range(3):
            self.channelLabel.append(xbmcgui.ControlImage(50 + (50 * i), 50, 50, 50, IMAGES_LOC + 'solid.png', colorDiffuse='0xAA00ff00'))
            self.addControl(self.channelLabel[i])
            self.channelLabel[i].setVisible(False)

        self.doModal()
        self.log('__init__ return')


    def resetChannelTimes(self):
        curtime = time.time()

        for i in range(self.maxChannels):
            self.channels[i].setAccessTime(curtime - self.channels[i].totalTimePlayed)


    def onFocus(self, controlId):
        pass


    # override the doModal function so we can setup everything first
    def onInit(self):
        self.log('onInit')
        self.channelLabelTimer = threading.Timer(5.0, self.hideChannelLabel)
        self.background = self.getControl(101)

        if not os.path.exists(CHANNELS_LOC):
            try:
                os.makedirs(CHANNELS_LOC)
            except:
                self.Error('Unable to create the cache directory')
                return

        self.myEPG = EPGWindow("script.PseudoTV.EPG.xml", ADDON_INFO, "Default")
        self.myEPG.MyOverlayWindow = self
        self.findMaxChannels()

        if self.maxChannels == 0:
            self.Error('Unable to find any channels. Create smart\nplaylists with file names Channel_1, Chanbel_2, etc.')
            return

        # Don't allow any actions during initialization
        self.actionSemaphore.acquire()

        if self.readConfig() == False:
            return

        if self.sleepTimeValue > 0:
            self.sleepTimer = threading.Timer(self.sleepTimeValue, self.sleepAction)

        self.resetChannelTimes()
        self.setChannel(self.currentChannel)
        self.timeStarted = time.time()
        self.background.setVisible(False)
        self.startSleepTimer()
        self.actionSemaphore.release()
        self.log('onInit return')


    # Determine the maximum number of channels by opening consecutive
    # playlists until we don't find one
    def findMaxChannels(self):
        self.log('findMaxChannels')
        notfound = False
        channel = 1

        while notfound == False:
            if len(self.getSmartPlaylistFilename(channel)) == 0:
                break

            channel += 1

        self.maxChannels = channel - 1
        self.log('findMaxChannels return ' + str(self.maxChannels))


    # setup all basic configuration parameters, including creating the playlists that
    # will be used to actually run this thing
    def readConfig(self):
        self.log('readConfig')
        self.updateDialog = xbmcgui.DialogProgress()
        # Sleep setting is in 30 minute incriments...so multiply by 30, and then 60 (min to sec)
        self.sleepTimeValue = int(ADDON_SETTINGS.getSetting('AutoOff')) * 1800
        self.log('Auto off is ' + str(self.sleepTimeValue))
        forcereset = ADDON_SETTINGS.getSetting('ForceChannelReset') == "true"
        self.log('Force Reset is ' + str(forcereset))
        self.startupTime = time.time()
        self.updateDialog.create("PseudoTV", "Updating channel list")
        self.updateDialog.update(0, "Updating channel list")
        self.background.setVisible(True)

        # Go through all channels, create their arrays, and setup the new playlist
        for i in range(self.maxChannels):
            self.updateDialog.update(i * 100 // self.maxChannels, "Updating channel list")
            self.channels.append(Channel())
            createlist = True

            # If the user pressed cancel, stop everything and exit
            if self.updateDialog.iscanceled():
                self.log('Update channels cancelled')
                self.updateDialog.close()
                self.end()
                return False

            # If possible, use an existing playlist
            if os.path.exists(CHANNELS_LOC + 'channel_' + str(i + 1) + '.m3u'):
                try:
                    self.channels[-1].totalTimePlayed = int(ADDON_SETTINGS.getSetting('Channel_' + str(i + 1) + '_time'))
                    self.channels[-1].setPlaylist(CHANNELS_LOC + 'channel_' + str(i + 1) + '.m3u')

                    # If this channel has been watched for longer than it lasts, reset the channel
                    # Really, this should only apply when the order is random
                    if self.channels[-1].totalTimePlayed < self.channels[-1].getTotalDuration():
                        createlist = forcereset
                except:
                    pass

            if createlist:
                if self.makeChannelList(i + 1) == False:
                    self.updateDialog.close()
                    return False

                self.channels[-1].setPlaylist(CHANNELS_LOC + 'channel_' + str(i + 1) + '.m3u')
                self.channels[-1].totalTimePlayed = 0
                ADDON_SETTINGS.setSetting('Channel_' + str(i + 1) + '_time', '0')

            self.channels[-1].name = self.getSmartPlaylistName(self.getSmartPlaylistFilename(i + 1))

        ADDON_SETTINGS.setSetting('ForceChannelReset', 'false')
        self.currentChannel = 1
        xbmc.Player().stop()
        self.updateDialog.close()
        self.log('readConfig return')
        return True


    def getSmartPlaylistFilename(self, channel):
        if os.path.exists(xbmc.translatePath('special://profile/playlists/video') + '/Channel_' + str(channel) + '.xsp'):
            return xbmc.translatePath('special://profile/playlists/video') + '/Channel_' + str(channel) + '.xsp'
#        elif os.path.exists(xbmc.translatePath('special://profile/playlists/mixed') + '/Channel_' + str(channel) + '.xsp'):
#            return xbmc.translatePath('special://profile/playlists/mixed') + '/Channel_' + str(channel) + '.xsp'
        else:
            return ''


    # Open the smart playlist and read the name out of it...this is the channel name
    def getSmartPlaylistName(self, filename):
        self.log('getSmartPlaylistName ' + filename)

        try:
            fl = open(filename, "r")
        except:
            self.log("Unable to open the smart playlist " + filename, xbmc.LOGERROR)
            return ''

        line = fl.readline()
        thename = ''

        while len(line) > 0:
            index1 = line.find('<name>')

            if index1 >= 0:
                index2 = line.find('</name>')

                if index2 > index1 + 6:
                    thename = line[index1 + 6:index2]
                    break

            line = fl.readline()

        fl.close()
        self.log('getSmartPlaylistName return ' + thename)
        return thename


    # handle fatal errors: log it, show the dialog, and exit
    def Error(self, message):
        self.log('FATAL ERROR: ' + message, xbmc.LOGFATAL)
        dlg = xbmcgui.Dialog()
        dlg.ok('Error', message)
        del dlg
        self.end()


    # Based on a smart playlist, create a normal playlist that can actually be used by us
    def makeChannelList(self, channel):
        self.log('makeChannelList ' + str(channel))
        fle = self.getSmartPlaylistFilename(channel)

        if len(fle) == 0:
            self.Error('Unable to locate the playlist for channel ' + str(channel))
            return False
            
        fileList = self.buildFileList(fle)
        
        try:
            channelplaylist = open(CHANNELS_LOC + "channel_" + str(channel) + ".m3u", "w")
        except:
            self.Error('Unable to open the cache file ' + CHANNELS_LOC + 'channel_' + str(channel) + '.m3u')
            return False

        channelplaylist.write("#EXTM3U\n")
        updatebase = (channel - 1) * 100.0 / self.maxChannels
        totalchanrange = 100.0 / self.maxChannels
        itemsize = totalchanrange / len(fileList)
        lastval = 0

        # Write each entry into the new playlist
        for i in range(len(fileList)):
            duration = self.getDurationForFile(fileList[i])

            if duration > 0:
                data = self.getInformation(fileList[i])
                channelplaylist.write("#EXTINF:" + str(duration) + "," + data + "\n")
                channelplaylist.write(fileList[i] + "\n")
            else:
                self.log("Can't get duration: " + fileList[i], xbmc.LOGERROR)

            if (i + 1) * itemsize // 1 > lastval:
                self.updateDialog.update(updatebase + ((i + 1) * itemsize), "Updating channel list")
                lastval = (i + 1) * itemsize // 1

        channelplaylist.close()
        self.log('makeChannelList return')
        return True
        
            
    def buildFileList( self, dir_name, media_type="files", recursive="TRUE", contains="" ):
        fileList = []
        json_query = '{"jsonrpc": "2.0", "method": "Files.GetDirectory", "params": {"directory": "%s", "media": "%s", "recursive": "%s"}, "id": 1}' % ( self.escapeDirJSON( dir_name ), media_type, recursive )
        json_folder_detail = xbmc.executeJSONRPC(json_query)
        file_detail = re.compile( "{(.*?)}", re.DOTALL ).findall(json_folder_detail)
        for f in file_detail:
            match = re.search( '"file" : "(.*?)",', f )
            if match:
                if ( match.group(1).endswith( "/" ) or match.group(1).endswith( "\\" ) ):
                    if ( recursive == "TRUE" ):
                        fileList.extend( self.buildFileList( match.group(1), media_type, recursive, contains ) )
                elif not contains or ( contains and (contains in match.group(1) ) ):
                    fileList.append( match.group(1) )
            else:
                continue
        return fileList
        
        
    def escapeDirJSON ( self, dir_name ):
        if (dir_name.find(":")):
            dir_name = dir_name.replace("\\", "\\\\")
        return dir_name    


    # Return a string wirh the needed show information
    def getInformation(self, filename):
        self.log('getInformation ' + filename)
        fileid = self.getFileId(filename)
        epid = self.getEpisodeId(fileid)

        if epid > -1:
            self.log('getInformation episode return')
            return self.getEpisodeInformation(epid)

        movieid = self.getMovieId(fileid)
        self.log('getInformation movie return')
        return self.getMovieInformation(movieid)


    def getFileId(self, filename):
        if len(filename) == 0:
            self.log('getFileId no filename')
            return -1

        # determine the filename and path
        path, name = os.path.split(filename)

        if filename.find('/') > -1:
            path += '/'
        else:
            path += '\\'

        # Get past a bug in the http api that turns all commas into semi-colons
        name = name.replace(',', '%2C')
        path = path.replace(',', '%2C')
        # construct the query

        query = 'select files.idFile from files where files.strFilename="' + name + '" and files.idPath in ' \
            '(select path.idPath from path where path.strPath="' + path + '")'
        #run the query
        data = xbmc.executehttpapi('QueryVideoDatabase(' + query + ')')

        try:
            return int(self.parseQuery(data))
        except:
            return -1


    def parseQuery(self, data):
        if len(data) > 15:
            # parse the result
            index1 = data.find('<field>')

            # parse the result
            if index1 >= 0:
                index2 = data.find('</field>')

                if index2 > (index1 + 7):
                    return data[index1 + 7:index2]

        return ''


    def getEpisodeInformation(self, episodeid):
        self.log('getEpisodeInformation')
        # Want to use JSON, but GetEpisodeDetails isn't in the mainstream release yet
#        retv = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodeDetails", "params": {"episodeid": ' + str(epid) + '}, "id": 1}')
        # Get the TV show title
        query = 'select tvshow.c00 from tvshow where tvshow.idShow in' \
            '(select tvshowlinkepisode.idShow from tvshowlinkepisode where tvshowlinkepisode.idEpisode=' + str(episodeid) + ')'
        data = xbmc.executehttpapi('QueryVideoDatabase(' + query + ')')
        result = self.parseQuery(data)
        # Get the episode title and description
        query = 'select episode.c00 from episode where episode.idEpisode=' + str(episodeid)
        data = xbmc.executehttpapi('QueryVideoDatabase(' + query + ')')
        result += '//' + self.parseQuery(data)
        query = 'select episode.c01 from episode where episode.idEpisode=' + str(episodeid)
        data = xbmc.executehttpapi('QueryVideoDatabase(' + query + ')')
        result += '//' + self.parseQuery(data)
        self.log('getEpisodeInformation return')
        return result


    def getMovieInformation(self, movieid):
        self.log('getMovieInformation')
        # Get the episode title and description
        query = 'select movie.c00 from movie where movie.idMovie=' + str(movieid)
        data = xbmc.executehttpapi('QueryVideoDatabase(' + query + ')')
        self.log('1-' + data)
        result = self.parseQuery(data) + '//'
        query = 'select movie.c03 from movie where movie.idMovie=' + str(movieid)
        data = xbmc.executehttpapi('QueryVideoDatabase(' + query + ')')
        self.log('2-' + data)
        result += self.parseQuery(data) + '//'
        query = 'select movie.c01 from movie where movie.idMovie=' + str(movieid)
        data = xbmc.executehttpapi('QueryVideoDatabase(' + query + ')')
        self.log('3-' + data)
        result += self.parseQuery(data)
        self.log('getMovieInformation return')
        return result


    def getEpisodeId(self, fileid):
        query = 'select episode.idEpisode from episode where episode.idFile=' + str(fileid)
        #run the query
        data = xbmc.executehttpapi('QueryVideoDatabase(' + query + ')')

        try:
            return int(self.parseQuery(data))
        except:
            return -1


    def getMovieId(self, fileid):
        query = 'select movie.idMovie from movie where movie.idFile=' + str(fileid)
        #run the query
        data = xbmc.executehttpapi('QueryVideoDatabase(' + query + ')')

        try:
            return int(self.parseQuery(data))
        except:
            return -1


    # since the playlist isn't properly returning the duration, get it from the database
    def getDurationForFile(self, filename):
        self.log('getDurationForFile ' + filename)

        if len(filename) == 0:
            self.log('getDurationForFile return no filename')
            return 0

        # determine the filename and path
        path, name = os.path.split(filename)

        if filename.find('/') > -1:
            path += '/'
        else:
            path += '\\'

        # Get past a bug in the http api that turns all commas into semi-colons
        name = name.replace(',', '%2C')
        path = path.replace(',', '%2C')
        # construct the query
        query = 'select streamdetails.iVideoDuration from streamdetails where streamdetails.iStreamType=0 and streamdetails.idFile in' \
            '(select files.idFile from files where files.strFilename="' + name + '" and files.idPath in' \
            '(select path.idPath from path where path.strPath="' + path + '"))'
        #run the query
        data = xbmc.executehttpapi('QueryVideoDatabase(' + query + ')')

        try:
            x = int(self.parseQuery(data))
            self.log('getDurationForFile return ' + str(x))
            return x
        except:
            self.log('getDurationForFile return 0')
            return 0


    def channelDown(self):
        self.log('channelDown')

        if self.maxChannels == 1:
            return

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

        if self.maxChannels == 1:
            return

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


    def log(self, msg, level = xbmc.LOGDEBUG):
        log('TVOverlay: ' + msg, level)


    # set the channel, the proper show offset, and time offset
    def setChannel(self, channel):
        self.log('setChannel ' + str(channel))

        if channel < 1 or channel > self.maxChannels:
            self.log('setChannel invalid channel ' + str(channel), xbmc.LOGERROR)
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

            xbmc.executebuiltin("XBMC.PlayerControl(repeatall)")

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
                self.log('Exception during seek on paused channel', xbmc.LOGERROR)
        else:
            seektime = self.channels[self.currentChannel - 1].showTimeOffset + timedif

            try:
                xbmc.Player().seekTime(seektime)
            except:
                self.log('Exception during seek', xbmc.LOGERROR)

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
                    return False

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

        if action == ACTION_SELECT_ITEM:
            # If we're manually typing the channel, set it now
            if self.inputChannel > 0:
                if self.inputChannel != self.currentChannel:
                    self.setChannel(self.inputChannel)

                self.inputChannel = -1
            else:
                # Otherwise, show the EPG
                if self.sleepTimeValue > 0:
                    if self.sleepTimer.isAlive():
                        self.sleepTimer.cancel()
                        self.sleepTimer = threading.Timer(self.sleepTimeValue, self.sleepAction)

                self.newChannel = 0
                self.myEPG.doModal()

                if self.newChannel != 0:
                    self.background.setVisible(True)
                    self.setChannel(self.newChannel)
                    self.background.setVisible(False)
        elif action == ACTION_MOVE_UP:
            self.channelUp()
        elif action == ACTION_MOVE_DOWN:
            self.channelDown()
        elif action == ACTION_STOP:
            self.end()
        elif action >= ACTION_NUMBER_0 and action <= ACTION_NUMBER_9:
            if self.inputChannel < 0:
                self.inputChannel = action - ACTION_NUMBER_0
            else:
                if self.inputChannel < 100:
                    self.inputChannel = self.inputChannel * 10 + action - ACTION_NUMBER_0

            self.showChannelLabel(self.inputChannel)

        self.actionSemaphore.release()
        self.log('onAction return')


    # Reset the sleep timer
    def startSleepTimer(self):
        if self.sleepTimeValue == 0:
            return

        # Cancel the timer if itbis still running
        if self.sleepTimer.isAlive():
            self.sleepTimer.cancel()
            self.sleepTimer = threading.Timer(self.sleepTimeValue, self.sleepAction)

        self.sleepTimer.start()


    # This is called when the sleep timer expires
    def sleepAction(self):
        self.log("sleepAction")
        self.actionSemaphore.acquire()
#        self.sleepTimer = threading.Timer(self.sleepTimeValue, self.sleepAction)
        # TODO: show some dialog, allow the user to cancel the sleep
        # perhaps modify the sleep time based on the current show
        self.end()
        self.actionSemaphore.release()


    # cleanup and end
    def end(self):
        self.log('end')

        try:
            if self.channelLabelTimer.isAlive():
                self.channelLabelTimer.cancel()

            if self.sleepTimeValue > 0:
                if self.sleepTimer.isAlive():
                    self.sleepTimer.cancel()
        except:
            pass

        if xbmc.Player().isPlaying():
            xbmc.Player().stop()

        if self.timeStarted > 0:
            for i in range(self.maxChannels):
                ADDON_SETTINGS.setSetting('Channel_' + str(i + 1) + '_time', str(int(time.time() - self.timeStarted + self.channels[i].totalTimePlayed)))

        self.background.setVisible(False)
        self.close()
