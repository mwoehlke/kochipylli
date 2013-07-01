# Copyright 2013 Matthew Woehlke <mw_triad@users.sourceforge.net>
# Licensed under GPLv3

from PyKDE4.kdecore import *
from PyKDE4.kdeui import *
from PyKDE4.kparts import *

from PyQt4.QtCore import *
from PyQt4.QtGui import *

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
        listview.setIconSize(service.iconSize())
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
        item.setData(Qt.DecorationRole, QIcon(QPixmap.fromImage(image)))
        item.setData(self.NameRole, name)
        item.setData(self.FetchUrlRole, fetch_url)
        self.m_list.addItem(item)

#==============================================================================
# kate: replace-tabs on; replace-tabs-save on; indent-width 4;
