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
import traceback

import sgtk
from sgtk.util.filesystem import ensure_folder_exists
from sgtk.util.version import is_version_older

__author__ = "Diego Garcia Huerta"
__contact__ = "https://www.linkedin.com/in/diegogh/"


HookBaseClass = sgtk.get_hook_baseclass()


import sd


class SubstanceDesignerPackageBasePublishPlugin(HookBaseClass):
    """
    Base plugin got publishing hooks for this engine.

    This hook relies on functionality found in the base file publisher hook in
    the publish2 app and should inherit from it in the configuration. The hook
    setting for this plugin should look something like this:

        hook: "{self}/publish_file.py:{engine}/tk-multi-publish2/basic/publish_package_base.py"

    """

    # NOTE: The plugin icon and name are defined by the base file plugin.
    @property
    def type_description(self):
        return ""

    @property
    def short_description(self):
        return "Publishes the file to Shotgun"

    @property
    def description(self):
        """
        Verbose, multi-line description of what the plugin does. This can
        contain simple html for formatting.
        """

        loader_url = "https://support.shotgunsoftware.com/hc/en-us/articles/219033078"

        return """
        %s. A <b>Publish</b> entry will be
        created in Shotgun which will include a reference to the file's current
        path on disk. If a publish template is configured, a copy of the
        current session will be copied to the publish template path which
        will be the file that is published. Other users will be able to access
        the published file via the <b><a href='%s'>Loader</a></b> so long as
        they have access to the file's location on disk.

        If the session has not been saved, validation will fail and a button
        will be provided in the logging output to save the file.

        <h3>File versioning</h3>
        If the filename contains a version number, the process will bump the
        file to the next version after publishing.

        The <code>version</code> field of the resulting <b>Publish</b> in
        Shotgun will also reflect the version number identified in the filename.
        The basic worklfow recognizes the following version formats by default:

        <ul>
        <li><code>filename.v###.ext</code></li>
        <li><code>filename_v###.ext</code></li>
        <li><code>filename-v###.ext</code></li>
        </ul>

        After publishing, if a version number is detected in the work file, the
        work file will automatically be saved to the next incremental version
        number. For example, <code>filename.v001.ext</code> will be published
        and copied to <code>filename.v002.ext</code>

        If the next incremental version of the file already exists on disk, the
        validation step will produce a warning, and a button will be provided in
        the logging output which will allow saving the session to the next
        available version number prior to publishing.

        <br><br><i>NOTE: any amount of version number padding is supported. for
        non-template based workflows.</i>

        <h3>Overwriting an existing publish</h3>
        In non-template workflows, a file can be published multiple times,
        however only the most recent publish will be available to other users.
        Warnings will be provided during validation if there are previous
        publishes.
        """ % (
            self.short_description,
            loader_url,
        )

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
            super(SubstanceDesignerPackageBasePublishPlugin, self).settings or {}
        )

        # settings specific to this class
        substancedesigner_publish_settings = {
            "Publish Template": {
                "type": "template",
                "default": None,
                "description": "Template path for published %s files. Should"
                "correspond to a template defined in "
                "templates.yml." % self.type_description,
            }
        }

        # update the base settings
        base_settings.update(substancedesigner_publish_settings)

        return base_settings

    @property
    def item_filters(self):
        """
        List of item types that this plugin is interested in.

        Only items matching entries in this list will be presented to the
        accept() method. Strings can contain glob patters such as *, for example
        ["substancedesigner.*", "file.substancedesigner"]
        """
        return []

    def accept(self, settings, item):
        """
        Method called by the publisher to determine if an item is of any
        interest to this plugin. Only items matching the filters defined via the
        item_filters property will be presented to this method.

        A publish task will be generated for each item accepted here. Returns a
        dictionary with the following booleans:

            - accepted: Indicates if the plugin is interested in this value at
                all. Required.
            - enabled: If True, the plugin will be enabled in the UI, otherwise
                it will be disabled. Optional, True by default.
            - visible: If True, the plugin will be visible in the UI, otherwise
                it will be hidden. Optional, True by default.
            - checked: If True, the plugin will be checked in the UI, otherwise
                it will be unchecked. Optional, True by default.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process

        :returns: dictionary with boolean keys accepted, required and enabled
        """

        # if a publish template is configured, disable context change. This
        # is a temporary measure until the publisher handles context switching
        # natively.
        publish_template = self.get_publish_template(settings, item)
        if publish_template:
            item.context_change_allowed = False

        # if we validate the session , we can accept it in principle
        self.session_validate(settings, item)

        self.logger.info(
            "SubstanceDesigner '%s' plugin accepted to publish a %s"
            % (self.name, self.type_description)
        )
        return {"accepted": True, "checked": True}

    def get_publish_template(self, settings, item):
        """
        Retrieves and and validates the publish template from the settings.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process

        :returns: A template representing the publish path of the item or
            None if no template could be identified.
        """
        publisher = self.parent

        publish_template = item.get_property("publish_template")
        if publish_template:
            return publish_template

        publish_template = None
        publish_template_setting = settings.get("Publish Template")

        if publish_template_setting and publish_template_setting.value:
            publish_template = publisher.engine.get_template_by_name(
                publish_template_setting.value
            )
            if not publish_template:
                raise TankError(
                    "Missing Publish Template in templates.yml: %s "
                    % publish_template_setting.value
                )

        # cache it for later use
        item.properties["publish_template"] = publish_template

        return publish_template

    def get_publish_path(self, settings, item):
        """
        Get a publish path for the supplied settings and item.
        :param settings: This plugin instance's configured settings
        :param item: The item to determine the publish path for
        :return: A string representing the output path to supply when
            registering a publish for the supplied item
        Extracts the publish path via the configured work and publish templates
        if possible.
        """

        # publish type explicitly set or defined on the item
        publish_path = item.get_property("publish_path")
        if publish_path:
            return publish_path

        # fall back to template/path logic
        path = item.properties.path

        work_template = item.properties.get("work_template")
        publish_template = self.get_publish_template(settings, item)

        work_fields = []
        publish_path = None

        # We need both work and publish template to be defined for template
        # support to be enabled.
        if work_template and publish_template:
            if work_template.validate(path):
                work_fields = work_template.get_fields(path)

            # add extra fields to be able to fulfill the publish
            # template if this is required
            if item.properties.get("extra_fields"):
                work_fields.update(item.properties["extra_fields"])

            missing_keys = publish_template.missing_keys(work_fields)

            if missing_keys:
                self.logger.warning(
                    "Not enough keys to apply work fields (%s) to "
                    "publish template (%s)" % (work_fields, publish_template)
                )
            else:
                publish_path = publish_template.apply_fields(work_fields)
                self.logger.debug(
                    "Used publish template to determine the publish path: %s"
                    % (publish_path,)
                )
        else:
            self.logger.debug("publish_template: %s" % publish_template)
            self.logger.debug("work_template: %s" % work_template)

        if not publish_path:
            publish_path = path
            self.logger.debug(
                "Could not validate a publish template. Publishing in place."
            )

        return publish_path

    def session_validate(self, settings, item):
        pck = item.properties["package"]
        package_path = pck.getFilePath()

        if not package_path:
            # the session has not been saved before (no path determined).
            # provide a save button. the session will need to be saved before
            # validation will succeed.
            error_msg = (
                "The SubstanceDesigner package has not been saved. Please save your package "
                "before publishing."
            )
            self.logger.error(error_msg, extra=_get_save_as_action())
            raise Exception(error_msg)

        # get the path in a normalized state. no trailing separator,
        # separators are appropriate for current OS, no double separators,
        # etc.
        package_path = sgtk.util.ShotgunPath.normalize(package_path)

        # set the session path on the item for use by the base plugin validation
        # step. NOTE: this path could change prior to the publish phase.
        item.properties["path"] = package_path

        return True

    def templates_validate(self, settings, item):
        valid = True
        package_path = item.properties.get("path")

        # if the session item has a known work template, see if the path
        # matches. if not, warn the user and provide a way to save the file to
        # a different path
        work_template = item.properties.get("work_template")
        if work_template:
            if not work_template.validate(package_path):
                self.logger.warning(
                    (
                        "The current session does not match the configured work file "
                        "template. Please save your session before publishing."
                    ),
                    extra=_get_save_as_action(),
                    valid=False,
                )
            else:
                self.logger.debug("Work template configured and matches session file.")
        else:
            self.logger.debug("No work template configured.")
            valid = False

        # publish template
        publish_template = self.get_publish_template(settings, item)
        if publish_template:
            self.logger.debug("Session Publish template: %s " % publish_template)
        else:
            self.logger.warning("No Publish template defined for the session.")
            valid = False

        return valid

    def version_validate(self, settings, item):
        path = item.properties["path"]

        # ---- see if the version can be bumped post-publish

        # check to see if the next version of the work file already exists on
        # disk. if so, warn the user and provide the ability to jump to save
        # to that version now
        (next_version_path, version) = self._get_next_version_info(path, item)
        if next_version_path and os.path.exists(next_version_path):

            # determine the next available version_number. just keep asking for
            # the next one until we get one that doesn't exist.
            while os.path.exists(next_version_path):
                (next_version_path, version) = self._get_next_version_info(
                    next_version_path, item
                )

            error_msg = "The next version of this file already exists on disk."
            self.logger.error(
                error_msg,
                extra={
                    "action_button": {
                        "label": "Save to v%s" % (version,),
                        "tooltip": "Save to the next available version number, "
                        "v%s" % (version,),
                        "callback": lambda: _save_package(pck, next_version_path),
                    }
                },
            )
            raise Exception(error_msg)

        return True

    def validate_package_output_graphs(self, settings, item):
        """
        Validates the package to check if contains graphs with valid outputs. Returns a
        boolean to indicate validity.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        :returns: True if item is valid, False otherwise.
        """

        # do an extra check to see if there are any output nodes for any
        # of the graphs in the package
        pck = item.properties["package"]

        self.logger.info("Packages Resources: %s" % pck.getChildrenResources(True))

        # seems like only one graph needs to have outputs for the pck to be
        # got to export
        for resource in pck.getChildrenResources(True):
            self.logger.info("Resource <%s> %s" % (type(resource), resource))

            if isinstance(resource, sd.api.sbs.sdsbscompgraph.SDSBSCompGraph):
                output_nodes = resource.getOutputNodes()
                if len(output_nodes) > 0:
                    return True

        error_msg = (
            "Cannot find outputs to cook in the graph %s. Invalid package to publish (%s). Please deselect this from the publisher if you want to continue."
            % (resource.getIdentifier(), self.type_description)
        )
        self.logger.error(error_msg)
        return False

    def validate_graph_output(self, settings, item):
        """
        Validates the graph to check if contains valid outputs. Returns a
        boolean to indicate validity.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        :returns: True if item is valid, False otherwise.
        """

        # do an extra check to see if there are any output nodes for any
        # of the graphs in the package
        resource = item.properties["resource"]

        self.logger.info("Resource <%s> %s" % (type(resource), resource))

        if isinstance(resource, sd.api.sbs.sdsbscompgraph.SDSBSCompGraph):
            output_nodes = resource.getOutputNodes()
            if len(output_nodes) == 0:
                error_msg = (
                    "Cannot find outputs to cook in the graph %s. Invalid package to publish (%s). Please deselect this from the publisher if you want to continue."
                    % (resource.getIdentifier(), self.type_description)
                )
                self.logger.error(error_msg)
                return False

        return True

    def validate(self, settings, item):
        """
        Validates the given item to check that it is ok to publish. Returns a
        boolean to indicate validity.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        :returns: True if item is valid, False otherwise.
        """

        publisher = self.parent

        valid = self.session_validate(settings, item)
        valid = valid and self.templates_validate(settings, item)
        valid = valid and self.version_validate(settings, item)

        # run the base class validation
        return valid and super(
            SubstanceDesignerPackageBasePublishPlugin, self
        ).validate(settings, item)

    def _export(self, settings, item, path):
        raise NotImplementedError

    def _copy_work_to_publish(self, settings, item):
        """
        This method handles the exporting of the .sbsar archive into the
        publish location. It does it by acquiring the fields from the session
        to the work template and applying them to the publish template to
        build the publish path, then exporting the .sbar file using the
        publish file path.
        """

        # ---- ensure templates are available
        work_template = item.properties.get("work_template")
        if not work_template:
            self.logger.debug(
                "No work template set on the item. "
                "Skipping copy file to publish location."
            )
            return

        publish_template = self.get_publish_template(settings, item)
        if not publish_template:
            self.logger.debug(
                "No publish template set on the item. "
                "Skipping copying file to publish location."
            )
            return

        # ---- get a list of files to be copied

        # by default, the path that was collected for publishing
        work_files = [item.properties.path]

        # ---- copy the work files to the publish location

        for work_file in work_files:

            if not work_template.validate(work_file):
                self.logger.warning(
                    "Work file '%s' did not match work template '%s'. "
                    "Publishing in place." % (work_file, work_template)
                )
                return

            work_fields = work_template.get_fields(work_file)

            # add extra fields to be able to fulfill the publish
            # template if this is required
            if item.properties.get("extra_fields"):
                work_fields.update(item.properties["extra_fields"])

            missing_keys = publish_template.missing_keys(work_fields)

            if missing_keys:
                self.logger.warning(
                    "Work file '%s' missing keys required for the publish "
                    "template: %s" % (work_file, missing_keys)
                )
                return

            publish_file = publish_template.apply_fields(work_fields)
            publish_folder = os.path.dirname(publish_file)

            # copy the file
            try:
                ensure_folder_exists(publish_folder)
                self._export(settings, item, publish_file)
            except Exception:
                raise Exception(
                    "Failed to export to '%s'.\n%s"
                    % (publish_file, traceback.format_exc()),
                    extra={"action_show_folder": {"path": publish_folder}},
                )

            self.logger.debug(
                "Exported to '%s'." % (publish_file),
                extra={"action_show_folder": {"path": publish_folder}},
            )

    def get_publish_dependencies(self, settings, item):
        """
        Get publish dependencies for the supplied settings and item.
        :param settings: This plugin instance's configured settings
        :param item: The item to determine the publish dependencies for
        :return: A list of file paths representing the dependencies to store in
            SG for this publish
        """
        # add dependencies for the base class to register when publishing
        item.properties["publish_dependencies"] = self._get_extra_dependencies(
            settings, item
        )

        # let the base class register the publish
        return super(
            SubstanceDesignerPackageBasePublishPlugin, self
        ).get_publish_dependencies(settings, item)

    def _get_extra_dependencies(self, settings, item):
        """
        Find additional dependencies from this publisher
        """
        # Figure out what read nodes are known to the engine and use them
        # as dependencies

        return []


# TODO: method duplicated in all the substancedesigner hooks
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
