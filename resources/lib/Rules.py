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
from Playlist import PlaylistItem



class RulesList:
    def __init__(self):
        self.ruleList = [BaseRule(), RenameRule(), NoShowRule(), ScheduleChannelRule(), OnlyWatchedRule(), DontAddChannel(), InterleaveChannel(), ForceRealTime(), AlwaysPause(), ForceResume(), ForceRandom(), OnlyUnWatchedRule()]


    def getRuleCount(self):
        return len(self.ruleList)


    def getRule(self, index):
        while index < 0:
            index += len(self.ruleList)

        while index >= len(self.ruleList):
            index -= len(self.ruleList)

        return self.ruleList[index]



class BaseRule:
    def __init__(self):
        self.name = ""
        self.description = ""
        self.optionLabels = []
        self.optionValues = []
        self.myId = 0
        self.actions = 0


    def getName(self):
        return self.name


    def getOptionCount(self):
        return len(self.optionLabels)


    def onAction(self, act, optionindex):
        return ''


    def getOptionLabel(self, index):
        if index >= 0 and index < self.getOptionCount():
            return self.optionLabels[index]

        return ''


    def getOptionValue(self, index):
        if index >= 0 and index < len(self.optionValues):
            return self.optionValues[index]

        return ''


    def getRuleIndex(self, channeldata):
        index = 0

        for rule in channeldata.ruleList:
            if rule == self:
                return index

            index += 1

        return -1


    def getId(self):
        return self.myId


    def runAction(self, actionid, channelList, param):
        return param


    def copy(self):
        return BaseRule()


    def log(self, msg):
        log("Rule " + self.name + ": " + msg)


    def validate(self):
        pass


    def reset(self):
        self.__init__()


    def validateTextBox(self, optionindex, length):
        if len(self.optionValues[optionindex]) > length:
            self.optionValues[optionindex] = self.optionValues[optionindex][:length]


    def onActionTextBox(self, act, optionindex):
        if act.getId() == ACTION_SELECT_ITEM:
            keyb = xbmc.Keyboard(self.optionValues[optionindex], self.name, False)
            keyb.doModal()

            if keyb.isConfirmed():
                self.optionValues[optionindex] = keyb.getText()

        button = act.getButtonCode()

        # Upper-case values
        if button >= 0x2f041 and button <= 0x2f05b:
            self.optionValues[optionindex] += chr(button - 0x2F000)

        # Lower-case values
        if button >= 0xf041 and button <= 0xf05b:
            self.optionValues[optionindex] += chr(button - 0xEFE0)

        # Numbers
        if button >= 0xf030 and button <= 0xf039:
            self.optionValues[optionindex] += chr(button - 0xF000)

        # Backspace
        if button == 0xF008:
            if len(self.optionValues[optionindex]) >= 1:
                self.optionValues[optionindex] = self.optionValues[optionindex][:-1]

        # Delete
        if button == 0xF02E:
            self.optionValues[optionindex] = ''

        # Space
        if button == 0xF020:
            self.optionValues[optionindex] += ' '


    def onActionDateBox(self, act, optionindex):
        self.log("onActionDateBox")

        if act.getId() == ACTION_SELECT_ITEM:
            dlg = xbmcgui.Dialog()
            info = dlg.numeric(1, self.optionLabels[optionindex], self.optionValues[optionindex])

            if info != None:
                self.optionValues[optionindex] = info


    def onActionTimeBox(self, act, optionindex):
        self.log("onActionTimeBox")

        if act.getId() == ACTION_SELECT_ITEM:
            dlg = xbmcgui.Dialog()
            info = dlg.numeric(2, self.optionLabels[optionindex], self.optionValues[optionindex])

            if info[0] == ' ':
                info = info[1:]

            if len(info) == 4:
                info = "0" + info

            self.optionValues[optionindex] = info

        button = act.getButtonCode()

        # Numbers
        if button >= 0xF030 and button <= 0xF039:
            value = button - 0xF030
            length = len(self.optionValues[optionindex])

            if length == 0:
                if value <= 2:
                    self.optionValues[optionindex] = chr(button - 0xF000)
            elif length == 1:
                if int(self.optionValues[optionindex][0]) == 2:
                    if value < 4:
                        self.optionValues[optionindex] += chr(button - 0xF000)
                else:
                    self.optionValues[optionindex] += chr(button - 0xF000)
            elif length == 2:
                if value < 6:
                    self.optionValues[optionindex] += ":" + chr(button - 0xF000)
            elif length < 5:
                self.optionValues[optionindex] += chr(button - 0xF000)

        # Backspace
        if button == 0xF008:
            if len(self.optionValues[optionindex]) >= 1:
                if len(self.optionValues[optionindex]) == 4:
                    self.optionValues[optionindex] = self.optionValues[optionindex][:-1]

                self.optionValues[optionindex] = self.optionValues[optionindex][:-1]


    def validateTimeBox(self, optionindex):
        if len(self.optionValues[optionindex]) != 5 or self.optionValues[optionindex][2] != ':':
            self.optionValues[optionindex] = "00:00"
            return

        values = []
        broken = False

        try:
            values.append(int(self.optionValues[optionindex][0]))
            values.append(int(self.optionValues[optionindex][1]))
            values.append(int(self.optionValues[optionindex][3]))
            values.append(int(self.optionValues[optionindex][4]))
        except:
            self.optionValues[optionindex] = "00:00"
            return

        if values[0] > 2:
            broken = True

        if values[0] == 2:
            if values[1] > 3:
                broken = True

        if values[2] > 5:
            broken = True

        if broken:
            self.optionValues[optionindex] = "00:00"
            return


    def onActionDaysofWeekBox(self, act, optionindex):
        self.log("onActionDaysofWeekBox")

        if act.getId() == ACTION_SELECT_ITEM:
            keyb = xbmc.Keyboard(self.optionValues[optionindex], self.name, False)
            keyb.doModal()

            if keyb.isConfirmed():
                self.optionValues[optionindex] = keyb.getText().upper()

        button = act.getButtonCode()

        # Remove the shift key if it's there
        if button >= 0x2F041 and button <= 0x2F05B:
            button -= 0x20000

        # Pressed some character
        if button >= 0xF041 and button <= 0xF05B:
            button -= 0xF000

            # Check for UMTWHFS
            if button == 85 or button == 77 or button == 84 or button == 87 or button == 72 or button == 70 or button == 83:
                # Check to see if it's already in the string
                loc = self.optionValues[optionindex].find(chr(button))

                if loc != -1:
                    self.log("Removing key")
                    self.optionValues[optionindex] = self.optionValues[optionindex][:loc] + self.optionValues[optionindex][loc + 1:]
                else:
                    self.log("Adding key")
                    self.optionValues[optionindex] += chr(button)

        # Backspace
        if button == 0xF008:
            if len(self.optionValues[optionindex]) >= 1:
                self.optionValues[optionindex] = self.optionValues[optionindex][:-1]


    def validateDaysofWeekBox(self, optionindex):
        self.log("validateDaysofWeekBox")
        daysofweek = "UMTWHFS"
        newstr = ''

        for day in daysofweek:
            loc = self.optionValues[optionindex].find(day)

            if loc != -1:
                newstr += day

        self.optionValues[optionindex] = newstr


    def validateDigitBox(self, optionindex, minimum, maximum, default):
        if len(self.optionValues[optionindex]) == 0:
            return

        try:
            val = int(self.optionValues[optionindex])

            if val >= minimum and val <= maximum:
                self.optionValues[optionindex] = str(val)

            return
        except:
            pass

        self.optionValues[optionindex] = str(default)


    def onActionDigitBox(self, act, optionindex):
        if act.getId() == ACTION_SELECT_ITEM:
            dlg = xbmcgui.Dialog()
            value = dlg.numeric(0, self.optionLabels[optionindex], self.optionValues[optionindex])
            self.optionValues[optionindex] = value

        button = act.getButtonCode()

        # Numbers
        if button >= 0xf030 and button <= 0xf039:
            self.optionValues[optionindex] += chr(button - 0xF000)

        # Backspace
        if button == 0xF008:
            if len(self.optionValues[optionindex]) >= 1:
                self.optionValues[optionindex] = self.optionValues[optionindex][:-1]

        # Delete
        if button == 0xF02E:
            self.optionValues[optionindex] = ''



