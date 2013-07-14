# Copyright 2013 Matthew Woehlke <mw_triad@users.sourceforge.net>
# Licensed under GPLv3
#
# Based on K3b::MetaItemModel:
#   Copyright 2008 Sebastian Trueg <trueg@k3b.org>
#   Copyright 2009 Gustavo Pichorim Boiko <gustavo.boiko@kdemail.net>
#   Copyright 2009 Michal Malek <michalm@jabster.pl>

from PyKDE4.kdecore import *
from PyKDE4.kio import *

from PyQt4.QtCore import *
from PyQt4.QtGui import *

#==============================================================================
class Node:

    #--------------------------------------------------------------------------
    def __init__(self, parent=None, original_model_index=QModelIndex()):
        self.m_original_model_index = original_model_index
        self.m_parent = parent
        self.m_place = None
        self.m_children = []

    #--------------------------------------------------------------------------
    def isPlace(self):
        return False

    #--------------------------------------------------------------------------
    def place(self):
        return self.m_place

    #--------------------------------------------------------------------------
    def setPlace(self, place):
        self.m_place = place

    #--------------------------------------------------------------------------
    def model(self):
        return self.place().model()

    #--------------------------------------------------------------------------
    def updateChildren(self):
        # Only update children when there are no items in the list
        if not len(self.m_children):
            rows = self.model().rowCount(self.m_original_model_index)
            for i in xrange(rows):
                index = self.model().index(i, 0, self.m_original_model_index)
                node = Node(self, index)
                node.setPlace(self.place())
                children.append(node)

    #--------------------------------------------------------------------------
    def getChildNode(self, original_index):
        self.updateChildren()
        return self.m_children[original_index.row()]

    #--------------------------------------------------------------------------
    def findNodeForOriginalIndex(self, index):
        if self.m_original_model_index == index:
            return self

        for child in self.m_children:
            node = child.findNodeForOriginalIndex(index)
            if node is not None:
                return node

        return None

    #--------------------------------------------------------------------------
    def createNodeForOriginalIndex(self, index):
        if not index.isValid() and self.isPlace():
            return self

        # All the node mapping is done on the first column, so make sure we use
        # an index on the first column
        first_column_index = index.model().index(index.row(), 0, index.parent())
        node = self.findNodeForOriginalIndex(first_column_index)
        if node is None:
            parent = first_column_index.parent()
            parent_node = self.createNodeForOriginalIndex(parent)
            node = parent_node.getChildNode(first_column_index)

        return node

    #--------------------------------------------------------------------------
    def reset(self):
        self.m_children = []

#==============================================================================
class Place(Node):
    #--------------------------------------------------------------------------
    def __init__(self, model):
        Node.__init__(self)
        self.m_model = model
        self.m_name = None
        self.m_icon = None
        self.m_row = None

    #--------------------------------------------------------------------------
    def isPlace(self):
        return True

    #--------------------------------------------------------------------------
    def place(self):
        return self

    #--------------------------------------------------------------------------
    def model(self):
        return self.m_model

