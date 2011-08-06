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

import xbmc
import subprocess, os
import time, threading
import random, os
import Globals

VFS_AVAILABLE = False

try:
    import xbmcvfs
    VFS_AVAILABLE = True
except:
    pass


FILE_LOCK_MAX_FILE_TIMEOUT = 8
FILE_LOCK_NAME = "FileLock.dat"



class FileAccess:
    @staticmethod
    def open(filename, mode):
        fle = 0
        filename = xbmc.makeLegalFilename(filename)

        if os.path.exists(filename) == False:
            if filename[0:6].lower() == 'smb://':
                fle = FileAccess.openSMB(filename, mode)

                if fle != 0:
                    return fle

        # Even if we can't find the file, try to open it anyway
        try:
            fle = open(filename, mode)
        except:
            fle = 0

        if fle == 0:
            raise IOError()

        return fle


    @staticmethod
    def exists(filename):
        if os.path.exists(filename):
            return True

        if filename[0:6].lower() == 'smb://':
            return FileAccess.existsSMB(filename)

        return False


    @staticmethod
    def openSMB(filename, mode):
        fle = 0

        if os.name.lower() == 'nt':
            filename = '\\\\' + filename[6:]

            try:
                fle = open(filename, mode)
            except:
                fle = 0

        return fle


    @staticmethod
    def existsSMB(filename):
        if os.name.lower() == 'nt':
            filename = '\\\\' + filename[6:]

            if os.path.exists(filename):
                return True

        return False


    @staticmethod
    def makedirs(directory):
        try:
            os.makedirs(directory)
        except:
            FileAccess._makedirs(directory)


    @staticmethod
    def _makedirs(path):
        if VFS_AVAILABLE == True:
            if len(path) == 0:
                return False

            if(xbmcvfs.exists(path)):
                return True

            success = xbmcvfs.mkdir(path)

            if success == False:
                if path == os.path.dirname(path):
                    return False

                if FileAccess._makedirs(os.path.dirname(path)):
                    return xbmcvfs.mkdir(path)

            return xbmcvfs.exists(path)

        return False



