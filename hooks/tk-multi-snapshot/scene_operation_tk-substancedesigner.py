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
from sgtk import Hook
from sgtk import TankError

__author__ = "Diego Garcia Huerta"
__contact__ = "https://www.linkedin.com/in/diegogh/"


HookClass = sgtk.get_hook_baseclass()


import sd


class SceneOperation(HookClass):
    """
    Hook called to perform an operation with the
    current scene
    """

    def execute(self, operation, file_path, **kwargs):
        """
        Main hook entry point

        :operation: String
                    Scene operation to perform

        :file_path: String
                    File path to use if the operation
                    requires it (e.g. open)

        :returns:   Depends on operation:
                    'current_path' - Return the current scene
                                     file path as a String
                    all others     - None
        """
        logger = self.parent.logger

        logger.debug("operation: %s" % operation)
        logger.debug("file_path: %s" % file_path)

        app = self.parent

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
                if pck:
                    # for some reason savePackage did not work
                    # so we use saveas with the same current filename
                    pm.savePackageAs(pck, pck.getFilePath())