class RenameRule(BaseRule):
    def __init__(self):
        self.name = "Set Channel Name"
        self.optionLabels = ['New Channel Name']
        self.optionValues = ['']
        self.myId = 1
        self.actions = RULES_ACTION_FINAL_MADE | RULES_ACTION_FINAL_LOADED


    def copy(self):
        return RenameRule()


    def onAction(self, act, optionindex):
        self.onActionTextBox(act, optionindex)
        self.validate()
        return self.optionValues[optionindex]


    def validate(self):
        self.validateTextBox(0, 18)


    def runAction(self, actionid, channelList, channeldata):
        if actionid == RULES_ACTION_FINAL_MADE or actionid == RULES_ACTION_FINAL_LOADED:
            self.validate()
            channeldata.name = self.optionValues[0]

        return channeldata



class NoShowRule(BaseRule):
    def __init__(self):
        self.name = "Don't Include a Show"
        self.optionLabels = ['Show Name']
        self.optionValues = ['']
        self.myId = 2
        self.actions = RULES_ACTION_LIST


    def copy(self):
        return NoShowRule()


    def onAction(self, act, optionindex):
        self.onActionTextBox(act, optionindex)
        self.validate()
        return self.optionValues[optionindex]


    def validate(self):
        self.validateTextBox(0, 20)


    def runAction(self, actionid, channelList, filelist):
        if actionid == RULES_ACTION_LIST:
            self.validate()
            opt = self.optionValues[0].lower()
            realindex = 0

            for index in range(len(filelist)):
                item = filelist[realindex]
                loc = item.find(',')

                if loc > -1:
                    loc2 = item.find("//")

                    if loc2 > -1:
                        showname = item[loc + 1:loc2]
                        showname = showname.lower()

                        if showname.find(opt) > -1:
                            filelist.pop(realindex)
                            realindex -= 1

                realindex += 1

        return filelist



