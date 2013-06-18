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

import xbmc, xbmcaddon
import sys, re, os
import time, traceback
import Globals

from FileAccess import FileLock, FileAccess



class Settings:
    def __init__(self):
        self.logfile = xbmc.translatePath(os.path.join(Globals.SETTINGS_LOC, 'settings2.xml'))
        self.currentSettings = []
        self.alwaysWrite = 1


    def loadSettings(self):
        self.log("Loading settings from " + self.logfile);
        del self.currentSettings[:]

        if FileAccess.exists(self.logfile):
            try:
                fle = FileAccess.open(self.logfile, "r")
                curset = fle.readlines()
                fle.close()
            except:
                self.log("Exception when reading settings: ")
                self.log(traceback.format_exc(), xbmc.LOGERROR)

            for line in curset:
                name = re.search('setting id="(.*?)"', line)

                if name:
                    val = re.search(' value="(.*?)"', line)

                    if val:
                        self.currentSettings.append([name.group(1), val.group(1)])


    def disableWriteOnSave(self):
        self.alwaysWrite = 0


    def log(self, msg, level = xbmc.LOGDEBUG):
        Globals.log('Settings: ' + msg, level)


    def getSetting(self, name, force = False):
        if force:
            self.loadSettings()

        result = self.getSettingNew(name)

        if result is None:
            return self.realGetSetting(name)

        return result


    def getSettingNew(self, name):
        for i in range(len(self.currentSettings)):
            if self.currentSettings[i][0] == name:
                return self.currentSettings[i][1]

        return None


    def realGetSetting(self, name):
        try:
            val = Globals.REAL_SETTINGS.getSetting(name)
            return val
        except:
            return ''


    def setSetting(self, name, value):
        found = False

        for i in range(len(self.currentSettings)):
            if self.currentSettings[i][0] == name:
                self.currentSettings[i][1] = value
                found = True
                break

        if found == False:
            self.currentSettings.append([name, value])

        if self.alwaysWrite == 1:
            self.writeSettings()


    def writeSettings(self):
        try:
            fle = FileAccess.open(self.logfile, "w")
        except:
            self.log("Unable to open the file for writing")
            return

        flewrite = Globals.uni("<settings>\n")

        for i in range(len(self.currentSettings)):
            flewrite += Globals.uni('    <setting id="') + Globals.uni(self.currentSettings[i][0]) + Globals.uni('" value="') + Globals.uni(self.currentSettings[i][1]) + Globals.uni('" />\n')

        flewrite += Globals.uni('</settings>\n')
        fle.write(flewrite)
        fle.close()
