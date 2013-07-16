# Copyright 2013 Matthew Woehlke <mw_triad@users.sourceforge.net>
# Licensed under GPLv3

from PyKDE4.kdecore import *
from PyKDE4.kdeui import *

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtNetwork import *

#------------------------------------------------------------------------------
def listFiles(out, path):
    path_str = path.path()

    # Get files
    for entry in path.entryList(QDir.Files):
        full_path = QDir(path_str + "/" + entry).canonicalPath()
        if entry in out:
            out[entry] += [full_path]
        else:
            out[entry] = [full_path]

    # Recurse through directories
    for entry in path.entryList(QDir.Dirs | QDir.NoDotAndDotDot):
        listFiles(out, QDir(path_str + "/" + entry))

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
        self.m_outstanding_requests = {}
        self.m_outstanding_request_urls = set()

        self.m_info_pane_layout = None
        self.m_info_pane_id = None
        self.m_info_pane_title = None

        self.m_existing_files = {}
        self.m_results = {}
        self.m_database_entries = {}

        self.m_archive = QDir(archive)
        archive_path = self.m_archive.canonicalPath()

        self.m_database_dir = QDir(archive_path + "/.kochipylli/database")
        self.m_results_dir = QDir(archive_path + "/.kochipylli/results")

        results_path = self.m_results_dir.canonicalPath()
        self.m_results_info_dir = QDir(results_path + "/info")
        self.m_results_thumbs_dir = QDir(results_path + "/thumbnails")
        self.m_results_images_dir = QDir(results_path + "/images")

        archive.mkpath(self.m_database_dir.path())
        archive.mkpath(self.m_results_info_dir.path())
        archive.mkpath(self.m_results_thumbs_dir.path())
        archive.mkpath(self.m_results_images_dir.path())

        listFiles(self.m_existing_files, archive)
        self.readDatabase()

    #--------------------------------------------------------------------------
    # UI Interaction
    #--------------------------------------------------------------------------
    def bind(self, window):
        self.m_window = window

    #--------------------------------------------------------------------------
    def setupNavigationBar(self, navbar):
        self.m_navbar = navbar

    #--------------------------------------------------------------------------
    def addInfoLabel(self, caption, widget=KSqueezedTextLabel):
        caption_label = QLabel(caption)

        value_label = widget()
        value_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        self.m_info_pane_layout.addRow(caption_label, value_label)

        return value_label

    #--------------------------------------------------------------------------
    def setupInformationPane(self, pane):
        self.m_info_pane_layout = QFormLayout()
        pane.setLayout(self.m_info_pane_layout)

        self.m_info_pane_id = self.addInfoLabel("ID:")
        self.m_info_pane_title = self.addInfoLabel("Title:")

    #--------------------------------------------------------------------------
    def resultImagePath(self, name):
        if name in self.m_results:
            result = self.m_results[name]
            if "cache_path" in result:
                return result["cache_path"]
            if "thumb_path" in result:
                return result["thumb_path"]

        return None

    #--------------------------------------------------------------------------
    def resultStatus(self, name):
        if name in self.m_results:
            if name in self.m_database_entries:
                return self.m_database_entries[name]
            elif "cache_path" in self.m_results[name]:
                return True

        return False

    #--------------------------------------------------------------------------
    def setInfoText(self, widget, result, key, wrap=False, parser=None):
        if key in result:
            value = result[key]
            widget.setText(value if parser is None else parser(value))
            widget.setEnabled(True)

            if type(widget) is QLabel:
                widget.setWordWrap(wrap)
            if type(widget) is KSqueezedTextLabel:
                widget.setTextElideMode(Qt.ElideNone if wrap else Qt.ElideRight)
        else:
            widget.setText(i18nc("@info", "(unavailable)"))
            widget.setEnabled(False)

            if type(widget) is KSqueezedTextLabel:
                widget.setTextElideMode(Qt.ElideRight)

    #--------------------------------------------------------------------------
    def populateResultInfoPane(self, pane, result_name):
        self.m_info_pane_id.setText(result_name)
        if result_name in self.m_results:
            result = self.m_results[result_name]
            self.setInfoText(self.m_info_pane_title, result, "title")

        return True

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
    def resultInfo(self, result_name, read_only=False):
        info_path = self.m_results_info_dir.path()
        info_path = QString("%1/%2").arg(info_path, result_name)

        info = QSettings(info_path, QSettings.IniFormat)
        if info.status() != QSettings.NoError:
            msg = None
            if read_only:
                qDebug(i18n("Failed to read result info '%1'", info_path))
            else:
                qDebug(i18n("Failed to write result info '%1'", info_path))
            return None

        return info

    #--------------------------------------------------------------------------
    def saveResultInfo(self, info):
        info.sync()
        if info.status() != QSettings.NoError:
            qDebug(i18n("Failed to write result info '%1'", info_path))
            return False
        return True

    #--------------------------------------------------------------------------
    def loadResults(self):
        path_str = self.m_results_info_dir.path()
        for result in self.m_results_info_dir.entryList(QDir.Files):
            self.loadResult(QDir(path_str + "/" + result).canonicalPath())

    #--------------------------------------------------------------------------
    def loadResult(self, path):
        info = QSettings(path, QSettings.IniFormat)
        if info.status() != QSettings.NoError:
            qDebug(i18n("Failed to read result info '%1'", path))
            return

        # Get thumbnail info
        info.beginGroup("thumbnail")
        thumb_name = info.value("name").toString()
        thumb_url = info.value("url").toUrl()
        info.endGroup()

        # Get result info
        info.beginGroup("result")
        result_name = info.value("name").toString()
        title = info.value("title").toString()
        fetch_url = info.value("fetch_url").toString()
        image_name = info.value("image_name").toString()
        cache_name = info.value("cache_name").toString()
        info.endGroup()

        self.m_results[result_name] = { "title": title, "fetch_url": fetch_url }
        self.loadResultInfo(self.m_results[result_name], info)

        # Try to load saved result thumbnail
        thumb_path = self.m_results_thumbs_dir.path()
        thumb_path = QString("%1/%2").arg(thumb_path, thumb_name)
        image = QImage()
        if image.load(thumb_path):
            result = self.m_results[result_name]
            result["title"] = title
            result["thumb_path"] = thumb_path
            available = not image_name.isEmpty() and not cache_name.isEmpty()
            if available:
                result["image_name"] = image_name
                result["cache_name"] = cache_name

                cache_path = self.m_results_images_dir.path()
                cache_path = QString("%1/%2").arg(cache_path, cache_name)
                result["cache_path"] = cache_path

            self.m_window.addThumbnail(result_name, image, title,
                                       fetch_url, available)
            return

        # If loading from disk fails, try to fetch again
        self.requestThumbnail(thumb_url, result_name, title, fetch_url)

    #--------------------------------------------------------------------------
    def loadResultInfo(self, result, info):
        pass

    #--------------------------------------------------------------------------
    def saveResult(self, thumb_url, data, result_name, title, fetch_url):
        thumb_ext = QFileInfo(thumb_url.path()).suffix()
        thumb_name = QString("t_%1.%2").arg(result_name, thumb_ext)

        info = self.resultInfo(result_name)
        if info is None:
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

        if not self.saveResultInfo(info):
            return

        thumb_path = self.m_results_thumbs_dir.path()
        thumb_path = QString("%1/%2").arg(thumb_path, thumb_name)

        thumb = QFile(thumb_path)
        if not thumb.open(QIODevice.WriteOnly):
            qDebug(i18n("Failed to write result thumbnail '%1'", thumb_path))
            return

        thumb.write(data)
        thumb.close()

        result = self.m_results[result_name]
        result["thumb_path"] = thumb_path

    #--------------------------------------------------------------------------
    def saveResultImage(self, result_name, image_url, data):
        image_info = QFileInfo(image_url.path())
        image_name = image_info.fileName()
        image_ext = image_info.suffix()
        cache_name = QString("%1.%2").arg(result_name, image_ext)

        info = self.resultInfo(result_name)
        if info is None:
            return

        info.beginGroup("result")
        info.setValue("image_name", image_name)
        info.setValue("cache_name", cache_name)
        info.endGroup()

        if not self.saveResultInfo(info):
            return

        cache_path = self.m_results_images_dir.path()
        cache_path = QString("%1/%2").arg(cache_path, cache_name)

        image = QFile(cache_path)
        if not image.open(QIODevice.WriteOnly):
            qDebug(i18n("Failed to write result image '%1'", cache_path))
            return

        image.write(data)
        image.close()

        result = self.m_results[result_name]
        result["image_name"] = image_name
        result["cache_path"] = cache_path

    #--------------------------------------------------------------------------
    def deleteResult(self, name):
        info_path = self.m_results_info_dir.path()
        info_path = QString("%1/%2").arg(info_path, name)

        info = QSettings(info_path, QSettings.IniFormat)
        if info.status() != QSettings.NoError:
            qDebug(i18n("Failed to read result info '%1'", path))
            return

        # Get thumbnail info
        info.beginGroup("thumbnail")
        thumb_name = info.value("name").toString()
        info.endGroup()

        info.beginGroup("result")
        cache_name = info.value("cache_name").toString()
        info.endGroup()

        info = None

        # Remove result files
        self.m_results_info_dir.remove(name)
        self.m_results_thumbs_dir.remove(thumb_name)
        if not cache_name.isEmpty():
            self.m_results_images_dir.remove(cache_name)

        # Remove from internal result set
        if name in self.m_results:
            del self.m_results[name]

    #--------------------------------------------------------------------------
    def discardResult(self, name):
        # Delete result files
        self.deleteResult(name)

        # Write result to database so we don't fetch it again
        self.writeDatabaseEntry(name, QString())

    #--------------------------------------------------------------------------
    # Web Interaction
    #--------------------------------------------------------------------------
    def request(self, url):
        # Don't request anything that is already requested; we must use the
        # encoded form as QUrl never matches in a set/dict (likely a bug)
        url = QUrl(url)
        encoded_url = url.toEncoded()
        if encoded_url in self.m_outstanding_request_urls:
            return None

        # Issue the request
        reply = self.m_net_manager.get(QNetworkRequest(url))
        reply.error.connect(self.releaseJob)
        reply.finished.connect(self.releaseJob)

        # Update the outstanding requests information and status
        self.m_outstanding_requests[reply] = encoded_url
        self.m_outstanding_request_urls.add(encoded_url)
        self.updateJobs()

        # Return the response object
        return reply

    #--------------------------------------------------------------------------
    def releaseJob(self):
        reply = self.sender()

        # Delete the reply so it is not leaked
        reply.deleteLater()

        # Remove the request from the outstanding requests information
        request_encoded_url = self.m_outstanding_requests[reply]
        self.m_outstanding_request_urls.discard(request_encoded_url)
        del self.m_outstanding_requests[reply]

        # Update outstanding requests status
        self.updateJobs()

    #--------------------------------------------------------------------------
    def updateJobs(self):
        outstanding_requests_count = len(self.m_outstanding_requests)
        self.m_window.setActiveJobs(outstanding_requests_count)
        self.m_navbar.setEnabled(outstanding_requests_count <= 0)

    #--------------------------------------------------------------------------
    def requestImageListing(self, url):
        reply = self.request(url)
        if reply is None:
            return

        reply.finished.connect(self.dispatchImageListingRequest)

    #--------------------------------------------------------------------------
    def dispatchImageListingRequest(self):
        reply = self.sender()
        data = reply.readAll()
        self.parseImageListingRequest(reply.url(), data)

    #--------------------------------------------------------------------------
    def requestThumbnail(self, thumb_url, name, title, fetch_url):
        # Don't download results we already have in the working set
        if name in self.m_results:
            return

        # Request the result thumbnail
        reply = self.request(thumb_url)
        if reply is None:
            return

        # Store result information on the response object and set up to save
        # the thumbnail when the download finishes
        reply.setProperty("name", name)
        reply.setProperty("title", title)
        reply.setProperty("fetch_url", fetch_url)
        reply.finished.connect(self.addReadyThumbnail)

    #--------------------------------------------------------------------------
    def addReadyThumbnail(self):
        reply = self.sender()

        img_url = reply.url()
        image = QImage()
        data = reply.readAll()
        if not image.loadFromData(data):
            qDebug(i18n("Failed to retrieve image from '%1'", img_url))
            return

        name = reply.property("name").toString()
        title = reply.property("title").toString()
        fetch_url = reply.property("fetch_url").toString()

        self.m_results[name] = { "title": title, "fetch_url": fetch_url }
        self.saveResult(img_url, data, name, title, fetch_url)
        self.m_window.addThumbnail(name, image, title, fetch_url)

    #--------------------------------------------------------------------------
    def requestResult(self, name, url):
        reply = self.request(url)
        if reply is None:
            return

        reply.setProperty("name", name)
        reply.finished.connect(self.dispatchResultRequest)

    #--------------------------------------------------------------------------
    def dispatchResultRequest(self):
        reply = self.sender()
        data = reply.readAll()
        self.parseResultRequest(reply.url(), data)

    #--------------------------------------------------------------------------
    def requestResultImage(self, name, url):
        reply = self.request(url)
        if reply is None:
            return

        reply.setProperty("name", name)
        reply.finished.connect(self.dispatchResultImageRequest)

    #--------------------------------------------------------------------------
    def dispatchResultImageRequest(self):
        reply = self.sender()

        name = reply.property("name").toString()
        self.saveResultImage(name, reply.url(), reply.readAll())
        self.m_window.updateResult(name, completed=True)

#==============================================================================
# kate: replace-tabs on; replace-tabs-save on; indent-width 4;
