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

import sgtk
from sgtk.util.filesystem import ensure_folder_exists
from sgtk.util.version import is_version_older

__author__ = "Diego Garcia Huerta"
__contact__ = "https://www.linkedin.com/in/diegogh/"


HookBaseClass = sgtk.get_hook_baseclass()


import sd
import sd.api.mdl.sdmdlexporter as sdmdlexporter


class SubstanceDesignerGraphPresetMDLPlugin(HookBaseClass):
    """
    Plugin for publishing Substance Designer Graph as preset.
    Publishes the specified SDMDLGraph as a preset to the specified MDL module file

    This hook relies on functionality found in the base file publisher hook in
    the publish2 app and publish_package_base hook from this hook folder.
    The hook setting for this plugin should look something like this for the
    proper inheritance to work:

        hook: "{self}/publish_file.py:{engine}/tk-multi-publish2/basic/publish_package_base.py:{engine}/tk-multi-publish2/basic/publish_graph_as_preset.py"

    """

    # NOTE: The plugin icon and name are defined by the base file plugin.
    @property
    def type_description(self):
        return "Graph Preset as NVIDIA Material Definition Language .mdl"

    @property
    def short_description(self):
        return "Publishes the Graph as a preset in MDL format"

    @property
    def item_filters(self):
        """
        List of item types that this plugin is interested in.

        Only items matching entries in this list will be presented to the
        accept() method. Strings can contain glob patters such as *, for example
        ["substancedesigner.*", "file.substancedesigner"]
        """
        return ["substancedesigner.graph.preset"]

    def _export(self, settings, item, path):
        graph = item.properties["resource"]
        sdmdlexporter.SDMDLExporter.sExportPreset(graph, path)