class FileLock:
    def __init__(self):
        random.seed()
        self.lockName = Globals.CHANNELS_LOC + str(random.randint(1, 60000)) + ".lock"
        self.lockFileName = Globals.CHANNELS_LOC + FILE_LOCK_NAME
        self.lockedList = []
        self.refreshLocksTimer = threading.Timer(3.0, self.refreshLocks)
        self.refreshLocksTimer.start()

        try:
            os.remove(self.lockName)
        except:
            pass


    def close(self):
        self.log("close")

        if self.refreshLocksTimer.isAlive():
            self.refreshLocksTimer.cancel()

        for i in range(len(self.lockedList)):
            self.unlockFile(self.lockedList[0])


    def log(self, msg, level = xbmc.LOGDEBUG):
        Globals.log('FileLock: ' + msg, level)


    def refreshLocks(self):
        for item in self.lockedList:
            self.lockFile(item, True)

        self.refreshLocksTimer = threading.Timer(3.0, self.refreshLocks)
        self.refreshLocksTimer.start()


    def lockFile(self, filename, block = False):
        self.log("lockFile " + filename)
        curval = -1
        attempts = 0
        fle = 0
        filename = filename.lower()
        locked = True

        while(locked == True and attempts < FILE_LOCK_MAX_FILE_TIMEOUT):
            locked = False

            if curval > -1:
                self.releaseLockFile()
                time.sleep(1)

            if self.grabLockFile() == False:
                return False

            try:
                fle = FileAccess.open(self.lockName, "r")
            except:
                self.log("Unable to open the lock file")
                self.releaseLockFile()
                return False

            lines = fle.readlines()
            fle.close()
            val = self.findLockEntry(lines, filename)

            # If the file is locked:
            if val > -1:
                locked = True

                # If we're the ones that have the file locked, allow overriding it
                for item in self.lockedList:
                    if item == filename:
                        locked = False
                        block = False
                        break

                if curval == -1:
                    curval = val
                else:
                    if curval == val:
                        attempts += 1
                    else:
                        if block == True:
                            self.releaseLockFile()
                            self.log("File is locked")
                            return False

                        curval = val
                        attempts = 0

        self.log("File is unlocked")
        self.writeLockEntry(lines, filename)
        self.releaseLockFile()
        existing = False

        for i in range(len(self.lockedList)):
            if self.lockedList[i] == filename:
                existing = True
                break

        if existing == False:
            self.lockedList.append(filename)

        return True


    def grabLockFile(self):
        self.log("grabLockFile")

        # Wait a maximum of 10 seconds to grab file-lock file
        for i in range(20):
            try:
                os.rename(self.lockFileName, self.lockName)
                fle = FileAccess.open(self.lockName, 'r')
                fle.close()
                return True
            except:
                time.sleep(.5)

        # If we couldn't grab it, it is gone.  Create it.
        try:
            fle = FileAccess.open(self.lockName, "w")
            fle.close()
        except:
            self.log("Unable to create the lock file")
            return False

        return True


    def releaseLockFile(self):
        self.log("releaseLockFile")

        # Move the file back to the original lock file name
        try:
            os.rename(self.lockName, self.lockFileName)
        except:
            self.log("Unable to rename the file back to the original name")
            return False

        return True


    def writeLockEntry(self, lines, filename, addentry = True):
        self.log("writeLockEntry")
        # Make sure the entry doesn't exist.  This should only be the case
        # when the attempts count times out
        self.removeLockEntry(lines, filename)

        if addentry:
            lines.append(str(random.randint(1, 60000)) + "," + filename + "\n")

        try:
            fle = FileAccess.open(self.lockName, 'w')
        except:
            self.log("Unable to open the lock file for writing")
            return False

        for line in lines:
            fle.write(line)

        fle.close()


    def findLockEntry(self, lines, filename):
        self.log("findLockEntry")

        # Read the file
        for line in lines:
            # Format is 'random value,filename'
            index = line.find(",")
            flenme = ''
            setval = -1

            # Valid line, get the value and filename
            if index > -1:
                try:
                    setval = int(line[:index])
                    flenme = line[index + 1:].strip()
                except:
                    setval = -1
                    flenme = ''

            # The lock already exists
            if flenme == filename:
                return setval

        return -1


    def removeLockEntry(self, lines, filename):
        self.log("removeLockEntry")
        realindex = 0

        for i in range(len(lines)):
            index = lines[realindex].find(filename)

            if index > -1:
                del lines[realindex]
                realindex -= 1

            realindex += 1


    def unlockFile(self, filename):
        self.log("unlockFile " + filename)
        filename = filename.lower()
        found = False
        realindex = 0

        # First make sure we actually own the lock
        # Remove it from the list if we do
        for i in range(len(self.lockedList)):
            if self.lockedList[realindex] == filename:
                del self.lockedList[realindex]
                found = True
                realindex -= 1

            realindex += 1

        if found == False:
            self.log("Lock not found")
            return False

        if self.grabLockFile() == False:
            return False

        try:
            fle = FileAccess.open(self.lockName, "r")
        except:
            self.log("Unable to open the lock file")
            self.releaseLockFile()
            return False

        lines = fle.readlines()
        fle.close()
        self.writeLockEntry(lines, filename, False)
        self.releaseLockFile()
        return True


    def isFileLocked(self, filename, block = False):
        self.log("isFileLocked " + filename)
        filename = filename.lower()

        if self.grabLockFile() == False:
            return True

        try:
            fle = FileAccess.open(self.lockName, "r")
        except:
            self.log("Unable to open the lock file")
            self.releaseLockFile()
            return True

        lines = fle.readlines()
        fle.close()
        retval = False

        if self.findLockEntry(lines, filename) > -1:
            retval = True

        self.releaseLockFile()
        return retval
