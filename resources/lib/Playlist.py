import xbmcgui, xbmc



class PlaylistItem:
    def __init__(self):
        self.duration = 0
        self.filename = ''
        self.description = ''
        self.title = ''
        self.episodetitle = ''



class Playlist:
    def __init__(self):
        self.itemlist = []
        self.totalDuration = 0


    def getduration(self, index):
        if index >= 0 and index < len(self.itemlist):
            return self.itemlist[index].duration

        return 0


    def size(self):
        return len(self.itemlist)


    def getfilename(self, index):
        if index >= 0 and index < len(self.itemlist):
            return self.itemlist[index].filename

        return ''


    def getdescription(self, index):
        if index >= 0 and index < len(self.itemlist):
            return self.itemlist[index].description

        return ''


    def getepisodetitle(self, index):
        if index >= 0 and index < len(self.itemlist):
            return self.itemlist[index].episodetitle

        return ''


    def getTitle(self, index):
        if index >= 0 and index < len(self.itemlist):
            return self.itemlist[index].title

        return ''


    def clear(self):
        del self.itemlist[:]
        self.totalDuration = 0


    def log(self, msg):
        xbmc.log('XBTV - Playlist: ' + msg)


    def load(self, filename):
        self.clear()

        try:
            fle = open(filename, 'r')
        except IOError:
            self.log('Unable to open the file: ' + filename)
            return False

        # find and read the header
        line = fle.readline()

        while len(line) > 0:
            if line == '#EXTM3U\n':
                break

            line = fle.readline()
        else:
            fle.close()
            self.log('Unable to find playlist header for the file: ' + filename)
            return False

        line = fle.readline()

        # past the header, so get the info
        while len(line) > 0:
            if line[:8] == '#EXTINF:':
                tmpitem = PlaylistItem()
                index = line.find(',')

                if index > 0:
                    tmpitem.duration = int(line[8:index])
                    tmpitem.title = line[index + 1:-1]
                    index = tmpitem.title.find('//')

                    if index >= 0:
                        tmpitem.episodetitle = tmpitem.title[index + 2:]
                        tmpitem.title = tmpitem.title[:index]
                        index = tmpitem.episodetitle.find('//')

                        if index >= 0:
                            tmpitem.description = tmpitem.episodetitle[index + 2:]
                            tmpitem.episodetitle = tmpitem.episodetitle[:index]

                line = fle.readline()

                if len(line) == 0:
                    del tmpitem
                    break

                tmpitem.filename = line[:-1]
                self.itemlist.append(tmpitem)
                self.totalDuration += tmpitem.duration

            line = fle.readline()

        fle.close()
        return True
