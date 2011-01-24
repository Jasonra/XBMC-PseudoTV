from Playlist import Playlist
from Globals import *



class Channel:
    def __init__(self):
        self.Playlist = Playlist()
        self.name = ''
        self.playlistPosition = 0
        self.showTimeOffset = 0
        self.lastAccessTime = 0
        self.totalTimePlayed = 0
        self.isPaused = False


    def log(self, msg):
        log('Channel: ' + msg)


    def setPlaylist(self, filename):
        self.Playlist.load(filename)


    def setPaused(self, paused):
        self.isPaused = paused


    def setShowTime(self, thetime):
        self.showTimeOffset = thetime // 1


    def setShowPosition(self, show):
        show = int(show)
        self.playlistPosition = self.fixPlaylistIndex(show)


    def setAccessTime(self, thetime):
        self.lastAccessTime = thetime // 1


    def getCurrentDuration(self):
        return self.getItemDuration(self.playlistPosition)


    def getItemDuration(self, index):
        return self.Playlist.getduration(self.fixPlaylistIndex(index))


    def getTotalDuration(self):
        return self.Playlist.totalDuration


    def getCurrentDescription(self):
        return self.getItemDescription(self.playlistPosition)


    def getItemDescription(self, index):
        return self.Playlist.getdescription(self.fixPlaylistIndex(index))


    def getCurrentEpisodeTitle(self):
        return self.getItemEpisodeTitle(self.playlistPosition)


    def getItemEpisodeTitle(self, index):
        return self.Playlist.getepisodetitle(self.fixPlaylistIndex(index))


    def getCurrentTitle(self):
        return self.getItemTitle(self.playlistPosition)


    def getItemTitle(self, index):
        return self.Playlist.getTitle(self.fixPlaylistIndex(index))


    def getCurrentFilename(self):
        return self.getItemFilename(self.playlistPosition)


    def getItemFilename(self, index):
        return self.Playlist.getfilename(self.fixPlaylistIndex(index))


    def fixPlaylistIndex(self, index):
        if self.Playlist.size() == 0:
            return index

        while index >= self.Playlist.size():
            index -= self.Playlist.size()

        while index < 0:
            index += self.Playlist.size()

        return index


    def addShowPosition(self, addition):
        self.setShowPosition(self.showTimeOffset + addition)
