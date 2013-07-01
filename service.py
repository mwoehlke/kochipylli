# Copyright 2013 Matthew Woehlke <mw_triad@users.sourceforge.net>
# Licensed under GPLv3

from PyKDE4.kdecore import *
from PyKDE4.kdeui import *

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtNetwork import *

#==============================================================================
class Service(QObject):
    #--------------------------------------------------------------------------
    def __init__(self, parent = None):
        QObject.__init__(self, parent)
        self.m_window = None
        self.m_net_manager = QNetworkAccessManager(self)

    #--------------------------------------------------------------------------
    def bind(self, window):
        self.m_window = window

    #--------------------------------------------------------------------------
    def requestImageListing(self, url):
        reply = self.m_net_manager.get(QNetworkRequest(QUrl(url)))
        reply.error.connect(reply.deleteLater)
        reply.finished.connect(self.dispatchImageListingRequest)

    #--------------------------------------------------------------------------
    def dispatchImageListingRequest(self):
        reply = self.sender()
        data = reply.readAll()
        self.parseImageListingRequest(reply.url(), data)
        reply.deleteLater()

    #--------------------------------------------------------------------------
    def getThumbnail(self, thumb_url, name, title, fetch_url):
        print "requesting", thumb_url
        reply = self.m_net_manager.get(QNetworkRequest(QUrl(thumb_url)))
        reply.setProperty("name", name)
        reply.setProperty("title", title)
        reply.setProperty("fetch_url", fetch_url)
        reply.error.connect(reply.deleteLater)
        reply.finished.connect(self.addReadyThumbnail)

    #--------------------------------------------------------------------------
    def addReadyThumbnail(self):
        reply = self.sender()
        reply.deleteLater()

        image = QImage()
        if not image.load(reply, None):
            print "Failed to retrieve image from %s" % reply.url()
            return

        name = reply.property("name").toString()
        title = reply.property("title").toString()
        fetch_url = reply.property("fetch_url").toString()

        self.m_window.addThumbnail(name, image, title, fetch_url);

#==============================================================================
# kate: replace-tabs on; replace-tabs-save on; indent-width 4;
