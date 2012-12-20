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
		self.connections = []


	def log(self, msg, level = xbmc.LOGDEBUG):
		Globals.log('SMBManager: ' + msg, level)


	def openFile(self, filename, mode):
		self.log("openFile " + filename)

		if filename[0:6].lower() == 'smb://':
			filename = filename[6:]

		if filename[0:2] == '\\\\':
			filename = filename[2:]

		self.log("base: " + filename)
		# Now see if there is a username and password
		index = filename.find(':')
		username = ''
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
				return 0

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
		connection = 0
		serverip = ''
		hostname = ''

		# See if the host is in our list
		for curconn in self.connections:
			if curconn.hostname == host or curconn.serverip == host:
				serverip = curconn.serverip
				hostname = curconn.hostname
				connection = curconn
				self.log("Using an existing connection")
				break

		if connection == 0:
			# Now make sure we have the IP and host name
			# See if the host name we have is an IP or not
			try:
				socket.inet_aton(host)
				serverip = host
				conn = NetBIOS(broadcast = False)
				hostname = conn.queryIPForName(host, timeout = 5)[0]
			except:
				hostname = host
				conn = NetBIOS()

				try:
					serverip = conn.queryName(host, timeout = 5)[0]
				except:
					self.log("Unable to get the server and IP")
					serverip = ''
					hostname = ''

		if serverip == '' or hostname == '':
			self.log("Unable to get the IP or hostname for " + str(host), xbmc.LOGERROR)
			return 0

		if connection == 0:
			connection = Connection(serverip, hostname, username, password)
			self.connections.append(connection)

		myfile = SMBFile(connection, filepath, filedir, mode)
		return myfile



class Connection:
	def __init__(self, ip, host, username, password):
		self.serverip = ip
		self.hostname = host
		self.username = username
		self.password = password
		self.lastConnection = 0
		self.conn = 0
		self.alive = False
		self.ntlmv2 = True
		self.dead = False
		self.log("Trying to connect to " + ip + " with the name " + host + ", " + username + " / " + password)
		self.tryConnection()

		if self.dead and self.username == '' and self.password == '':
			self.username = 'guest'
			self.ntlmv2 = True
			self.dead = False
			self.tryConnection()


	def tryConnection(self):
		if self.connect() == False:
			self.ntlmv2 = False

			if self.connect() == False:
				self.dead = True
				self.log("Couldn't connect to " + self.serverip + " with the name " + self.hostname + ", " + self.username + " / " + self.password, xbmc.LOGERROR)


	def connect(self):
		self.log("connect")
		# Try the most basic connection
		self.log('trying: ' + self.username + ' ' + self.password + ' ' + self.hostname)
		self.conn = SMBConnection(self.username, self.password, 'PSEUDOTV', self.hostname, '', use_ntlm_v2=self.ntlmv2)

		try:
			self.log('connecting: ' + self.serverip)
			if self.conn.connect(self.serverip, timeout=10):
				self.log('Connected')
				self.lastConnection = time.time()
				self.alive = True
				return True
		except:
			pass

		self.alive = False
		self.conn = 0
		self.log('No connection!')
		return False


	def log(self, msg, level = xbmc.LOGDEBUG):
		Globals.log('Connection: ' + msg, level)


	def check(self):
		if self.dead:
			return False

		if time.time() - self.lastConnection < 10:
			self.lastConnection = time.time()
			return True

		self.log("connection stale")
		self.conn.close()
		self.alive = False

		if self.connect() == False:
			self.dead = True

		return self.alive


	def reconnect(self):
		if self.dead:
			return False

		self.log("reconnect")

		if self.conn:
			self.conn.close()
			self.conn = 0

		self.alive = False

		if self.connect() == False:
			self.dead = True

		return self.alive


	def retrieveFile(self, fdir, fpath, fhandle):
		if self.dead:
			return (0,0)

		file_attributes = 0
		filesize = 0

		try:
			file_attributes, filesize = self.conn.retrieveFile(fdir, fpath, fhandle)
		except:
			if self.reconnect() == True:
				try:
					file_attributes, filesize = self.conn.retrieveFile(fdir, fpath, fhandle)
				except:
					self.reconnect()
					return (0,0)

		return (file_attributes, filesize)


	def readFile(self, fdir, fpath, fhandle, offset):
		if self.dead:
			return (0,0)

		file_attributes = 0
		readsize = 0

		try:
			file_attributes, readsize = self.conn.retrieveFileFromOffset(fdir, fpath, fhandle, offset, 65535L)
		except:
			if self.reconnect() == True:
				try:
					file_attributes, readsize = self.conn.retrieveFileFromOffset(fdir, fpath, fhandle, offset, 65535L)
				except:
					self.reconnect()
					return (0,0)

		return (file_attributes, readsize)



class SMBFile:
	def __init__(self, connection, filepath, filedir, mode):
		self.connection = connection
		self.isOpen = True
		self.currentOffset = 0
		self.fileDir = filedir
		self.filePath = filepath
		self.mode = mode
		self.fileSize = -1
		self.cache = ''


	def log(self, msg, level = xbmc.LOGDEBUG):
		Globals.log('SMBFile: ' + msg, level)


	def close(self):
		self.isOpen = False
		self.currentOffset = 0
		self.fileSize = -1


	def write(self):
		self.log("Write is not implimented")


	def readlines(self):
		if self.connection.check() == False:
			return ''

		tempfh = SMBReadFile()
		file_attributes, filesize = self.connection.retrieveFile(self.fileDir, self.filePath, tempfh)
		return tempfh.getvalue()


	def read(self, bytes):
		if self.connection.check() == False:
			return ''

		tempfh = SMBReadFile()
		readamount = 0
		offset = self.currentOffset

		while(len(self.cache) < bytes):
			file_attributes, readsize = self.connection.readFile(self.fileDir, self.filePath, tempfh, offset + readamount)
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
					if self.fileSize < 0:
						self.determineFileSize()

					self.currentOffset = self.fileSize + offset


	def tell(self):
		return self.currentOffset


	def determineFileSize(self):
		data = ''
		maxsize = 0
		minsize = 0
		myoffset = self.currentOffset
		self.currentOffset = 100
		self.cache = ''

		# Find the uppper-end of the file size
		data = self.read(1)

		while len(data) > 0:
			minsize = self.currentOffset
			self.currentOffset *= 2
			self.cache = ''
			data = self.read(1)

		maxsize = self.currentOffset

		# Now narrow down the gap to 100 or less bytes
		while(maxsize - minsize > 100):
			self.currentOffset = ((maxsize - minsize) / 2) + minsize
			self.cache = ''
			data = self.read(1)

			if len(data) > 0:
				minsize = self.currentOffset
			else:
				maxsize = self.currentOffset

		# Now read 100 bytes.  Whatever we get + minsize is the total file size
		self.cache = ''
		data = self.read(100)
		self.fileSize = minsize + len(data)
		self.currentOffset = myoffset
		self.cache = ''



class SMBReadFile:
	def __init__(self):
		self.data = ''


	def write(self, info):
		self.data = self.data + info


	def getvalue(self):
		return self.data


	def clear(self):
		self.data = ''
