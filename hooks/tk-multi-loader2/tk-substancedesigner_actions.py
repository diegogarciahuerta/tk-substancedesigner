# Copyright (c) 2015 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

"""
Hook that loads defines all the available actions, broken down by publish type.
"""

import os
import sgtk
import bisect

__author__ = "Diego Garcia Huerta"
__contact__ = "https://www.linkedin.com/in/diegogh/"


HookBaseClass = sgtk.get_hook_baseclass()

import sd
from sd.api.sdresourcebitmap import SDResourceBitmap
from sd.api.sdresourcesvg import SDResourceSVG
from sd.api.sdresourcefont import SDResourceFont
from sd.api.sdresourcescene import SDResourceScene
from sd.api.sdresourcelightprofile import SDResourceLightProfile
from sd.api.sdresourcebsdfmeasurement import SDResourceBSDFMeasurement
from sd.api.sdresource import EmbedMethod


# here we map the action to the method that brings the resource into the current
# package
action_to_fn = {
    "bitmap": SDResourceBitmap,
    "svg": SDResourceSVG,
    "font": SDResourceFont,
    "scene": SDResourceScene,
    "light_profile": SDResourceLightProfile,
    "bsdf_measurement": SDResourceBSDFMeasurement,
}


class SubstanceDesignerActions(HookBaseClass):
    # public interface - to be overridden by deriving classes

    def generate_actions(self, sg_publish_data, actions, ui_area):
        """
        Returns a list of action instances for a particular publish.
        This method is called each time a user clicks a publish somewhere in
        the UI.
        The data returned from this hook will be used to populate the actions
        menu for a publish.

        The mapping between Publish types and actions are kept in a different
        place (in the configuration) so at the point when this hook is called,
        the loader app has already established *which* actions are appropriate
        for this object.

        The hook should return at least one action for each item passed in via
        the actions parameter.

        This method needs to return detailed data for those actions, in the
        form of a list of dictionaries, each with name, params, caption and
        description keys.

        Because you are operating on a particular publish, you may tailor the
        output  (caption, tooltip etc) to contain custom information suitable
        for this publish.

        The ui_area parameter is a string and indicates where the publish is to
        be shown.
        - If it will be shown in the main browsing area, "main" is passed.
        - If it will be shown in the details area, "details" is passed.
        - If it will be shown in the history area, "history" is passed.

        Please note that it is perfectly possible to create more than one
        action "instance" for an action! You can for example do scene
        introspection - if the action passed in is "character_attachment"
        you may for example scan the scene, figure out all the nodes
        where this object can be attached and return a list of action
        instances:
        "attach to left hand", "attach to right hand" etc. In this case,
        when more than one object is returned for an action, use the params
        key to pass additional data into the run_action hook.

        :param sg_publish_data: Shotgun data dictionary with all the standard
                                publish fields.
        :param actions: List of action strings which have been defined in the
                        app configuration.
        :param ui_area: String denoting the UI Area (see above).
        :returns List of dictionaries, each with keys name, params, caption and
         description
        """
        app = self.parent
        app.log_debug(
            "Generate actions called for UI element %s. "
            "Actions: %s. Publish Data: %s" % (ui_area, actions, sg_publish_data)
        )

        action_instances = []

        if "bitmap" in actions:
            action_instances.append(
                {
                    "name": "bitmap",
                    "params": None,
                    "caption": "Import as a Bitmap",
                    "description": (
                        "Import as a Bitmap resource in the current Package"
                    ),
                }
            )

        if "font" in actions:
            action_instances.append(
                {
                    "name": "font",
                    "params": None,
                    "caption": "Import as a Font",
                    "description": ("Import as a Font resource in the current Package"),
                }
            )

        if "scene" in actions:
            action_instances.append(
                {
                    "name": "scene",
                    "params": None,
                    "caption": "Import as a Scene",
                    "description": (
                        "Import as a Scene resource in the current Package"
                    ),
                }
            )

        if "light_profile" in actions:
            action_instances.append(
                {
                    "name": "light_profile",
                    "params": None,
                    "caption": "Import as a Light Profile",
                    "description": (
                        "Import as a resource Light Profile in the current Package"
                    ),
                }
            )

        if "bsdf_measurement" in actions:
            action_instances.append(
                {
                    "name": "bsdf_measurement",
                    "params": None,
                    "caption": "Import as a BSDF Measurement",
                    "description": (
                        "Import as a resource BSDF Measurement in the current Package"
                    ),
                }
            )

        if "svg" in actions:
            action_instances.append(
                {
                    "name": "svg",
                    "params": None,
                    "caption": "Import as a SVG",
                    "description": ("Import as a resource SVG in the current Package"),
                }
            )

        return action_instances

    def execute_multiple_actions(self, actions):
        """
        Executes the specified action on a list of items.

        The default implementation dispatches each item from ``actions`` to
        the ``execute_action`` method.

        The ``actions`` is a list of dictionaries holding all the actions to
        execute.
        Each entry will have the following values:

            name: Name of the action to execute
            sg_publish_data: Publish information coming from Shotgun
            params: Parameters passed down from the generate_actions hook.

        .. note::
            This is the default entry point for the hook. It reuses the
            ``execute_action`` method for backward compatibility with hooks
            written for the previous version of the loader.

        .. note::
            The hook will stop applying the actions on the selection if an
            error is raised midway through.

        :param list actions: Action dictionaries.
        """
        app = self.parent
        for single_action in actions:
            app.log_debug("Single Action: %s" % single_action)
            name = single_action["name"]
            sg_publish_data = single_action["sg_publish_data"]
            params = single_action["params"]

            self.execute_action(name, params, sg_publish_data)

    def execute_action(self, name, params, sg_publish_data):
        """
        Execute a given action. The data sent to this be method will
        represent one of the actions enumerated by the generate_actions method.

        :param name: Action name string representing one of the items returned
                     by generate_actions.
        :param params: Params data, as specified by generate_actions.
        :param sg_publish_data: Shotgun data dictionary with all the standard
                                publish fields.
        :returns: No return value expected.
        """
        app = self.parent
        app.log_debug(
            "Execute action called for action %s. "
            "Parameters: %s. Publish Data: %s" % (name, params, sg_publish_data)
        )

        # resolve path
        # toolkit uses utf-8 encoded strings internally and SubstanceDesigner API expects
        # unicode so convert the path to ensure filenames containing complex
        # characters are supported
        path = self.get_publish_path(sg_publish_data).replace(os.path.sep, "/")

        if name in action_to_fn:
            ctx = sd.getContext()
            app = ctx.getSDApplication()
            pm = app.getPackageMgr()
            uiMgr = app.getQtForPythonUIMgr()

            current_graph = uiMgr.getCurrentGraph()
            if current_graph:
                pck = current_graph.getPackage()
                fn = action_to_fn[name]
                fn.sNewFromFile(pck, path, EmbedMethod.Linked)
