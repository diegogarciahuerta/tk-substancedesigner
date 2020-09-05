# Copyright (c) 2017 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import os
import tempfile
import contextlib
from functools import partial

import sgtk
from sgtk.util.filesystem import ensure_folder_exists
from sgtk.util.version import is_version_older

__author__ = "Diego Garcia Huerta"
__contact__ = "https://www.linkedin.com/in/diegogh/"


HookBaseClass = sgtk.get_hook_baseclass()


import sd


class SubstanceDesignerPackagePublishPlugin(HookBaseClass):
    """
    Plugin for publishing the current Package as Substance Designer Package
    (.sbs format).

    This hook relies on functionality found in the base file publisher hook in
    the publish2 app and publish_package_base hook from this hook folder.
    The hook setting for this plugin should look something like this for the
    proper inheritance to work:

        hook: "{self}/publish_file.py:{engine}/tk-multi-publish2/basic/publish_package_base.py:{engine}/tk-multi-publish2/basic/publish_package.py"
    """

    @property
    def type_description(self):
        return "Package"

    @property
    def short_description(self):
        return "Publishes the current selected Package from the Explorer"

    @property
    def item_filters(self):
        """
        List of item types that this plugin is interested in.

        Only items matching entries in this list will be presented to the
        accept() method. Strings can contain glob patters such as *, for example
        ["substancedesigner.*", "file.substancedesigner"]
        """
        return ["substancedesigner.package"]

    def _export(self, settings, item, path):
        pck = item.properties["package"]
        _save_package(pck, str(path))

    def finalize(self, settings, item):
        """
        Execute the finalization pass. This pass executes once all the publish
        tasks have completed, and can for example be used to version up files.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """

        # do the base class finalization
        super(SubstanceDesignerPackagePublishPlugin, self).finalize(settings, item)

        # bump the package file to the next version
        pck = item.properties["package"]
        self._save_to_next_version(
            item.properties["path"], item, partial(_save_package, pck)
        )


def _save_package(pck, path):
    """
    Save the  package to the supplied path.
    """
    ctx = sd.getContext()
    app = ctx.getSDApplication()
    pm = app.getPackageMgr()
    pm.savePackageAs(pck, path)


def _get_save_as_action():
    """
    Simple helper for returning a log action dict for saving the session
    """

    engine = sgtk.platform.current_engine()

    callback = _save_as

    # if workfiles2 is configured, use that for file save
    if "tk-multi-workfiles2" in engine.apps:
        app = engine.apps["tk-multi-workfiles2"]
        if hasattr(app, "show_file_save_dlg"):
            callback = app.show_file_save_dlg

    return {
        "action_button": {
            "label": "Save As...",
            "tooltip": "Save the current session",
            "callback": callback,
        }
    }


def _save_as():
    """
    Emulates the save as functionality from the package tool-bar
    """

    ctx = sd.getContext()
    app = ctx.getSDApplication()
    pm = app.getPackageMgr()
    uiMgr = app.getQtForPythonUIMgr()
    main_window = uiMgr.getMainWindow()

    # find the Save as action under one of the explorers
    explorer = None
    explorers = main_window.findChildren(PySide2.QtWidgets.QDockWidget)
    for w in explorers:
        if "Explorer" in w.windowTitle():
            explorer = w
            break

    if explorer:
        actions = explorer.widget().findChildren(PySide2.QtWidgets.QAction)

        for a in actions:
            if a.text() == "Save As...":
                a.trigger()
                break
