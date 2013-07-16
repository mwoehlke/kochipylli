# Copyright 2013 Matthew Woehlke <mw_triad@users.sourceforge.net>
# Licensed under GPLv3

from PyKDE4.kdecore import *
from PyKDE4.kdeui import *
from PyKDE4.kio import *
from PyKDE4.kparts import *

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from kfiletreeview import KFileTreeView

#------------------------------------------------------------------------------
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

#------------------------------------------------------------------------------
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

    resultRequested = pyqtSignal(QString, QString)
    resultDiscarded = pyqtSignal(QString)

    #--------------------------------------------------------------------------
    def __init__(self, parent = None):
        QListWidget.__init__(self, parent)
        self.itemActivated.connect(self.requestItem)

        self.m_last_scroll_value = 0
        self.m_scroll_bar = self.horizontalScrollBar()
        self.m_scroll_bar.rangeChanged.connect(self.scrollRangeChanged)
        self.m_scroll_bar.valueChanged.connect(self.scrollValueChanged)

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

        name = item.data(ResultList.NameRole).toString()
        fetch_url = item.data(ResultList.FetchUrlRole).toString()
        self.resultRequested.emit(name, fetch_url)

    #--------------------------------------------------------------------------
    def deleteSelectedItems(self):
        for item in self.selectedItems():
            name = item.data(self.NameRole).toString()
            self.resultDiscarded.emit(name)

            item = self.takeItem(self.row(item))
            item = None

    #--------------------------------------------------------------------------
    def scrollRangeChanged(self, minimum, maximum):
        current_value = self.m_scroll_bar.value()
        if self.m_last_scroll_value != current_value:
            self.m_scroll_bar.setValue(self.m_last_scroll_value)

    #--------------------------------------------------------------------------
    def scrollValueChanged(self, new_value):
        maximum = self.m_scroll_bar.maximum()
        if new_value < maximum or new_value > self.m_last_scroll_value:
            self.m_last_scroll_value = new_value

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
        self.m_items = {}

        # Bind service
        self.m_service = service
        service.bind(self)
        self.m_icon_size = service.iconSize()

        # Create Gwenview part
        part_service = KService.serviceByDesktopName("gvpart")
        factory = KPluginLoader(part_service.library()).factory()
        part = factory.create(self)
        self.m_viewer = part

        # Create image list
        listview = ResultList()
        self.m_list = listview

        listview.setViewMode(QListView.IconMode)
        listview.setFlow(QListView.TopToBottom)
        listview.setResizeMode(QListView.Adjust)
        listview.setLayoutMode(QListView.Batched)
        listview.setBatchSize(30)
        listview.setIconSize(self.m_icon_size)
        dock = QDockWidget(i18nc("@title:dock", "Results"))
        dock.setWidget(listview)
        self.addDockWidget(Qt.BottomDockWidgetArea, dock)

        shortcut = QShortcut(QKeySequence(Qt.Key_Delete), listview)
        shortcut.setContext(Qt.WidgetShortcut)
        shortcut.activated.connect(listview.deleteSelectedItems)

        listview.resultRequested.connect(service.requestResult)
        listview.resultDiscarded.connect(service.discardResult)

        listview.resultDiscarded.connect(self.updateStatus)

        listview.currentItemChanged.connect(self.showResult)

        # Create navigation bar
        navbar = QToolBar(i18nc("@title:toolbar", "Navigation"))
        service.setupNavigationBar(navbar)
        self.addToolBar(navbar)

        # Create I/O bar
        iobar = QToolBar(i18nc("@title:toolbar", "File"))

        iobar_tools = QWidget()
        iobar_tools_layout = QHBoxLayout()
        iobar_tools_layout.setContentsMargins(0, 0, 0, 0)
        iobar_tools.setLayout(iobar_tools_layout)

        io_discard = QToolButton()
        io_discard.setText(i18nc("@action:button", "Discard"))
        io_discard.setToolTip(i18nc("@info>tooltip",
                                    "Discard the selected result"))
        io_discard.setIcon(KIcon("user-trash"))
        io_discard.setToolButtonStyle(Qt.ToolButtonFollowStyle)
        io_discard.setEnabled(False)
        io_discard.clicked.connect(listview.deleteSelectedItems)
        self.m_action_discard_result = io_discard

        msg = i18nc("@info>tooltip",
                    "Save result to the currently selected folder")
        io_save = QToolButton()
        io_save.setText(i18nc("@action:button", "Save"))
        io_save.setToolTip(msg)
        io_save.setIcon(KIcon("document-save"))
        io_save.setToolButtonStyle(Qt.ToolButtonFollowStyle)
        io_save.setEnabled(False)
        io_save.clicked.connect(self.saveResult)
        self.m_action_save_result = io_save

        io_save_location = QComboBox()
        dir_view = KFileTreeView()
        dir_view.setDirOnlyMode(True)
        dir_view.setRootUrl(KUrl(archive.canonicalPath()))
        dir_model = dir_view.model()
        io_save_location.setModel(dir_model)
        io_save_location.setView(dir_view)
        for col in range(1, dir_model.columnCount()):
            dir_view.setColumnHidden(col, True)
        io_save_location.setEnabled(False)
        self.m_save_location = io_save_location

        msg = i18nc("@info>tooltip",
                    "Create a new folder in the currently selected folder")
        io_new_folder = QToolButton()
        io_new_folder.setText(i18nc("@action:button", "New Folder"))
        io_new_folder.setToolTip(msg)
        io_new_folder.setIcon(KIcon("folder-new"))
        io_new_folder.setToolButtonStyle(Qt.ToolButtonFollowStyle)
        io_new_folder.setEnabled(False)
        io_new_folder.clicked.connect(self.createFolder)
        self.m_action_create_folder = io_new_folder

        iobar_tools_layout.addWidget(io_discard)
        iobar_tools_layout.addWidget(io_save)
        iobar_tools_layout.addWidget(io_save_location)
        iobar_tools_layout.addWidget(io_new_folder)

        iobar_save_location = QLabel()
        self.m_result_saved_path = iobar_save_location

        iobar_container = QStackedWidget()
        iobar_container.addWidget(iobar_tools)
        iobar_container.addWidget(iobar_save_location)
        self.m_iobar_container = iobar_container
        self.m_iobar_save_location = iobar_save_location

        iobar.addWidget(iobar_container)
        self.addToolBar(iobar)

        # Create result info pane
        info_widget = QWidget()
        service.setupInformationPane(info_widget)

        info_pane = QStackedWidget()
        info_pane.addWidget(QWidget())
        info_pane.addWidget(info_widget)
        self.m_info_pane = info_pane

        # Create central widget
        splitter = QSplitter()
        splitter.setOrientation(Qt.Horizontal)
        splitter.addWidget(info_pane)
        splitter.addWidget(part.widget())
        splitter.setSizes([144, 560])
        self.setCentralWidget(splitter)

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
    def addThumbnail(self, name, image, title, fetch_url, available=False):
        item = QListWidgetItem(title)
        item.setData(Qt.DecorationRole, fitImage(image, self.m_icon_size))
        item.setData(ResultList.NameRole, name)
        item.setData(ResultList.FetchUrlRole, fetch_url)

        scheme = KColorScheme(QPalette.Active)
        color = KColorScheme.LinkText
        if available:
            color = KColorScheme.NormalText
            # TODO PositiveText if already saved
        item.setForeground(scheme.foreground(color))

        self.m_items[name] = item
        self.m_list.addItem(item)
        self.updateStatus()

    #--------------------------------------------------------------------------
    def updateResult(self, name, completed=False, saved=False):
        item = self.m_items[name]
        if item == self.m_list.currentItem():
            self.showResult(item)

        if saved:
            scheme = KColorScheme(QPalette.Active)
            item.setForeground(scheme.foreground(KColorScheme.PositiveText))
        elif completed:
            scheme = KColorScheme(QPalette.Active)
            item.setForeground(scheme.foreground(KColorScheme.NormalText))

    #--------------------------------------------------------------------------
    def showResult(self, item):
        if item is None:
            self.m_info_pane.setCurrentIndex(0)
            self.m_iobar_container.setCurrentIndex(1)
            self.m_result_saved_path.clear()
            self.m_action_discard_result.setEnabled(False)
            self.m_action_save_result.setEnabled(False)
            self.m_save_location.setEnabled(False)
            self.m_action_create_folder.setEnabled(False)
            return

        # Get result information
        name = item.data(ResultList.NameRole).toString()
        image_path = self.m_service.resultImagePath(name)
        status = self.m_service.resultStatus(name)

        # Populate information pane
        if self.m_service.populateResultInfoPane(self.m_info_pane, name):
            self.m_info_pane.setCurrentIndex(1)
        else:
            self.m_info_pane.setCurrentIndex(0)

        # Enable/disable result actions or show saved location
        self.m_action_discard_result.setEnabled(True)
        if type(status) is QString:
            msg = i18nc("@info", "Saved as '%1'", status)
            self.m_result_saved_path.setText(msg)
            self.m_iobar_container.setCurrentIndex(1)
        else:
            self.m_iobar_container.setCurrentIndex(0)
            self.m_action_save_result.setEnabled(status)
            self.m_save_location.setEnabled(status)
            self.m_action_create_folder.setEnabled(status)

        # Show result image
        self.m_viewer.openUrl(KUrl.fromPath(image_path))

    #--------------------------------------------------------------------------
    def createFolder(self):
        dir_view = self.m_save_location.view()
        current_url = dir_view.currentUrl()
        parent_dir = QDir(current_url.toLocalFile())
        parent_path = parent_dir.absolutePath()

        dialog_title = i18nc("@title:dialog", "New Folder")
        dialog_text = i18nc("@info", "Create new folder in:\n%1", parent_path)
        default_name = i18nc("Default name for a new folder", "New Folder")
        result = KInputDialog.getText(dialog_title, dialog_text,
                                      default_name, self)
        if not result[1]:
            return

        new_url = KUrl.fromPath(QString("%1/%2").arg(parent_path, result[0]))
        check_mode = KIO.NetAccess.DestinationSide
        if not KIO.NetAccess.exists(new_url, check_mode, self):
            if not KIO.NetAccess.mkdir(new_url, self):
                error_text = i18nc("@info", "Failed to create directory")
                KMessageBox.sorry(self, error_text)
                return

    #--------------------------------------------------------------------------
    def saveResult(self):
        item = self.m_list.currentItem()
        if item is None:
            return

        dir_view = self.m_save_location.view()
        root_path = dir_view.rootUrl().toLocalFile()
        target_path = dir_view.currentUrl().toLocalFile()
        path = KUrl.relativePath(root_path, target_path)[0]

        name = item.data(ResultList.NameRole).toString()
        self.m_service.saveToDisk(name, path)

#==============================================================================
# kate: replace-tabs on; replace-tabs-save on; indent-width 4;
