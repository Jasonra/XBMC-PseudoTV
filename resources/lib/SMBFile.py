#   Copyright (C) 2012 Jason Anderson
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
import time
from smb.SMBConnection import SMBConnection
from smb.nmb.NetBIOS import NetBIOS
import Globals
import socket



class SMBManager:
	def __init__(self):
		self.hosts = []


	def log(self, msg, level = xbmc.LOGDEBUG):
		Globals.log('SMBManager: ' + msg, level)


	def openFile(self, filename, mode):
		if filename[0:6].lower() == 'smb://':
			filename = filename[6:]

		if filename[0:2] == '\\\\':
			filename = filename[2:]

		self.log("base: " + filename)
		# Now see if there is a username and password
		index = filename.find(':')
		username = 'guest'
		password = ''

		if index > 0:
			username = filename[0:index]
			filename = filename[index + 1:]
			self.log("username: " + username)

		index = filename.find('@')

		if index > 0:
			password = filename[0:index]
			filename = filename[index + 1:]
			self.log("password: " + password)

		# Grab the host or IP
		index = filename.find('/')
		host = ''

		if index > 0:
			host = filename[0:index]
			filename = filename[index:]
		else:
			index = filename.find('\\')

			if index > 0:
				host = filename[0:index]
				filename = filename[index:]
			else:
				self.log("Unable to determine the host")
				return

		self.log("host: " + host)
		# Grab out the file and it's path
		# The first character will always be \ or / so remove it
		filename = filename[1:]
		index = filename[0:].find('/')
		filedir = ''

		if index <= 0:
			index = filename[0:].find('\\')

		if index <= 0:
			filedir = ''
		else:
			filedir = filename[0:index]
			filename = filename[index:]

		filepath = filename
		self.log("File dir: " + filedir)
		self.log("File path: " + filepath)
		serverip = ''
		hostname = ''

		# See if the host is in our list
		for curhost in self.hosts:
			if curhost[0] == host or curhost[1] == host:
				serverip = curhost[0]
				hostname = curhost[1]
				self.log("Got the host info from cache")
				break

		if serverip == '':
			# Now make sure we have the IP and host name
			# See if the host name we have is an IP or not
			try:
				socket.inet_aton(host)
				serverip = host
				conn = NetBIOS(broadcast = False)
				hostname = conn.queryIPForName(host, timeout = 5)[0]
				self.hosts.append([serverip, hostname])
			except:
				hostname = host
				conn = NetBIOS()

				try:
					serverip = conn.queryName(host, timeout = 5)[0]
					self.hosts.append([serverip, hostname])
				except:
					self.log("Unable to get the server and IP")
					serverip = ''
					hostname = ''

		if serverip == '':
			self.log("Unable to get the IP or hostname for " + str(host))
			return

		myfile = SMBFile(serverip, hostname, username, password, filepath, filedir, mode)
		return myfile



class SMBFile:
	def __init__(self, serverip, hostname, username, password, filepath, filedir, mode):
		self.conn = None
		self.lastConnection = 0
		self.isOpen = True
		self.currentOffset = 0
		self.fileDir = filedir
		self.filePath = filepath
		self.mode = mode
		self.username = username
		self.password = password
		self.server = hostname
		self.serverip = serverip
		self.fileSize = -1
		self.cache = ''


	def log(self, msg, level = xbmc.LOGDEBUG):
		Globals.log('SMBFile: ' + msg, level)


	def close(self):
		self.isOpen = False

		if self.conn:
			self.conn.close()
			self.conn = None

		self.currentOffset = 0
		self.fileSize = -1


	def write(self):
		self.log("Write is not implimented")


	def readlines(self):
		if self.checkConn() == False:
			return

		tempfh = SMBReadFile()
		file_attributes, filesize = self.conn.retrieveFile(self.fileDir, self.filePath, tempfh)
		return tempfh.getvalue()


	def read(self, bytes):
		if self.checkConn() == False:
			return

		tempfh = SMBReadFile()
		readamount = 0
		offset = self.currentOffset

		while(len(self.cache) < bytes):
			self.log("Reading")
			file_attributes, readsize = self.conn.readFile(self.fileDir, self.filePath, tempfh, offset + readamount)
			readamount += readsize

			if readsize <= 0:
				break

			self.cache = self.cache + tempfh.getvalue()
			tempfh.clear()

		retdata = ''

		if len(self.cache) >= bytes:
			self.currentOffset += bytes
			retdata = self.cache[:bytes]
			self.cache = self.cache[bytes:]
		else:
			self.currentOffset += readamount
			retdata = self.cache
			self.cache = ''

		return retdata


	def seek(self, offset, direction = 0):
		self.cache = ''

		if direction == 0:
			self.currentOffset = offset
		else:
			if direction == 1:
				self.currentOffset += offset
			else:
				if direction == 2:
					self.currentOffset = self.fileSize + offset


	def tell(self):
		return self.currentOffset


	def checkConn(self):
		if self.conn:
			if time.time() - self.lastConnection < 10:
				self.lastConnection = time.time()
				return True

			self.log("connection stale")
			self.conn.close()

		# Try the most basic connection
		self.conn = SMBConnection(self.username, self.password, 'PseudoTV', self.server, '', use_ntlm_v2=True)

		if self.conn.connect(self.serverip, timeout=5):
			self.log('Connected')
			self.lastConnection = time.time()
			return True

		self.log('Trying again')
		# Try using ntlm v1
		self.conn = SMBConnection(self.username, self.password, 'PseudoTV', self.server, '', use_ntlm_v2=False)

		if self.conn.connect(self.serverip, timeout=5):
			self.log('second')
			self.lastConnection = time.time()
			return True

		self.log('No connection!')
		return False



class SMBReadFile:
	def __init__(self):
		self.data = ''


	def write(self, info):
		self.data = self.data + info


	def getvalue(self):
		return self.data


	def clear(self):
		self.data = ''
