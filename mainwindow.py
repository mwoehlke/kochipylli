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
class MainWindow(KMainWindow):
    NameRole = Qt.UserRole + 0
    FetchUrlRole = Qt.UserRole + 1

    #--------------------------------------------------------------------------
    def __init__(self, service):
        KMainWindow.__init__(self)
        self.resize(720, 480)

        self.m_service = service
        service.bind(self)
        self.m_icon_size = service.iconSize()

        # Create Gwenview part
        part_service = KService.serviceByDesktopName("gvpart");
        factory = KPluginLoader(part_service.library()).factory()
        part = factory.create(self)
        part.destroyed.connect(self.deleteLater)

        # Create image list
        listview = QListWidget()
        listview.setViewMode(QListView.IconMode)
        listview.setFlow(QListView.TopToBottom)
        listview.setResizeMode(QListView.Adjust)
        listview.setLayoutMode(QListView.Batched)
        listview.setBatchSize(5)
        listview.setIconSize(self.m_icon_size)
        dock = QDockWidget(i18n("Results"))
        dock.setWidget(listview)
        self.addDockWidget(Qt.BottomDockWidgetArea, dock)

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

    #--------------------------------------------------------------------------
    def addThumbnail(self, name, image, title, fetch_url):
        item = QListWidgetItem(title)
        item.setData(Qt.DecorationRole, fitImage(image, self.m_icon_size))
        item.setData(self.NameRole, name)
        item.setData(self.FetchUrlRole, fetch_url)
        self.m_list.addItem(item)

#==============================================================================
# kate: replace-tabs on; replace-tabs-save on; indent-width 4;
