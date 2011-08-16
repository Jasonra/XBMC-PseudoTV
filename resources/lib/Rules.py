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



class RulesList:
    def __init__(self):
        self.ruleList = [BaseRule(), RenameRule(), NoShowRule(), ScheduleChannelRule(), OnlyWatchedRule(), DontAddChannel(), InterleaveChannel(), ForceRealTime()]


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


    def getId(self):
        return self.myId


    def runAction(self, actionid, channelList, param):
        pass


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
                self.optionValues[optionindex] = keyb.getText().toUpper()

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
        self.name = "Schedule a Show"
        self.optionLabels = ['Channel Number', 'Days of the Week (UMTWHFS)', 'Time (HH:MM)', 'Episode Count', 'Starting Episode', 'Starting Date']
        self.optionValues = ['0', '', '00:00', '1', '1', '']
        self.myId = 3
        self.actions = RULES_ACTION_START | RULES_ACTION_BEFORE_CLEAR | RULES_ACTION_FINAL_MADE
        self.addedduration = 0
        self.appended = False


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

        self.validate()
        return self.optionValues[optionindex]


    def validate(self):
        self.validateDigitBox(0, 1, 1000, '')
        self.validateDaysofWeekBox(1)
        self.validateTimeBox(2)
        self.validateDigitBox(3, 1, 1000, 1)
        self.validateDigitBox(4, 1, 1000, 1)


    def runAction(self, actionid, channelList, channeldata):
        self.log("runAction")

        if action == RULES_ACTION_START:
            self.addedduration = channeldata.getTotalDuration()

        if action == RULES_ACTION_BEFORE:
            self.addedduration = self.channeldata.getTotalDuration() - self.addedduration

            if channeldata.totalTimePlayed > 0:
                self.appended = True
            else:
                self.appended = False

        if actionid == RULES_ACTION_FINAL_MADE:
            chan = 0
            epcount = 0
            startingep = 0
            curchan = channelList.runningActionChannel
            curruleid = channelList.runningActionId
            startindex = 0

            try:
                chan = int(self.optionValues[0])
                epcount = int(self.optionValues[3])
                startingep = int(self.optionValues[4])
            except:
                pass

            if chan > channelList.maxChannels or chan < 1 or epcount < 1 or startingep < 1:
                return filelist

            channelList.setupChannel(chan, True, True)

            if channelList.channels[chan - 1].Playlist.size() < 1:
                return filelist

            if self.appended == True:
                totdur = 0

                for item in channeldata.Playlist.itemlist:
                    totdur += item.duration
                    startindex += 1

                    if self.channeldata.getTotalDuration() - totdur >= self.addedduration:
                        break

            if startindex < channeldata.playlistPosition:
                startindex = channeldata.playlistPosition + 1

            # add a show at the proper position
            # first, determine the next show time and date

            # rearrange episodes to get an optimal time
            if channeldata.isRandom:
                pass



class OnlyWatchedRule(BaseRule):
    def __init__(self):
        self.name = "Only Played Watched Items"
        self.optionLabels = []
        self.optionValues = []
        self.myId = 4
        self.actions = RULES_ACTION_JSON


    def copy(self):
        return OnlyWatchedRule()



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
        self.optionLabels = ['Channel Number', 'Interleave Count', 'Starting Episode']
        self.optionValues = ['0', '1', '1']
        self.myId = 6
        self.actions = RULES_ACTION_FINAL_MADE


    def copy(self):
        return InterleaveChannel()


    def onAction(self, act, optionindex):
        self.onActionDigitBox(act, optionindex)
        self.validate()
        return self.optionValues[optionindex]


    def validate(self):
        self.validateDigitBox(0, 1, 1000, 0)
        self.validateDigitBox(1, 1, 100, 1)
        self.validateDigitBox(2, 1, 1000, 1)


    def runAction(self, actionid, channelList, filelist):
        self.log("runAction")

        if actionid == RULES_ACTION_FINAL_MADE:
            chan = 0
            interleave = 0
            startingep = 0
            curchan = channelList.runningActionChannel
            curruleid = channelList.runningActionId

            try:
                chan = int(self.optionValues[0])
                interleave = int(self.optionValues[1])
                startingep = int(self.optionValues[2])
            except:
                pass

            if chan > channelList.maxChannels or chan < 1 or interleave < 1 or startingep < 1:
                return filelist

            channelList.setupChannel(chan, True, True)

            if channelList.channels[chan - 1].Playlist.size() < 1:
                return filelist

            realindex = 0

            while realindex < len(filelist):
                newstr = str(channelList.channels[chan - 1].getItemDuration(startingep - 1)) + ',' + channelList.channels[chan - 1].getItemTitle(startingep - 1)
                newstr += "//" + channelList.channels[chan - 1].getItemEpisodeTitle(startingep - 1)
                newstr += "//" + channelList.channels[chan - 1].getItemDescription(startingep - 1) + '\n' + channelList.channels[chan - 1].getItemFilename(startingep - 1)
                filelist.insert(realindex, newstr)
                realindex += interleave + 1
                startingep += 1

            startingep = channelList.channels[chan - 1].fixPlaylistIndex(startingep)
            # Write starting episode
            self.optionValues[2] = str(startingep)
            ADDON_SETTINGS.setSetting('Channel_' + str(curchan) + '_rule_' + str(curruleid) + '_opt_' + str(3), self.optionValues[2])

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
            channeldata.mode |= MODE_RESUME

        return channeldata
