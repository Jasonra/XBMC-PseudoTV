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
        self.ruleList = [BaseRule(), RenameRule(), NoShowRule(), ScheduleShowRule(), ScheduleMovieRule(), SchedulePlaylistRule(), OnlyWatchedRule(), DontAddChannel(), InterleaveChannel(), ForceRealTime()]


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


    def onActionTimeBox(self, act, optionindex):
        self.log("onActionTimeBox")
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
        self.optionLabels = ['Channel Name']
        self.optionValues = ['']
        self.myId = 1
        self.actions = RULES_ACTION_FINAL


    def copy(self):
        return RenameRule()


    def onAction(self, act, optionindex):
        self.onActionTextBox(act, optionindex)
        self.validate()
        return self.optionValues[optionindex]


    def validate(self):
        self.validateTextBox(0, 18)


    def runAction(self, actionid, channelList, channeldata):
        if actionid == RULES_ACTION_FINAL:
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



class ScheduleShowRule(BaseRule):
    def __init__(self):
        self.name = "Schedule a TV Show"
        self.optionLabels = ['Show Name', 'Days of the Week (UMTWHFS)', 'Time (HH:MM)', 'Episode Count', 'Starting Episode']
        self.optionValues = ['', '', '00:00', '1', '1']
        self.myId = 3
        self.actions = RULES_ACTION_JSON | RULES_ACTION_FINAL


    def copy(self):
        return ScheduleShowRule()


    def onAction(self, act, optionindex):
        if optionindex == 0:
            self.onActionTextBox(act, optionindex)

        if optionindex == 1:
            self.onActionDaysofWeekBox(act, optionindex)

        if optionindex == 2:
            self.onActionTimeBox(act, optionindex)

        if optionindex == 3 or optionindex == 4:
            self.onActionDigitBox(act, optionindex)

        self.validate()
        return self.optionValues[optionindex]


    def validate(self):
        self.validateTextBox(0, 10)
        self.validateDaysofWeekBox(1)
        self.validateDigitBox(3, 1, 1000, 1)
        self.validateDigitBox(4, 1, 1000, 1)



class ScheduleMovieRule(BaseRule):
    def __init__(self):
        self.name = "Schedule a Movie"
        self.optionLabels = ['Movie Name', 'Days of the Week (MTWHFSU)', 'Time (HH:MM)', 'Repeat (Y/N)']
        self.optionValues = ['', '', '00:00', 'N']
        self.myId = 4
        self.actions = RULES_ACTION_JSON | RULES_ACTION_FINAL


    def copy(self):
        return ScheduleMovieRule()


    def onAction(self, act, optionindex):
        if optionindex == 0:
            self.onActionTextBox(act, optionindex)

        self.validate()
        return self.optionValues[optionindex]


    def validate(self):
        self.validateTextBox(0, 10)



class SchedulePlaylistRule(BaseRule):
    def __init__(self):
        self.name = "Schedule a Playlist"
        self.optionLabels = ['Playlist File (with path)', 'Days of the Week (MTWHFSU)', 'Time (HH:MM)', 'Entry Count']
        self.optionValues = ['', '', '00:00', '0']
        self.myId = 5
        self.actions = RULES_ACTION_JSON | RULES_ACTION_FINAL


    def copy(self):
        return SchedulePlaylistRule()



class OnlyWatchedRule(BaseRule):
    def __init__(self):
        self.name = "Only Played Watched Items"
        self.optionLabels = []
        self.optionValues = []
        self.myId = 6
        self.actions = RULES_ACTION_JSON


    def copy(self):
        return OnlyWatchedRule()



class DontAddChannel(BaseRule):
    def __init__(self):
        self.name = "Don't Play This Channel"
        self.optionLabels = []
        self.optionValues = []
        self.myId = 7
        self.actions = RULES_ACTION_FINAL


    def copy(self):
        return DontAddChannel()


    def runAction(self, actionid, channelList, channeldata):
        if actionid == RULES_ACTION_FINAL:
            channeldata.isValid = False

        return channeldata



class InterleaveChannel(BaseRule):
    def __init__(self):
        self.name = "Interleave Another Channel"
        self.optionLabels = ['Other Channel Number', 'Interleave Count']
        self.optionValues = ['0', '1']
        self.myId = 8
        self.actions = RULES_ACTION_FINAL


    def copy(self):
        return InterleaveChannel()


    def onAction(self, act, optionindex):
        self.onActionDigitBox(act, optionindex)
        self.validate()
        return self.optionValues[optionindex]


    def validate(self):
        self.validateDigitBox(0, 1, 999, 0)
        self.validateDigitBox(1, 1, 100, 0)



class ForceRealTime(BaseRule):
    def __init__(self):
        self.name = "Force Real-Time Mode"
        self.optionLabels = []
        self.optionValues = []
        self.myId = 9
        self.actions = RULES_ACTION_BEFORE_TIME


    def copy(self):
        return ForceRealTime()


    def runAction(self, actionid, channelList, channeldata):
        if actionid == RULES_ACTION_BEFORE_TIME:
            channeldata.mode &= ~MODE_STARTMODES
            channeldata.mode |= MODE_RESUME

        return channeldata