#==============================================================================
class KMetaModel(QAbstractItemModel):
    #==========================================================================
    class Private(QObject):
        #----------------------------------------------------------------------
        def __init__(self, q):
            QObject.__init__(self, q)
            self.m_qptr = q
            self.m_places = []

        #----------------------------------------------------------------------
        def placeForModel(self, model):
            for place in self.m_places:
                if place.model() == model:
                    return place

            return None

        #----------------------------------------------------------------------
        def updatePlaceRows(self):
            row = 0
            for place in self.m_places:
                place.m_row = row
                row += 1

        #----------------------------------------------------------------------
        def getRootNode(self, row):
            if row >= 0 and row < len(self.m_places):
                return self.m_places[row]

            return None

        #----------------------------------------------------------------------
        def getRootNodeRow(self, node):
            if not node.isPlace():
                return -1

            row = 0
            node_model = node.model()
            for place in self.m_places:
                if node_model == place.model():
                    return row

                row += 1

            return -1

        #----------------------------------------------------------------------
        def nodeForIndex(self, index):
            # All indices store the node in their internal pointers
            if index.isValid() and index.model() == self.m_qptr:
                return index.internalPointer()

            return None

        #----------------------------------------------------------------------
        def sourceIndex(self, index):
            node = self.nodeForIndex(index)
            if node is None or node.isPlace():
                return QModelIndex()

            omi = node.m_original_model_index
            return node.model().index(omi.row(), index.column(), omi.parent())

        #----------------------------------------------------------------------
        def reset(self):
            # Clean out any cached nodes
            for place in self.m_places:
                place.reset()
            self.updatePlaceRows()
            self.m_qptr.reset()

    #--------------------------------------------------------------------------
    def __init__(self, parent=None):
        QAbstractItemModel.__init__(self, parent)
        self.m_dptr = self.Private(self)

    #--------------------------------------------------------------------------
    def indexForSubModel(self, model):
        if len(self.m_dptr.m_places):
            place = self.m_dptr.placeForModel(model)
            if place is not None:
                return self.createIndex(place.m_row, 0, place)

        return QModelIndex()

    #--------------------------------------------------------------------------
    def subModelForIndex(self, index):
        node = self.m_dptr.nodeForIndex(index)
        return node.model() if node is not None else None

    #--------------------------------------------------------------------------
    def mapToSubModel(self, index):
        if index.isValid():
            return self.m_dptr.sourceIndex(index)
        return QModelIndex()

    #--------------------------------------------------------------------------
    def mapFromSubModel(self, index):
        if index.isValid():
            place = self.m_dptr.placeForModel(index.model())
            node = place.createNodeForOriginalIndex(index)
            return self.createIndex(index.row(), index.column(), node)

        return QModelIndex()


    #--------------------------------------------------------------------------
    def columnCount(self, parent=QModelIndex()):
        model = self.subModelForIndex(parent)
        if model is None:
            return 1

        return model.columnCount(self.mapToSubModel(parent))

    #--------------------------------------------------------------------------
    def data(self, index, role):
        node = self.m_dptr.nodeForIndex(index)
        if node is not None:
            if node.isPlace():
                if role == Qt.DisplayRole:
                    return node.place().m_name
                elif role == Qt.DecorationRole:
                    return QIcon(node.place().m_icon)
                else:
                    return QVariant()
            else:
                return node.model().data(self.mapToSubModel(index), role)

        return QVariant()

    #--------------------------------------------------------------------------
    def index(self, row, column, parent):
        if row < 0 or column < 0:
            return QModelIndex()

        if parent.isValid():
            parent_node = self.m_dptr.nodeForIndex(parent)

            # For places, m_original_model_index is invalid
            omi = parent_node.m_original_model_index
            original_index = parent_node.model().index(row, 0, omi)
            parent_place = parent_node.place()
            node = parent_place.createNodeForOriginalIndex(original_index)
            return self.createIndex(row, column, node)
        else:
            node = self.m_dptr.getRootNode(row)
            if node is not None:
                return self.createIndex(row, column, node)
            else:
                return QModelIndex()

    #--------------------------------------------------------------------------
    def parent(self, index):
        node = self.m_dptr.nodeForIndex(index)

        if not index.isValid() or node is None or node.isPlace():
            return QModelIndex()

        original_index = self.mapToSubModel(index).parent()
        if original_index.isValid():
            return self.mapFromSubModel(original_index)
        else:
            return self.createIndex(node.place().m_row, 0, node.place())

    #--------------------------------------------------------------------------
    def flags(self, index):
        if index.isValid():
            node = self.m_dptr.nodeForIndex(index)
            if node.isPlace:
                # Flags from invalid index can be helpful when model is
                # drop-enabled
                flags = node.model().flags(QModelIndex())
                return flags | Qt.ItemIsSelectable | Qt.ItemIsEnabled
            else:
                return self.mapToSubModel(index).flags()

        return QAbstractItemModel.flags(index)

    #--------------------------------------------------------------------------
    def hasChildren(self, parent):
        if parent.isValid():
            parent_node = self.m_dptr.nodeForIndex(parent)

            # m_original_model_index is invalid for place nodes
            return parent_node.model().hasChildren(self.mapToSubModel(parent))

        return len(self.m_dptr.m_places) > 0

    #--------------------------------------------------------------------------
    def canFetchMore(self, parent):
        if parent.isValid():
            parent_node = self.m_dptr.nodeForIndex(parent)
            return parent_node.model().canFetchMore(self.mapToSubModel(parent))
        else:
            return False

    #--------------------------------------------------------------------------
    def fetchMore(self, parent):
        if parent.isValid():
            parent_node = self.m_dptr.nodeForIndex(parent)
            parent_node.model().fetchMore(self.mapToSubModel(parent))

    #--------------------------------------------------------------------------
    def rowCount(self, parent):
        if parent.column() > 0:
            return 0

        if parent.isValid():
            parent_node = self.m_dptr.nodeForIndex(parent)
            return parent_node.model().rowCount(self.mapToSubModel(parent))
        else:
            return len(self.m_dptr.m_places)

    #--------------------------------------------------------------------------
    def setData(self, index, value, role):
        if index.isValid():
            node = self.m_dptr.nodeForIndex(index)
            if node.isPlace():
                # Places can't be edited
                return False
            else:
                submodel_index = self.mapToSubModel(index)
                return node.model().setData(submodel_index, value, role)

        return False

    #--------------------------------------------------------------------------
    def removeRows(self, row, count, parent):
        if parent.isValid():
            parent_node = self.m_dptr.nodeForIndex(parent)
            submodel_parent = self.mapToSubModel(parent)
            return parent_node.model().removeRows(row, count, submodel_parent)
        elif row >= 0:
            for i in xrange(count):
                self.m_dptr.places.removeAt(row)
            return True

        return False

    #--------------------------------------------------------------------------
    def addSubModel(self, model, item):
        row = len(self.m_dptr.m_places)

        self.beginInsertRows(QModelIndex(), row, row)

        model.setParent(self)

        place = Place(model)

        place.m_name = item.name
        place.m_icon = item.icon

        self.m_dptr.m_places.append(place)

        place.updateChildren()
        self.m_dptr.updatePlaceRows()

        model.modelReset.connect(self.m_dptr.reset)
        model.rowsAboutToBeInserted.connect(self.prepareToInsertRows)
        model.rowsAboutToBeRemoved.connect(self.prepareToRemoveRows)
        model.rowsInserted.connect(self.finishInsertingRows)
        model.rowsRemoved.connect(self.finishRemovingRows)
        model.dataChanged.connect(self.updateModelData)

        self.endInsertRows()

    #--------------------------------------------------------------------------
    def removeSubModel(self, model):
        # Find the place index...
        row = 0
        for place in self.m_dptr.m_places:
            if place.model() == model:
                break
            row += 1

        # ...and simply remove the place from the list
        self.beginRemoveRows(QModelIndex(), row, row)

        del self.m_dptr.m_places[row]
        self.m_dptr.updatePlaceRows()

        self.endRemoveRows()

    #--------------------------------------------------------------------------
    def prepareToInsertRows(self, parent, start, end):
        place = self.m_dptr.placeForModel(self.sender())

        new_parent = None
        target_start = start
        target_end = end

        # Prepare to insert
        if parent.isValid():
            # Search node corresponding to 'index'
            new_parent = self.mapFromSubModel(parent)
        else:
            new_parent = self.createIndex(place.m_row, 0, place)

        self.beginInsertRows(new_parent, target_start, target_end)

        # Do the insertion
        parent_node = None
        if parent.isValid():
            parent_node = place.createNodeForOriginalIndex(parent)
        else:
            parent_node = place

        # If the node doesn't have children yet (maybe not yet accessed), or if
        # it has less items than the start point of this insertion, simply load
        # the child nodes
        if start > len(parent_node.m_children):
            parent_node.updateChildren()
        else:
            # Insert the newly created items in the children list
            for i in xrange(start, end + 1):
                new_child = Node(parent_node)
                new_child.setPlace(parent_node.place())
                parent_node.m_children.insert(i, new_child)

    #--------------------------------------------------------------------------
    def finishInsertingRows(self, parent, start, end):
        place = self.m_dptr.placeForModel(self.sender())

        parent_node = None
        if parent.isValid():
            parent_node = place.createNodeForOriginalIndex(parent)
        else:
            parent_node = place

        # Update original indices in newly created nodes
        for i in xrange(start, end + 1):
            child = parent_node.m_children[i]
            new_index = parent_node.model().index(i, 0, parent)
            child.m_original_model_index = new_index

        self.endInsertRows()

    #--------------------------------------------------------------------------
    def prepareToRemoveRows(self, parent, start, end):
        place = self.m_dptr.placeForModel(self.sender())

        new_parent = None
        target_start = start
        target_end = end

        # Prepare to remove
        if parent.isValid():
            # Search node corresponding to 'index'
            new_parent = self.mapFromSubModel(parent)
        else:
            new_parent = self.createIndex(place.m_row, 0, place)

        # Do the removal
        self.beginRemoveRows(new_parent, target_start, target_end)

        parent_node = None
        if parent.isValid():
            parent_node = place.createNodeForOriginalIndex(parent)
        else:
            parent_node = place

        # Remove the specified children
        del parent_node.m_children[start:end+1]

    #--------------------------------------------------------------------------
    def finishRemovingRows(self, parent, start, end):
        place = self.m_dptr.placeForModel(self.sender())
        self.endRemoveRows()

    #--------------------------------------------------------------------------
    def updateModelData(self, top_left, bottom_right):
        top_left = self.mapFromSubModel(top_left)
        bottom_right = self.mapFromSubModel(bottom_right)
        self.dataChanged.emit(top_left, bottom_right)

#==============================================================================
# kate: replace-tabs on; replace-tabs-save on; indent-width 4;