class ScheduleChannelRule(BaseRule):
    def __init__(self):
        self.name = "Best-Effort Channel Scheduling"
        self.optionLabels = ['Channel Number', 'Days of the Week (UMTWHFS)', 'Time (HH:MM)', 'Episode Count', 'Starting Episode', 'Starting Date']
        self.optionValues = ['0', '', '00:00', '1', '1', '']
        self.myId = 3
        self.actions = RULES_ACTION_START | RULES_ACTION_BEFORE_CLEAR | RULES_ACTION_FINAL_MADE | RULES_ACTION_FINAL_LOADED
        self.clearedcount = 0
        self.appended = False
        self.hasRun = False
        self.nextScheduledTime = 0
        self.startIndex = 0


    def copy(self):
        return ScheduleChannelRule()


    def onAction(self, act, optionindex):
        if optionindex == 0:
            self.onActionDigitBox(act, optionindex)

        if optionindex == 1:
            self.onActionDaysofWeekBox(act, optionindex)

        if optionindex == 2:
            self.onActionTimeBox(act, optionindex)

        if optionindex == 3:
            self.onActionDigitBox(act, optionindex)

        if optionindex == 4:
            self.onActionDigitBox(act, optionindex)

        if optionindex == 5:
            self.onActionDateBox(act, optionindex)

        self.validate()
        return self.optionValues[optionindex]


    def validate(self):
        self.validateDigitBox(0, 1, 1000, '')
        self.validateDaysofWeekBox(1)
        self.validateTimeBox(2)
        self.validateDigitBox(3, 1, 1000, 1)
        self.validateDigitBox(4, 1, 1000, 1)


    def runAction(self, actionid, channelList, channeldata):
        self.log("runAction " + str(actionid))

        if actionid == RULES_ACTION_START:
            self.clearedcount = 0
            self.hasRun = False
            self.nextScheduledTime = 0

        if actionid == RULES_ACTION_BEFORE_CLEAR:
            self.clearedcount = channeldata.Playlist.size()

            if channeldata.totalTimePlayed > 0:
                self.appended = True
            else:
                self.appended = False

        if (actionid == RULES_ACTION_FINAL_MADE or actionid == RULES_ACTION_FINAL_LOADED) and (self.hasRun == False):
            self.runSchedulingRules(channelList, channeldata)

        return channeldata


    def runSchedulingRules(self, channelList, channeldata):
        self.log("runSchedulingRules")
        curchan = channelList.runningActionChannel
        self.hasRun = True

        try:
            self.startIndex = int(ADDON_SETTINGS.getSetting('Channel_' + str(curchan) + '_lastscheduled'))
        except:
            self.startIndex = 0

        if self.appended == True:
            self.startIndex -= self.clearedcount - channeldata.Playlist.size()

        if self.startIndex < channeldata.playlistPosition:
            self.startIndex = channeldata.fixPlaylistIndex(channeldata.playlistPosition + 1)

            if self.startIndex == 0:
                self.log("Currently playing the last item, odd")
                return

        # Have all scheduling rules determine the next scheduling time
        self.determineNextTime()
        minimum = self

        for rule in channeldata.ruleList:
            if rule.getId() == self.myId:
                if rule.nextScheduledTime == 0:
                    rule.determineNextTime()

                rule.startIndex = self.startIndex
                rule.hasRun = True

                if rule.nextScheduledTime < minimum.nextScheduledTime or minimum.nextScheduledTime == 0:
                    minimum = rule

        added = True
        newstart = 0

        while added == True and minimum.nextScheduledTime != 0:
            added = minimum.addScheduledShow(channelList, channeldata)
            newstart = minimum.startIndex

            # Determine the new minimum
            if added:
                minimum.determineNextTime()

                for rule in channeldata.ruleList:
                    if rule.getId() == self.myId:
                        rule.startIndex = newstart

                        if rule.nextScheduledTime < minimum.nextScheduledTime or minimum.nextScheduledTime == 0:
                            minimum = rule

        ADDON_SETTINGS.setSetting('Channel_' + str(curchan) + '_lastscheduled', str(newstart))
        # Write the channel playlist to a file
        channeldata.Playlist.save(CHANNELS_LOC + 'channel_' + str(curchan) + '.m3u')


    # Fill in nextScheduledTime
    def determineNextTime(self):
        self.optionValues[5] = self.optionValues[5].replace(' ', '0')
        self.log("determineNextTime " + self.optionValues[5] + " " + self.optionValues[2])
        starttime = 0
        daysofweek = 0

        try:
            starttime = time.mktime(time.strptime(self.optionValues[5] + " " + self.optionValues[2], xbmc.getRegion("dateshort") + " %H:%M"))
        except:
            self.log("Invalid date or time")
            self.nextScheduledTime = 0
            return

        try:
            tmp = self.optionValues[1]

            if tmp.find('M') > -1:
                daysofweek |= 1

            if tmp.find('T') > -1:
                daysofweek |= 2

            if tmp.find('W') > -1:
                daysofweek |= 4

            if tmp.find('H') > -1:
                daysofweek |= 8

            if tmp.find('F') > -1:
                daysofweek |= 16

            if tmp.find('S') > -1:
                daysofweek |= 32

            if tmp.find('U') > -1:
                daysofweek |= 64
        except:
            self.log("Invalid date or time")
            self.nextScheduledTime = 0
            return

        thedate = datetime.datetime.fromtimestamp(starttime)
        delta = datetime.timedelta(days=1)

        # If no day selected, assume every day
        if daysofweek == 0:
            daysofweek = 127

        # Determine the proper day of the week
        while True:
            if daysofweek & (1 << thedate.weekday()) > 0:
                break

            thedate += delta

        self.nextScheduledTime = int(time.mktime(thedate.timetuple()))
        self.log("Current Time is " + str(int(time.time())))
        self.log("Scheduled time is " + str(int(self.nextScheduledTime)))


    def saveOptions(self, channeldata):
        curchan = channeldata.channelNumber
        curruleid = self.getRuleIndex(channeldata) + 1
        ADDON_SETTINGS.setSetting('Channel_' + str(curchan) + '_rule_' + str(curruleid) + '_opt_5', self.optionValues[4])
        ADDON_SETTINGS.setSetting('Channel_' + str(curchan) + '_rule_' + str(curruleid) + '_opt_6', self.optionValues[5])


    # Add a single show (or shows) to the channel at nextScheduledTime
    # This needs to modify the startIndex value if something is added
    def addScheduledShow(self, channelList, channeldata):
        self.log("addScheduledShow")
        chan = 0
        epcount = 0
        startingep = 0
        curchan = channeldata.channelNumber
        curruleid = self.getRuleIndex(channeldata)
        currentchantime = channelList.lastExitTime + channeldata.totalTimePlayed

        if channeldata.Playlist.size() == 0:
            return False

        try:
            chan = int(self.optionValues[0])
            epcount = int(self.optionValues[3])
            startingep = int(self.optionValues[4]) - 1
        except:
            pass

        if startingep < 0:
            startingep = 0

        # If the next scheduled show has already passed, then skip it
        if currentchantime > self.nextScheduledTime:
            thedate = datetime.datetime.fromtimestamp(self.nextScheduledTime)
            delta = datetime.timedelta(days=1)
            thedate += delta
            self.optionValues[4] = str(startingep + epcount)
            self.optionValues[5] = thedate.strftime(xbmc.getRegion("dateshort"))
            self.log("Past the scheduled date and time, skipping")
            self.saveOptions(channeldata)
            return True

        if chan > channelList.maxChannels or chan < 1 or epcount < 1:
            self.log("channel number is invalid")
            return False

        # Should only do this if necessary
        channelList.setupChannel(chan, True, True, False)

        if channelList.channels[chan - 1].Playlist.size() < 1:
            self.log("scheduled channel isn't valid")
            return False

        timedif = self.nextScheduledTime - (time.time() - channeldata.totalTimePlayed)
        self.log("timedif is " + str(timedif))
        showindex = 0

        # Find the proper location to insert the show(s)
        while timedif > 120:
            self.log("show index is " + str(showindex) + ", dur is " + str(channeldata.getItemDuration(showindex)))
            timedif -= channeldata.getItemDuration(showindex)
            self.log("timedif is " + str(timedif))
            showindex = channeldata.fixPlaylistIndex(showindex + 1)

            # Shows that there was a looparound, so exit.
            if showindex == 0:
                self.log("Couldn't find a location for the show")
                return False

        # If there is nothing after the selected show index and the time is still
        # too far away, don't do anything
        if (channeldata.Playlist.size() - (showindex + 1) <= 0) and (timedif < -300):
            return False

        # rearrange episodes to get an optimal time
        if timedif < -300 and channeldata.isRandom:
            # This is a crappy way to do it, but implementing a subset sum algorithm is
            # a bit daunting at the moment
            lasttime = int(abs(timedif))

            # Try a maximum of 5 loops
            for loops in range(5):
                self.log("Starting rearrange loop " + str(loops + 1))
                newtime = self.rearrangeShows(showindex, lasttime, channeldata, channelList)

                if channelList.threadPause() == False:
                    return False

                # If no match found, then stop
                # If the time difference is less than 2 minutes, also stop
                if newtime == lasttime or newtime < 120:
                    self.log("newtime is " + str(newtime) + ", breaking")
                    break

                lasttime = newtime

            self.log("final difference is " + str(lasttime))

        for i in range(epcount):
            item = PlaylistItem()
            item.duration = channelList.channels[chan - 1].getItemDuration(startingep + i)
            item.filename = channelList.channels[chan - 1].getItemFilename(startingep + i)
            item.description = channelList.channels[chan - 1].getItemDescription(startingep + i)
            item.title = channelList.channels[chan - 1].getItemTitle(startingep + i)
            item.episodetitle = channelList.channels[chan - 1].getItemEpisodeTitle(startingep + i)
            channeldata.Playlist.itemlist.insert(showindex, item)
            channeldata.Playlist.totalDuration += item.duration
            showindex += 1

        thedate = datetime.datetime.fromtimestamp(self.nextScheduledTime)
        delta = datetime.timedelta(days=1)
        thedate += delta
        self.startIndex = showindex
        self.optionValues[4] = str(startingep + epcount + 1)
        self.optionValues[5] = thedate.strftime(xbmc.getRegion("dateshort"))
        self.saveOptions(channeldata)
        self.log("successfully scheduled")
        return True


    def rearrangeShows(self, showindex, timedif, channeldata, channelList):
        self.log("rearrangeShows " + str(showindex) + " " + str(timedif))
        self.log("start index: " + str(self.startIndex) + ", end index: " + str(showindex))
        matchdur = timedif
        matchidxa = 0
        matchidxb = 0

        if self.startIndex >= showindex:
            self.log("Invalid indexes")
            return timedif

        if channeldata.Playlist.size() - (showindex + 1) <= 0:
            self.log("No shows after the show index")
            return timedif

        for curindex in range(self.startIndex, showindex + 1):
            neededtime = channeldata.getItemDuration(curindex) - timedif

            if channelList.threadPause() == False:
                return timedif

            if neededtime > 0:
                for inx in range(showindex + 1, channeldata.Playlist.size()):
                    curtime = channeldata.getItemDuration(inx) - neededtime

                    if abs(curtime) < matchdur:
                        matchdur = abs(curtime)
                        matchidxa = curindex
                        matchidxb = inx

        # swap curindex with inx
        if matchdur < abs(timedif):
            self.log("Found with a new timedif of " + str(matchdur) + "!  Swapping " + str(matchidxa) + " with " + str(matchidxb))
            plitema = channeldata.Playlist.itemlist[matchidxa]
            plitemb = channeldata.Playlist.itemlist[matchidxb]
            channeldata.Playlist.itemlist[matchidxa] = plitemb
            channeldata.Playlist.itemlist[matchidxb] = plitema
            return matchdur

        self.log("No match found")
        return timedif



