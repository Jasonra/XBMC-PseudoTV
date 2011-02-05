import sys
import os
import xbmc
import xbmcaddon


# Script constants
__scriptname__ = "PseudoTV"
__author__     = "Jason102"
__url__        = "http://github.com/Jasonra/XBMC-PseudoTV"
__version__    = "0.1.5"
__settings__   = xbmcaddon.Addon(id='script.PseudoTV')
__language__   = __settings__.getLocalizedString
__cwd__        = __settings__.getAddonInfo('path')


import resources.lib.Overlay as Overlay


MyOverlayWindow = Overlay.TVOverlay("script.PseudoTV.TVOverlay.xml", __cwd__, "default")
del MyOverlayWindow
