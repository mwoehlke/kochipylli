# Copyright 2013 Matthew Woehlke <mw_triad@users.sourceforge.net>
# Licensed under GPLv3
#
# Based on KFileTreeView:
#   Copyright 2007 Tobias Koenig <tokoe@kde.org>

from PyKDE4.kdecore import *
from PyKDE4.kdeui import *
from PyKDE4.kio import *

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from kmetamodel import KMetaModel

#------------------------------------------------------------------------------
def createRootItem(url):
    class FolderItem:
        def __init__(self, url):
            self.name = QFileInfo(url.path()).fileName()
            self.icon = KIcon("folder")
    return FolderItem(url)

#==============================================================================
class KFileTreeView(QTreeView):
    activated = pyqtSignal(KUrl)
    kCurrentChanged = pyqtSignal(KUrl)

    #==========================================================================
    class Private(QObject):
        #----------------------------------------------------------------------
        def __init__(self, q):
            QObject.__init__(self, q)
            self.m_qptr = q

        #----------------------------------------------------------------------
        def urlForProxyIndex(self, index):
            model = self.m_meta_model.subModelForIndex(index)
            if model == self.m_dir_proxy_model:
                index = self.m_meta_model.mapToSubModel(index)
                index = self.m_dir_proxy_model.mapToSource(index)
                item = self.m_dir_model.itemForIndex(index)

                return item.url() if not item.isNull() else KUrl()
            else:
                # The only item that does not belong to the directory model
                # should be the root node
                return self.m_qptr.rootUrl()

        #----------------------------------------------------------------------
        def _k_activated(self, index):
            url = self.urlForProxyIndex(index)
            if url.isValid():
                self.m_qptr.activated.emit(url)

        #----------------------------------------------------------------------
        def _k_currentChanged(self, current_index):
            url = self.urlForProxyIndex(current_index)
            if url.isValid():
                self.m_qptr.kCurrentChanged.emit(url)

        #----------------------------------------------------------------------
        def _k_expanded(self, base_index):
            submodel_index = self.m_dir_proxy_model.mapFromSource(base_index)
            index = self.m_meta_model.mapFromSubModel(submodel_index)
            mode = QItemSelectionModel.SelectCurrent

            self.m_qptr.selectionModel().clearSelection()
            self.m_qptr.selectionModel().setCurrentIndex(index, mode)
            self.m_qptr.scrollTo(index)

    #--------------------------------------------------------------------------
    def __init__(self, parent = None):
        QTreeView.__init__(self, parent)

        d = self.Private(self)
        self.m_dptr = d

        d.m_dir_model = KDirModel(self)
        d.m_meta_model = KMetaModel(self)

        d.m_dir_proxy_model = KDirSortFilterProxyModel(self)
        d.m_dir_proxy_model.setSourceModel(d.m_dir_model)

        self.setModel(d.m_meta_model)
        self.setItemDelegate(KFileItemDelegate(self))

        root_url = KUrl(QDir.root().absolutePath())
        root_item = createRootItem(root_url)
        d.m_dir_model.dirLister().openUrl(root_url, KDirLister.Keep)
        d.m_meta_model.addSubModel(d.m_dir_proxy_model, root_item)

        root_index = d.m_meta_model.indexForSubModel(d.m_dir_proxy_model)
        self.setExpanded(root_index, True)

        self.activated.connect(d._k_activated)
        self.selectionModel().currentChanged.connect(d._k_currentChanged)
        d.m_dir_model.expand.connect(d._k_expanded)

        # TODO: Need to get headers from dir model; let users hide this if they
        #       don't want it
        self.setHeaderHidden(True)

    #--------------------------------------------------------------------------
    def currentUrl(self):
        return self.m_dptr.urlForProxyIndex(self.currentIndex())

    #--------------------------------------------------------------------------
    def selectedUrl(self):
        if not self.selectionModel().hasSelection():
            return KUrl()

        selection = self.selectionModel().selection()
        firstIndex = selection.indexes().first()

        return self.m_dptr.urlForProxyIndex(firstIndex)

    #--------------------------------------------------------------------------
    def selectedUrls(self):
        urls = []

        if not self.selectionModel().hasSelection():
            return urls

        indices = self.selectionModel().selection().indexes()
        for index in indices:
            url = self.m_dptr.urlForProxyIndex(index)
            if url.isValid():
                urls.append(url)

        return urls

    #--------------------------------------------------------------------------
    def rootUrl(self):
        return self.m_dptr.m_dir_model.dirLister().url()

    #--------------------------------------------------------------------------
    def setDirOnlyMode(self, enabled):
        dir_lister = self.m_dptr.m_dir_model.dirLister()
        dir_lister.setDirOnlyMode(enabled)
        dir_lister.openUrl(dir_lister.url())

    #--------------------------------------------------------------------------
    def setCurrentUrl(self, url):
        base_index = self.m_dptr.m_dir_model.indexForUrl(url)

        if not base_index.isValid():
            self.m_dptr.m_dir_model.expandToUrl(url)
            return

        mode = QItemSelectionModel.SelectCurrent
        proxy_index = self.m_dptr.m_dir_proxy_model.mapFromSource(base_index)
        index = self.m_dptr.m_meta_model.mapFromSubModel(proxy_index)
        self.selectionModel().clearSelection()
        self.selectionModel().setCurrentIndex(index, mode)
        self.scrollTo(index)

    #--------------------------------------------------------------------------
    def setRootUrl(self, url):
        d = self.m_dptr

        d.m_meta_model.removeSubModel(d.m_dir_proxy_model)
        d.m_dir_model.dirLister().openUrl(url)
        d.m_meta_model.addSubModel(d.m_dir_proxy_model, createRootItem(url))

        root_index = d.m_meta_model.indexForSubModel(d.m_dir_proxy_model)
        self.setExpanded(root_index, True)

#==============================================================================
# kate: replace-tabs on; replace-tabs-save on; indent-width 4;
