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
        archive_path = self.m_archive.canonicalPath()

        self.m_database_dir = QDir(archive_path + "/.kochipylli/database")
        self.m_results_dir = QDir(archive_path + "/.kochipylli/results")

        results_path = self.m_results_dir.canonicalPath()
        self.m_results_info_path = QDir(results_path + "/info")
        self.m_results_thumbs_path = QDir(results_path + "/thumbnails")

        archive.mkpath(self.m_database_dir.path())
        archive.mkpath(self.m_results_info_path.path())
        archive.mkpath(self.m_results_thumbs_path.path())

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
    # Saved Results Management
    #--------------------------------------------------------------------------
    def saveResult(self, thumb_url, data, result_name, title, fetch_url):
        thumb_ext = QFileInfo(thumb_url.path()).suffix()
        thumb_name = QString("t_%1.%2").arg(result_name, thumb_ext)

        info_path = self.m_results_info_path.path()
        info_path = QString("%1/%2").arg(info_path, result_name)

        info = QSettings(info_path, QSettings.IniFormat)
        if info.status() != QSettings.NoError:
            msg = i18n("Failed to write result info '%1'")
            qDebug(msg.arg(info_path))
            return

        info.beginGroup("thumbnail")
        info.setValue("name", thumb_name)
        info.setValue("url", thumb_url)
        info.endGroup()

        info.beginGroup("result")
        info.setValue("name", result_name)
        info.setValue("title", title)
        info.setValue("fetch_url", fetch_url)
        info.endGroup()

        if info.status() != QSettings.NoError:
            msg = i18n("Failed to write result info '%1'")
            qDebug(msg.arg(info_path))
            return

        thumb_path = self.m_results_thumbs_path.path()
        thumb_path = QString("%1/%2").arg(thumb_path, thumb_name)

        thumb = QFile(thumb_path)
        if not thumb.open(QIODevice.WriteOnly):
            msg = i18n("Failed to write result thumbnail '%1'")
            qDebug(msg.arg(thumb_path))
            return

        thumb.write(data)
        thumb.close()

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

        img_url = reply.url()
        image = QImage()
        data = reply.readAll()
        if not image.loadFromData(data):
            qDebug(i18n("Failed to retrieve image from '%1'").arg(img_url))
            return

        name = reply.property("name").toString()
        title = reply.property("title").toString()
        fetch_url = reply.property("fetch_url").toString()

        self.saveResult(img_url, data, name, title, fetch_url)
        self.m_window.addThumbnail(name, image, title, fetch_url)

#==============================================================================
# kate: replace-tabs on; replace-tabs-save on; indent-width 4;
