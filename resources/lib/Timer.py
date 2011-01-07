import xbmc
import os, threading


class RealTimer(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.shouldCancel = False
        self.running = False
        self.sleepTime = 0.0


    def run(self):
        self.running = True
        totalSleptTime = 0

        while totalSleptTime < self.sleepTime:
            if self.shouldCancel == False:
                xbmc.sleep(250)
                totalSleptTime += 250
            else:
                totalSleptTime = self.sleepTime

        # Don't run the action if the timer was cancelled
        if self.shouldCancel == False:
            self.action()
            
        self.running = False



class Timer:
    def __init__(self):
        self.MyTimer = RealTimer()


    def stopTimer(self):
        self.MyTimer.shouldCancel = True

        if self.MyTimer.running:
            self.MyTimer.join()

        self.MyTimer.shouldCancel = False


    def startTimer(self, sleepms, action):
        self.stopTimer()
        self.MyTimer.sleepTime = sleepms
        self.MyTimer.action = action
#        self.MyTimer.start()
