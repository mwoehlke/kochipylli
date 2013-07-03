# Copyright 2013 Matthew Woehlke <mw_triad@users.sourceforge.net>
# Licensed under GPLv3

from PyKDE4.kdecore import *
from PyKDE4.kdeui import *
from PyKDE4.kparts import *

from PyQt4.QtCore import *
from PyQt4.QtGui import *

#==============================================================================
def fitImage(image, size):
    in_size = image.size()
    if in_size == size:
        return QPixmap.fromImage(image)

    if image.width() > size.width() or image.height() > size.height():
        size = QSize(size)
        size.scale(in_size, Qt.KeepAspectRatioByExpanding)

    in_center = QPointF(in_size.width() / 2, in_size.height() / 2)
    out_center = QPointF(size.width() / 2, size.height() / 2)

    result = QImage(size, QImage.Format_ARGB32)
    result.fill(Qt.transparent)
    p = QPainter(result)
    p.drawImage((out_center - in_center).toPoint(), image)
    p.end()

    return QPixmap.fromImage(result)

#==============================================================================
def isRequestEvent(event):
    if event.button() == Qt.MiddleButton:
        return True
    if event.modifiers() & Qt.ControlModifier:
        return True
    return False

#==============================================================================
class ResultList(QListWidget):
    NameRole = Qt.UserRole + 0
    FetchUrlRole = Qt.UserRole + 1

    resultRequested = pyqtSignal(QListWidgetItem)
    resultDiscarded = pyqtSignal(QString)

    #--------------------------------------------------------------------------
    def __init__(self, parent = None):
        QListWidget.__init__(self, parent)
        self.itemDoubleClicked.connect(self.requestItem)

    #--------------------------------------------------------------------------
    def mousePressEvent(self, event):
        if isRequestEvent(event):
            pos = event.pos()
            index = self.indexAt(pos)
            if index.isValid():
                item = self.itemFromIndex(index)
                if item is not None:
                    self.requestItem(item)

        QListWidget.mousePressEvent(self, event)

    #--------------------------------------------------------------------------
    def requestItem(self, item):
        scheme = KColorScheme(QPalette.Active)
        item.setForeground(scheme.foreground(KColorScheme.VisitedText))
        self.resultRequested.emit(item)

    #--------------------------------------------------------------------------
    def deleteSelectedItems(self):
        for item in self.selectedItems():
            name = item.data(self.NameRole).toString()
            self.resultDiscarded.emit(name)

            item = self.takeItem(self.row(item))
            item = None


#==============================================================================
class MainWindow(KMainWindow):
    #--------------------------------------------------------------------------
    def __init__(self, service, archive):
        KMainWindow.__init__(self)
        self.resize(720, 480)

        # Set up status bar
        self.m_progress = QProgressBar()
        self.m_progress.setMaximumWidth(200)
        self.statusBar().addPermanentWidget(self.m_progress)
        self.m_active_jobs = 0

        # Bind service
        self.m_service = service
        service.bind(self)
        self.m_icon_size = service.iconSize()

        # Create Gwenview part
        part_service = KService.serviceByDesktopName("gvpart");
        factory = KPluginLoader(part_service.library()).factory()
        part = factory.create(self)
        part.destroyed.connect(self.deleteLater)

        # Create image list
        listview = ResultList()
        listview.setViewMode(QListView.IconMode)
        listview.setFlow(QListView.TopToBottom)
        listview.setResizeMode(QListView.Adjust)
        listview.setLayoutMode(QListView.Batched)
        listview.setBatchSize(30)
        listview.setIconSize(self.m_icon_size)
        dock = QDockWidget(i18n("Results"))
        dock.setWidget(listview)
        self.addDockWidget(Qt.BottomDockWidgetArea, dock)

        shortcut = QShortcut(QKeySequence(Qt.Key_Delete), listview)
        shortcut.setContext(Qt.WidgetShortcut)
        shortcut.activated.connect(listview.deleteSelectedItems);

        listview.resultDiscarded.connect(service.discardResult)

        # Create navigation bar
        navbar = QToolBar(i18n("Navigation"))
        service.createNav(navbar)
        self.addToolBar(navbar)

        # Create central widget
        splitter = QSplitter()
        splitter.setOrientation(Qt.Horizontal)
        splitter.addWidget(QWidget())
        splitter.addWidget(part.widget())
        splitter.setSizes([144, 560])
        self.setCentralWidget(splitter)

        self.m_viewer = part
        self.m_list = listview

        # Load previous results
        service.loadResults()

    #--------------------------------------------------------------------------
    def setActiveJobs(self, jobs):
        self.m_active_jobs = jobs
        self.updateStatus()

    #--------------------------------------------------------------------------
    def updateStatus(self):
        if self.m_active_jobs:
            msg = i18np("%1 download", "%1 downloads", self.m_active_jobs)
            self.statusBar().showMessage(msg)
            self.m_progress.setRange(0, 0)
        else:
            num_results = self.m_list.count()
            msg = i18np("%1 result", "%1 results", num_results)
            self.statusBar().showMessage(msg)
            self.m_progress.setRange(0, 1)

    #--------------------------------------------------------------------------
    def addThumbnail(self, name, image, title, fetch_url):
        item = QListWidgetItem(title)
        item.setData(Qt.DecorationRole, fitImage(image, self.m_icon_size))
        item.setData(ResultList.NameRole, name)
        item.setData(ResultList.FetchUrlRole, fetch_url)

        scheme = KColorScheme(QPalette.Active)
        item.setForeground(scheme.foreground(KColorScheme.LinkText))

        self.m_list.addItem(item)
        self.updateStatus()

#==============================================================================
# kate: replace-tabs on; replace-tabs-save on; indent-width 4;