class OnlyWatchedRule(BaseRule):
    def __init__(self):
        self.name = "Only Played Watched Items"
        self.optionLabels = []
        self.optionValues = []
        self.myId = 4
        self.actions = RULES_ACTION_JSON


    def copy(self):
        return OnlyWatchedRule()


    def runAction(self, actionid, channelList, filedata):
        if actionid == RULES_ACTION_JSON:
            playcount = re.search('"playcount" *: *([0-9]*?),', filedata)
            pc = 0

            try:
                pc = int(playcount.group(1))
            except:
                pc = 0

            if pc == 0:
                return ''

            return filedata



class OnlyUnWatchedRule(BaseRule):
    def __init__(self):
        self.name = "Only Played Unwatched Items"
        self.optionLabels = []
        self.optionValues = []
        self.myId = 11
        self.actions = RULES_ACTION_JSON


    def copy(self):
        return OnlyUnWatchedRule()


    def runAction(self, actionid, channelList, filedata):
        if actionid == RULES_ACTION_JSON:
            playcount = re.search('"playcount" *: *([0-9]*?),', filedata)
            pc = 0

            try:
                pc = int(playcount.group(1))
            except:
                pc = 0

            if pc > 0:
                return ''

            return filedata



class DontAddChannel(BaseRule):
    def __init__(self):
        self.name = "Don't Play This Channel"
        self.optionLabels = []
        self.optionValues = []
        self.myId = 5
        self.actions = RULES_ACTION_FINAL_MADE | RULES_ACTION_FINAL_LOADED


    def copy(self):
        return DontAddChannel()


    def runAction(self, actionid, channelList, channeldata):
        if actionid == RULES_ACTION_FINAL_MADE or actionid == RULES_ACTION_FINAL_LOADED:
            channeldata.isValid = False

        return channeldata



