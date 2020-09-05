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
import sd.tools.export


class SubstanceDesignerTexturesPublishPlugin(HookBaseClass):
    """
    Plugin for publishing Substance Designer Graphs output textures.

    This hook relies on functionality found in the base file publisher hook in
    the publish2 app and publish_package_base hook from this hook folder.
    The hook setting for this plugin should look something like this for the
    proper inheritance to work:

        hook: "{self}/publish_file.py:{engine}/tk-multi-publish2/basic/publish_package_base.py:{engine}/tk-multi-publish2/basic/publish_graph_textures.py"

    """

    @property
    def type_description(self):
        return "Graph Output Textures"

    @property
    def short_description(self):
        return "Publishes the Graph textures as a folder"

    @property
    def settings(self):
        """
        Dictionary defining the settings that this plugin expects to receive
        through the settings parameter in the accept, validate, publish and
        finalize methods.

        A dictionary on the following form::

            {
                "Settings Name": {
                    "type": "settings_type",
                    "default": "default_value",
                    "description": "One line description of the setting"
            }

        The type string should be one of the data types that toolkit accepts as
        part of its environment configuration.
        """

        # inherit the settings from the base publish plugin
        base_settings = (
            super(SubstanceDesignerTexturesPublishPlugin, self).settings or {}
        )

        # settings specific to this class
        substancedesigner_publish_settings = {
            "Texture Format": {
                "type": "str",
                "default": "png",
                "description": "Texture format to publish." "templates.yml.",
            }
        }

        # update the base settings
        base_settings.update(substancedesigner_publish_settings)

        return base_settings

    def validate(self, settings, item):
        valid = super(SubstanceDesignerTexturesPublishPlugin, self).validate(
            settings, item
        )
        valid = valid and self.validate_graph_output(settings, item)

        return valid

    @property
    def item_filters(self):
        """
        List of item types that this plugin is interested in.

        Only items matching entries in this list will be presented to the
        accept() method. Strings can contain glob patters such as *, for example
        ["substancedesigner.*", "file.substancedesigner"]
        """
        return ["substancedesigner.graph.textures"]

    def _export(self, settings, item, path):
        publish_format_setting = settings.get("Texture Format")
        extension = publish_format_setting.value
        graph = item.properties["resource"]
        sd.tools.export.exportSDGraphOutputs(graph, aOutputDir=path, aFileExt=extension)
