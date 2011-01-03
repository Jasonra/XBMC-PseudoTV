import xbmc
import os, threading


class Timer(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.running = False
        self.shouldCancel = False
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


    def stopTimer(self):
        self.shouldCancel = True

        if self.running:
            self.join()
#         while self.running == 1:
#             xbmc.sleep(50)

        self.shouldCancel = False


    def startTimer(self, sleepms, action):
        self.stopTimer()
        self.sleepTime = sleepms
        self.action = action
        self.start()
