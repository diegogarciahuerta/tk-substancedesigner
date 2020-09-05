# Copyright (c) 2013 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import os

import sgtk
from sgtk.platform.qt import QtGui, QtCore

__author__ = "Diego Garcia Huerta"
__contact__ = "https://www.linkedin.com/in/diegogh/"


HookClass = sgtk.get_hook_baseclass()


import sd


class GraphTypeDialog(QtGui.QDialog):
    def __init__(self, parent=None):
        super(GraphTypeDialog, self).__init__(parent)

        layout = QtGui.QVBoxLayout(self)

        self.graph_lbl = QtGui.QLabel("Graph Type:")
        self.graph_type_cmb = QtGui.QComboBox()
        self.graph_type_cmb.addItems(["Substance", "MDL Material"])
        self.vspc1 = QtGui.QSpacerItem(
            20, 5, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding
        )
        self.graph_name = QtGui.QLabel("Graph Name:")
        self.graph_name_edt = QtGui.QLineEdit("New Graph")
        self.vspc2 = QtGui.QSpacerItem(
            20, 20, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding
        )

        layout.addWidget(self.graph_lbl)
        layout.addWidget(self.graph_type_cmb)
        layout.addItem(self.vspc1)
        layout.addWidget(self.graph_name)
        layout.addWidget(self.graph_name_edt)
        layout.addItem(self.vspc2)

        # OK and Cancel buttons
        buttons = QtGui.QDialogButtonBox(
            QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal,
            self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # static method to create the dialog and return (date, time, accepted)
    @staticmethod
    def createGraphTypeDialog(parent=None):
        dialog = GraphTypeDialog(parent)
        result = dialog.exec_()
        graph_name = dialog.graph_name_edt.text()
        graph_type = dialog.graph_type_cmb.currentText()
        return (graph_type, graph_name, result == QtGui.QDialog.Accepted)


class SceneOperation(HookClass):
    """
    Hook called to perform an operation with the
    current scene
    """

    def execute(
        self,
        operation,
        file_path,
        context,
        parent_action,
        file_version,
        read_only,
        **kwargs
    ):
        """
        Main hook entry point

        :param operation:       String
                                Scene operation to perform

        :param file_path:       String
                                File path to use if the operation
                                requires it (e.g. open)

        :param context:         Context
                                The context the file operation is being
                                performed in.

        :param parent_action:   This is the action that this scene operation is
                                being executed for.  This can be one of:
                                - open_file
                                - new_file
                                - save_file_as
                                - version_up

        :param file_version:    The version/revision of the file to be opened.  If this is 'None'
                                then the latest version should be opened.

        :param read_only:       Specifies if the file should be opened read-only or not

        :returns:               Depends on operation:
                                'current_path' - Return the current scene
                                                 file path as a String
                                'reset'        - True if scene was reset to an empty
                                                 state, otherwise False
                                all others     - None
        """
        logger = self.parent.logger

        logger.debug("operation: %s" % operation)
        logger.debug("file_path: %s" % file_path)
        logger.debug("context: %s" % operation)
        logger.debug("parent_action: %s" % parent_action)
        logger.debug("file_version: %s" % file_version)
        logger.debug("read_only: %s" % read_only)

        ctx = sd.getContext()
        app = ctx.getSDApplication()
        pm = app.getPackageMgr()
        uiMgr = app.getQtForPythonUIMgr()

        if operation == "current_path":
            current_package_filename = ""

            current_graph = uiMgr.getCurrentGraph()
            if current_graph:
                pck = current_graph.getPackage()
                current_package_filename = pck.getFilePath()

            return current_package_filename

        elif operation == "open":
            pm.loadUserPackage(file_path, updatePackages=True)

        elif operation == "save":
            current_graph = uiMgr.getCurrentGraph()
            if current_graph:
                pck = current_graph.getPackage()
                pm.savePackage(pck)

        elif operation == "save_as":
            current_graph = uiMgr.getCurrentGraph()
            if current_graph:
                pck = current_graph.getPackage()
                pm.savePackageAs(pck, file_path)

        elif operation == "reset":
            for p in pm.getPackages():
                pm.unloadUserPackage(p)

            return True

        elif operation == "prepare_new":
            graph_type, graph_name, result = GraphTypeDialog.createGraphTypeDialog()
            if result:
                pck = pm.newUserPackage()

                graph = None
                if graph_type == "Substance":
                    graph = sd.api.sbs.sdsbscompgraph.SDSBSCompGraph.sNew(pck)
                elif graph_type == "MDL Material":
                    graph = sd.api.mdl.sdmdlgraph.SDMDLGraph.sNew(pck)

                if graph:
                    graph.setIdentifier(graph_name)

            return result
