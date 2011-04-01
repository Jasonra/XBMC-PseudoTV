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


ADDON_ID = 'script.pseudotv'
REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)


class Settings:
    def __init__(self):
        self.logfile = xbmc.translatePath('special://profile/addon_data/' + ADDON_ID + '/settings2.xml')


    def log(self, msg, level = xbmc.LOGDEBUG):
        log('Settings: ' + msg, level)


    def getSetting(self, name):
        result = self.getSettingNew(name)

        if result is None:
            return self.realGetSetting(name)

        return result


    def getSettingNew(self, name):
        result = ''
        found = False

        if os.path.exists(self.logfile) == False:
            return None

        try:
            fle = open(self.logfile, "r")
        except:
            self.log("Unable to open the settings file for reading")
            return None

        for line in fle:
            match = re.search('setting id="(.*?)"', line)

            if match:
                if name == match.group(1):
                    match = re.search(' value="(.*?)"', line)

                    if match:
                        result = match.group(1)
                        found = True
                        break

        fle.close()

        if found:
            return result

        return None


    def realGetSetting(self, name):
        try:
            val = REAL_SETTINGS.getSetting(name)
            return val
        except:
            return ''


    def setSetting(self, name, value):
        curdata = []
        matchindex = -1

        if os.path.exists(self.logfile):
            try:
                fle = open(self.logfile, "r")
                curdata = fle.readlines()
                fle.close()
            except:
                pass

        try:
            fle = open(self.logfile, "w")
        except:
            self.log("Unable to open the file for writing")
            return

        index = 0

        for line in curdata:
            match = re.search('setting id="(.*?)"', line)

            if match:
                if name == match.group(1):
                    matchindex = index
                    break

            index += 1

        fle.write("<settings>\n")

        for i in range(len(curdata)):
            if i != matchindex:
                match = re.search('setting id="(.*?)"', curdata[i])

                if match:
                    fle.write(curdata[i])

        fle.write('    <setting id="' + name + '" value="' + value + '" />\n')
        fle.write('</settings>\n')
        fle.close()