class InterleaveChannel(BaseRule):
    def __init__(self):
        self.name = "Interleave Another Channel"
        self.optionLabels = ['Channel Number', 'Min Interleave Count', 'Max Interleave Count', 'Starting Episode']
        self.optionValues = ['0', '1', '1', '1']
        self.myId = 6
        self.actions = RULES_ACTION_LIST


    def copy(self):
        return InterleaveChannel()


    def onAction(self, act, optionindex):
        self.onActionDigitBox(act, optionindex)
        self.validate()
        return self.optionValues[optionindex]


    def validate(self):
        self.validateDigitBox(0, 1, 1000, 0)
        self.validateDigitBox(1, 1, 100, 1)
        self.validateDigitBox(2, 1, 100, 1)
        self.validateDigitBox(3, 1, 1000, 1)


    def runAction(self, actionid, channelList, filelist):
        if actionid == RULES_ACTION_LIST:
            self.log("runAction")
            chan = 0
            minint = 0
            maxint = 0
            startingep = 0
            curchan = channelList.runningActionChannel
            curruleid = channelList.runningActionId
            self.validate()

            try:
                chan = int(self.optionValues[0])
                minint = int(self.optionValues[1])
                maxint = int(self.optionValues[2])
                startingep = int(self.optionValues[3])
            except:
                self.log("Except when reading params")

            if chan > channelList.maxChannels or chan < 1 or minint < 1 or maxint < 1 or startingep < 1:
                return filelist

            if minint > maxint:
                v = minint
                minint = maxint
                maxint = v

            channelList.setupChannel(chan, True, True, False)

            if channelList.channels[chan - 1].Playlist.size() < 1:
                self.log("The target channel is empty")
                return filelist

            realindex = random.randint(minint, maxint)

            while realindex < len(filelist):
                if channelList.threadPause() == False:
                    return filelist

                newstr = str(channelList.channels[chan - 1].getItemDuration(startingep - 1)) + ',' + channelList.channels[chan - 1].getItemTitle(startingep - 1)
                newstr += "//" + channelList.channels[chan - 1].getItemEpisodeTitle(startingep - 1)
                newstr += "//" + channelList.channels[chan - 1].getItemDescription(startingep - 1) + '\n' + channelList.channels[chan - 1].getItemFilename(startingep - 1)
                filelist.insert(realindex, newstr)
                # Add 1 to account for the thing we just inserted
                realindex += random.randint(minint, maxint) + 1
                startingep += 1

            startingep = channelList.channels[chan - 1].fixPlaylistIndex(startingep) + 1
            # Write starting episode
            self.optionValues[2] = str(startingep)
            ADDON_SETTINGS.setSetting('Channel_' + str(curchan) + '_rule_' + str(curruleid + 1) + '_opt_4', self.optionValues[2])

        return filelist



