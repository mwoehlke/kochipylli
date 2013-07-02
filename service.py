# Copyright 2013 Matthew Woehlke <mw_triad@users.sourceforge.net>
# Licensed under GPLv3

from PyKDE4.kdecore import *
from PyKDE4.kdeui import *

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtNetwork import *

#==============================================================================
def listFiles(out, path):
    # Get files
    for entry in path.entryList(QDir.Files):
        full_path = QDir(path.path() + "/" + entry).canonicalPath()
        if entry in out:
            out[entry] += [full_path]
        else:
            out[entry] = [full_path]

    # Recurse through directories
    for entry in path.entryList(QDir.Dirs | QDir.NoDotAndDotDot):
        listFiles(out, QDir(path.path() + "/" + entry))

#==============================================================================
class Service(QObject):
    #--------------------------------------------------------------------------
    # Initialization
    #--------------------------------------------------------------------------
    def __init__(self, archive, parent = None):
        QObject.__init__(self, parent)
        self.m_window = None
        self.m_navbar = None
        self.m_net_manager = QNetworkAccessManager(self)
        self.m_outstanding_requests = 0

        self.m_existing_files = {}
        self.m_results = {}
        self.m_database_entries = {}

        self.m_archive = QDir(archive)
        self.m_database_dir = QDir(archive.path() + "/.kochipylli/database")
        self.m_results_dir = QDir(archive.path() + "/.kochipylli/results")

        archive.mkpath(self.m_database_dir.path())
        archive.mkpath(self.m_results_dir.path())

        listFiles(self.m_existing_files, archive)
        self.readDatabase()

    #--------------------------------------------------------------------------
    def bind(self, window):
        self.m_window = window

    #--------------------------------------------------------------------------
    def createNav(self, navbar):
        self.m_navbar = navbar

    #--------------------------------------------------------------------------
    # Database Interaction
    #--------------------------------------------------------------------------
    def readDatabase(self):
        self.m_database = QFile(self.m_database_dir.canonicalPath() + "/index")
        if not self.m_database.open(QIODevice.ReadWrite | QIODevice.Append):
            raise IOError(i18n("Unable to open database index"))

        self.m_database.reset()
        while not self.m_database.atEnd():
            entry = self.m_database.readLine()
            if not entry.isEmpty():
                entry = QString.fromUtf8(entry.left(entry.length() - 1))
                self.parseDatabaseEntry(entry)

    #--------------------------------------------------------------------------
    def parseDatabaseEntry(self, entry):
        n = entry.indexOf("=")
        if n >= 0:
            self.m_database_entries[entry.left(n)] = entry.mid(n + 1)

    #--------------------------------------------------------------------------
    def writeDatabaseEntry(self, key, value):
        self.m_database_entries[key] = value
        line = QString("%1=%2\n").arg(key, value)
        r = self.m_database.write(line.toUtf8())
        self.m_database.flush()

    #--------------------------------------------------------------------------
    # Web Interaction
    #--------------------------------------------------------------------------
    def request(self, url):
        self.updateJobs(+1)
        reply = self.m_net_manager.get(QNetworkRequest(QUrl(url)))
        reply.error.connect(reply.deleteLater)
        reply.error.connect(self.releaseJob)
        reply.finished.connect(self.releaseJob)
        return reply

    #--------------------------------------------------------------------------
    def releaseJob(self):
        self.updateJobs(-1)

    #--------------------------------------------------------------------------
    def updateJobs(self, delta):
        self.m_outstanding_requests += delta
        self.m_window.setActiveJobs(self.m_outstanding_requests)
        self.m_navbar.setEnabled(self.m_outstanding_requests <= 0)

    #--------------------------------------------------------------------------
    def requestImageListing(self, url):
        reply = self.request(url)
        reply.finished.connect(self.dispatchImageListingRequest)

    #--------------------------------------------------------------------------
    def dispatchImageListingRequest(self):
        reply = self.sender()
        data = reply.readAll()
        self.parseImageListingRequest(reply.url(), data)
        reply.deleteLater()

    #--------------------------------------------------------------------------
    def getThumbnail(self, thumb_url, name, title, fetch_url):
        reply = self.request(thumb_url)
        reply.setProperty("name", name)
        reply.setProperty("title", title)
        reply.setProperty("fetch_url", fetch_url)
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
