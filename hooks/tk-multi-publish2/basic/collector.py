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
from functools import partial

import sgtk
from sgtk import TankError
from sgtk.util.filesystem import create_valid_filename


__author__ = "Diego Garcia Huerta"
__contact__ = "https://www.linkedin.com/in/diegogh/"


HookBaseClass = sgtk.get_hook_baseclass()


import sd


class SubstanceDesignerSessionCollector(HookBaseClass):
    """
    Collector that operates on the substancedesigner session. Should inherit from the basic
    collector hook.
    """

    @property
    def settings(self):
        """
        Dictionary defining the settings that this collector expects to receive
        through the settings parameter in the process_current_session and
        process_file methods.

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

        # grab any base class settings
        collector_settings = (
            super(SubstanceDesignerSessionCollector, self).settings or {}
        )

        # settings specific to this collector
        substancedesigner_session_settings = {
            "Work Template": {
                "type": "template",
                "default": None,
                "description": "Template path for artist work files. Should "
                "correspond to a template defined in "
                "templates.yml. If configured, is made available"
                "to publish plugins via the collected item's "
                "properties. ",
            }
        }

        # update the base settings with these settings
        collector_settings.update(substancedesigner_session_settings)

        return collector_settings

    def process_current_session(self, settings, parent_item):
        """
        Analyzes the current session open in SubstanceDesigner and parents a subtree of
        items under the parent_item passed in.

        :param dict settings: Configured settings for this collector
        :param parent_item: Root item instance

        """
        items = []

        # create an item representing the current substancedesigner session
        session_item = self.collect_current_substancedesigner_session(
            settings, parent_item
        )
        if session_item:
            items.append(session_item)
        return items

    def collect_current_substancedesigner_session(self, settings, parent_item):
        """
        Creates an item that represents the current substancedesigner session.

        :param parent_item: Parent Item instance

        :returns: Item of type substancedesigner.session
        """

        publisher = self.parent

        # if a work template is defined, add it to the item properties so
        # that it can be used by attached publish plugins
        work_template = None
        work_template_setting = settings.get("Work Template")
        if work_template_setting:
            work_template = publisher.engine.get_template_by_name(
                work_template_setting.value
            )

        # we will store the template on the item for use by publish plugins. we
        # can't evaluate the fields here because there's no guarantee the
        # current session path won't change once the item has been created.
        # the attached publish plugins will need to resolve the fields at
        # execution time.

        items = []

        # graph textures
        ctx = sd.getContext()
        app = ctx.getSDApplication()
        uiMgr = app.getQtForPythonUIMgr()
        pck_man = app.getPackageMgr()
        user_pcks = pck_man.getUserPackages()

        for pck in user_pcks:
            pck_filepath = pck.getFilePath()
            pck_file_info = publisher.util.get_file_path_components(pck_filepath)
            pck_id = pck_file_info["filename"]

            pck_item = parent_item.create_item(
                "substancedesigner.package", "Substance Designer Package", pck_id
            )
            icon_path = os.path.join(
                self.disk_location, os.pardir, "icons", "substancedesigner.png"
            )
            pck_item.set_icon_from_path(icon_path)
            pck_item.properties["package"] = pck
            pck_item.properties["work_template"] = work_template
            pck_item.properties["publish_type"] = "Substance Designer File"
            items.append(pck_item)

            has_mdl_graphs = False
            has_comp_graphs = False
            for resource in pck.getChildrenResources(True):
                self.logger.info("Resource <%s> %s" % (type(resource), resource))

                if isinstance(resource, sd.api.sbs.sdsbscompgraph.SDSBSCompGraph):
                    graph_id = resource.getIdentifier()
                    graph_item = pck_item.create_item(
                        "substancedesigner.graph.textures",
                        "Textures",
                        graph_id + " Textures",
                    )
                    icon_path = os.path.join(
                        self.disk_location, os.pardir, "icons", "texture.png"
                    )
                    graph_item.set_icon_from_path(icon_path)
                    graph_item.properties["package"] = pck
                    graph_item.properties["resource"] = resource
                    graph_item.properties["work_template"] = work_template
                    graph_item.properties["publish_type"] = "Texture Folder"
                    graph_item.properties["extra_fields"] = {
                        "substancedesigner.graph.name": graph_id
                    }
                    items.append(graph_item)
                    has_comp_graphs = True

                if isinstance(resource, sd.api.mdl.sdmdlgraph.SDMDLGraph):
                    has_mdl_graphs = True
                    graph_id = resource.getIdentifier()
                    graph_item = pck_item.create_item(
                        "substancedesigner.graph.mdle",
                        "Graph as MDLE",
                        graph_id + " MDLE",
                    )
                    icon_path = os.path.join(
                        self.disk_location,
                        os.pardir,
                        "icons",
                        "substancedesigner_graph_mdle.png",
                    )
                    graph_item.set_icon_from_path(icon_path)
                    graph_item.properties["package"] = pck
                    graph_item.properties["resource"] = resource
                    graph_item.properties["work_template"] = work_template
                    graph_item.properties["publish_type"] = "MDLE File"
                    graph_item.properties["extra_fields"] = {
                        "substancedesigner.graph.name": graph_id
                    }
                    items.append(graph_item)

                    has_mdl_graphs = True
                    graph_id = resource.getIdentifier()
                    graph_item = pck_item.create_item(
                        "substancedesigner.graph.preset",
                        "Graph as preset",
                        graph_id + " Preset(mdl)",
                    )
                    icon_path = os.path.join(
                        self.disk_location,
                        os.pardir,
                        "icons",
                        "substancedesigner_graph_preset.png",
                    )
                    graph_item.set_icon_from_path(icon_path)
                    graph_item.properties["package"] = pck
                    graph_item.properties["resource"] = resource
                    graph_item.properties["work_template"] = work_template
                    graph_item.properties["publish_type"] = "MDL File"
                    graph_item.properties["extra_fields"] = {
                        "substancedesigner.graph.name": graph_id
                    }
                    items.append(graph_item)

            if has_mdl_graphs:
                pck_mdl_item = pck_item.create_item(
                    "substancedesigner.package.mdl",
                    "Package as MDL Module",
                    pck_id + " MDL Module",
                )
                icon_path = os.path.join(
                    self.disk_location,
                    os.pardir,
                    "icons",
                    "substancedesigner_graph_mdl.png",
                )
                pck_mdl_item.set_icon_from_path(icon_path)
                pck_mdl_item.properties["package"] = pck
                pck_mdl_item.properties["work_template"] = work_template
                pck_mdl_item.properties["publish_type"] = "MDL File"
                items.append(pck_mdl_item)

            if has_comp_graphs:
                pck_archive_item = pck_item.create_item(
                    "substancedesigner.package.archive",
                    "Substance Designer Package Archive",
                    pck_id + " Archive",
                )
                icon_path = os.path.join(
                    self.disk_location,
                    os.pardir,
                    "icons",
                    "substancedesignerarchive.png",
                )
                pck_archive_item.set_icon_from_path(icon_path)
                pck_archive_item.properties["package"] = pck
                pck_archive_item.properties["work_template"] = work_template
                pck_archive_item.properties[
                    "publish_type"
                ] = "Substance Designer Archive"
                items.append(pck_archive_item)

        self.logger.info("Collected %s items from the session" % len(items))

        return items


def _session_path():
    """
    Return the path to the current session
    :return:
    """
    ctx = sd.getContext()
    app = ctx.getSDApplication()
    pm = app.getPackageMgr()
    uiMgr = app.getQtForPythonUIMgr()

    path = None
    current_package_filename = ""

    current_graph = uiMgr.getCurrentGraph()
    if current_graph:
        pck = current_graph.getPackage()
        current_package_filename = pck.getFilePath()
        path = current_package_filename

    return path