class ForceRealTime(BaseRule):
    def __init__(self):
        self.name = "Force Real-Time Mode"
        self.optionLabels = []
        self.optionValues = []
        self.myId = 7
        self.actions = RULES_ACTION_BEFORE_TIME


    def copy(self):
        return ForceRealTime()


    def runAction(self, actionid, channelList, channeldata):
        if actionid == RULES_ACTION_BEFORE_TIME:
            channeldata.mode &= ~MODE_STARTMODES
            channeldata.mode |= MODE_REALTIME

        return channeldata



class AlwaysPause(BaseRule):
    def __init__(self):
        self.name = "Pause When Not Watching"
        self.optionLabels = []
        self.optionValues = []
        self.myId = 8
        self.actions = RULES_ACTION_BEFORE_TIME


    def copy(self):
        return AlwaysPause()


    def runAction(self, actionid, channelList, channeldata):
        if actionid == RULES_ACTION_BEFORE_TIME:
            channeldata.mode |= MODE_ALWAYSPAUSE

        return channeldata


class ForceResume(BaseRule):
    def __init__(self):
        self.name = "Force Resume Mode"
        self.optionLabels = []
        self.optionValues = []
        self.myId = 9
        self.actions = RULES_ACTION_BEFORE_TIME


    def copy(self):
        return ForceResume()


    def runAction(self, actionid, channelList, channeldata):
        if actionid == RULES_ACTION_BEFORE_TIME:
            channeldata.mode &= ~MODE_STARTMODES
            channeldata.mode |= MODE_RESUME

        return channeldata



class ForceRandom(BaseRule):
    def __init__(self):
        self.name = "Force Random Mode"
        self.optionLabels = []
        self.optionValues = []
        self.myId = 10
        self.actions = RULES_ACTION_BEFORE_TIME


    def copy(self):
        return ForceRandom()


    def runAction(self, actionid, channelList, channeldata):
        if actionid == RULES_ACTION_BEFORE_TIME:
            channeldata.mode &= ~MODE_STARTMODES
            channeldata.mode |= MODE_RANDOM

        return channeldata

