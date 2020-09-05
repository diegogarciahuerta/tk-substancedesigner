# Copyright (c) 2013 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

"""
A SubstanceDesigner engine for Tank.
https://www.substance3d.com/products/substance-designer/
"""

import os
import sys
import time
import inspect
import logging
import traceback

# enable cool tracebacks
import cgitb

cgitb.enable(format="text")

import tank
from tank.log import LogManager
from tank.platform import Engine
from tank.util import is_windows, is_linux, is_macos

import tank.platform.framework

import sd

__author__ = "Diego Garcia Huerta"
__contact__ = "https://www.linkedin.com/in/diegogh/"


ENGINE_NAME = "tk-substancedesigner"
APPLICATION_NAME = "Substance Designer"


# environment variable that control if to show the compatibility warning dialog
# when SubstanceDesigner software version is above the tested one.
SHOW_COMP_DLG = "SGTK_COMPATIBILITY_DIALOG_SHOWN"

# this is the absolute minimum SubstanceDesigner version for the engine to work. Actually
# the one the engine was developed originally under, so change it at your
# own risk if needed.
MIN_COMPATIBILITY_VERSION = 10.1

# this is a place to put our persistent variables between different packages
# opened
if not hasattr(sd, "shotgun"):
    sd.shotgun = lambda: None

# Although the engine has logging already, this logger is needed for logging
# where an engine may not be present.
logger = LogManager.get_logger(__name__)


# let's log directly to substance designer logs
SUBSTANCEDESIGNER_LOG_HANDLER = sd.getContext().createRuntimeLogHandler()
# tk loggers require this so we patch the substance designer logger
# otherwise we would have to forward message by message to the
# substancedesigner logger.
SUBSTANCEDESIGNER_LOG_HANDLER.inside_dispatch = False


# logging functionality
def show_error(msg):
    from PySide2.QtWidgets import QMessageBox

    QMessageBox.critical(None, "Shotgun Error | %s engine" % APPLICATION_NAME, msg)


def show_warning(msg):
    from PySide2.QtWidgets import QMessageBox

    QMessageBox.warning(None, "Shotgun Warning | %s engine" % APPLICATION_NAME, msg)


def show_info(msg):
    from PySide2.QtWidgets import QMessageBox

    QMessageBox.information(None, "Shotgun Info | %s engine" % APPLICATION_NAME, msg)


def display_error(msg):
    # Add a handler to redirect logging to Designer's console panel.
    ctx = sd.getContext()
    logger.addHandler(ctx.createRuntimeLogHandler())

    substancedesigner.qCritical(msg)
    t = time.asctime(time.localtime())
    message = "%s - Shotgun Error | %s engine | %s " % (t, APPLICATION_NAME, msg)
    print(message)


def display_warning(msg):
    substancedesigner.qWarning(msg)
    t = time.asctime(time.localtime())
    message = "%s - Shotgun Warning | %s engine | %s " % (t, APPLICATION_NAME, msg)
    print(message)


def display_info(msg):
    # SubstanceDesigner 4.0.0 did not have qInfo yet, so use debug instead
    if hasattr(substancedesigner, "qInfo"):
        substancedesigner.qInfo(msg)
    else:
        substancedesigner.qDebug(msg)
    t = time.asctime(time.localtime())
    message = "%s - Shotgun Information | %s engine | %s " % (t, APPLICATION_NAME, msg)
    print(message)


def display_debug(msg):
    if os.environ.get("TK_DEBUG") == "1":
        substancedesigner.qDebug(msg)
        t = time.asctime(time.localtime())
        message = "%s - Shotgun Debug | %s engine | %s " % (t, APPLICATION_NAME, msg)
        print(message)


# methods to support the state when the engine cannot start up
# for example if a non-tank file is loaded in SubstanceDesigner we load the project
# context if exists, so we give a chance to the user to at least
# do the basics operations.
def refresh_engine():
    """
    refresh the current engine
    """

    logger.debug("Refreshing the engine")

    engine = tank.platform.current_engine()

    if not engine:
        # If we don't have an engine for some reason then we don't have
        # anything to do.
        logger.debug(
            "%s Refresh_engine | No currently initialized engine found; aborting the refresh of the engine\n"
            % APPLICATION_NAME
        )
        return

    # _fix_tk_multi_pythonconsole(logger)

    # get the current package filename
    current_package_filename = None

    ctx = sd.getContext()
    app = ctx.getSDApplication()
    pm = app.getPackageMgr()
    uiMgr = app.getQtForPythonUIMgr()

    current_graph = uiMgr.getCurrentGraph()
    if current_graph:
        pck = current_graph.getPackage()
        current_package_filename = pck.getFilePath()

    if not current_package_filename:
        logger.debug("File has not been saved yet, aborting the refresh of the engine.")
        return

    # make sure path is normalized
    current_package_filename = os.path.abspath(current_package_filename)

    # we are going to try to figure out the context based on the
    # active document
    current_context = tank.platform.current_engine().context

    ctx = current_context

    # this file could be in another project altogether, so create a new
    # API instance.
    try:
        # and construct the new context for this path:
        tk = tank.sgtk_from_path(current_package_filename)
        logger.debug(
            "Extracted sgtk instance: '%r' from path: '%r'",
            tk,
            current_package_filename,
        )

    except tank.TankError:
        # could not detect context from path, will use the project context
        # for menus if it exists
        message = (
            "Shotgun %s Engine could not detect the context\n"
            "from the active document. Shotgun menus will be  \n"
            "stay in the current context '%s' "
            "\n" % (APPLICATION_NAME, ctx)
        )
        display_warning(message)
        return

    ctx = tk.context_from_path(current_package_filename, current_context)
    logger.debug(
        "Given the path: '%s' the following context was extracted: '%r'",
        current_package_filename,
        ctx,
    )

    # default to project context in worse case scenario
    if not ctx:
        project_name = engine.context.project.get("name")
        ctx = tk.context_from_entity_dictionary(engine.context.project)
        logger.debug(
            (
                "Could not extract a context from the current active project "
                "path, so we revert to the current project '%r' context: '%r'"
            ),
            project_name,
            ctx,
        )

    # Only change if the context is different
    if ctx != current_context:
        try:
            engine.change_context(ctx)
        except tank.TankError:
            message = (
                "Shotgun %s Engine could not change context\n"
                "to '%r'. Shotgun menu will be disabled!.\n"
                "\n" % (APPLICATION_NAME, ctx)
            )
            display_warning(message)
            engine.create_shotgun_menu(disabled=True)


class SubstanceDesignerEngine(Engine):
    """
    Toolkit engine for SubstanceDesigner.
    """

    def __init__(self, *args, **kwargs):
        """
        Engine Constructor
        """

        # Add instance variables before calling our base class
        # __init__() because the initialization may need those
        # variables.
        self._dock_widgets = []

        tank.platform.Engine.__init__(self, *args, **kwargs)

        # this is where we connect the engine logger to the application
        # logger
        handler_types = [
            isinstance(handler, sd.logger.SDRuntimeLogHandler)
            for handler in self.logger.handlers
        ]
        has_substancedesigner_handler = any(handler_types)
        if not has_substancedesigner_handler:
            self.logger.addHandler(SUBSTANCEDESIGNER_LOG_HANDLER)
            self.logger.propagate = False

    @property
    def context_change_allowed(self):
        """
        Whether the engine allows a context change without the need for a restart.
        """
        return True

    @property
    def host_info(self):
        """
        :returns: A dictionary with information about the application hosting this
                  engine.

        The returned dictionary is of the following form on success:

            {
                "name": "Substance Designer",
                "version": "10.1.3",
            }

        The returned dictionary is of following form on an error preventing
        the version identification.

            {
                "name": "Substance Designer",
                "version: "unknown"
            }
        """

        host_info = {"name": APPLICATION_NAME, "version": "unknown"}
        try:
            from PySide2 import QtWidgets

            app = QtWidgets.QApplication.instance()
            substancedesigner_ver = app.applicationVersion()
            host_info["version"] = substancedesigner_ver
        except Exception:
            # Fallback to 'Substance Designer' initialized above
            pass
        return host_info

    def _on_active_package_timer(self):
        """
        Refresh the engine if the current package has changed since the last
        time we checked.
        """
        ctx = sd.getContext()
        app = ctx.getSDApplication()
        uiMgr = app.getQtForPythonUIMgr()

        active_package = None
        current_graph = uiMgr.getCurrentGraph()
        if current_graph:
            pck = current_graph.getPackage()
            active_package = pck.getFilePath()

        if active_package and self.active_package != active_package:
            self.active_package = active_package
            refresh_engine()

    def pre_app_init(self):
        """
        Runs after the engine is set up but before any apps have been
        initialized.
        """
        from tank.platform.qt import QtCore

        # unicode characters returned by the shotgun api need to be converted
        # to display correctly in all of the app windows
        # tell QT to interpret C strings as utf-8
        utf8 = QtCore.QTextCodec.codecForName("utf-8")
        QtCore.QTextCodec.setCodecForCStrings(utf8)
        self.logger.debug("set utf-8 codec for widget text")

        # We use a timer to know when the user changes graph/package
        # selection.
        #
        # Since the restart of the engine every time a view is chosen is an
        # expensive operation, we will offer this functionality as an option
        # inside the context menu.
        #
        self.active_package = None
        self.active_package_timer = QtCore.QTimer()
        self.active_package_timer.timeout.connect(self._on_active_package_timer)

    def init_engine(self):
        """
        Initializes the SubstanceDesigner engine.
        """
        self.logger.debug("%s: Initializing...", self)

        # check that we are running a supported OS
        if not any([is_windows(), is_linux(), is_macos()]):
            raise tank.TankError(
                "The current platform is not supported!"
                " Supported platforms "
                "are Mac, Linux 64 and Windows 64."
            )

        # check that we are running an ok version of SubstanceDesigner
        substancedesigner_build_version = self.host_info.get("version")
        substancedesigner_ver = float(
            ".".join(substancedesigner_build_version.split(".")[:2])
        )

        if substancedesigner_ver < MIN_COMPATIBILITY_VERSION:
            msg = (
                "Shotgun integration is not compatible with %s versions older than %s"
                % (APPLICATION_NAME, MIN_COMPATIBILITY_VERSION)
            )
            show_error(msg)
            raise tank.TankError(msg)

        if substancedesigner_ver > MIN_COMPATIBILITY_VERSION:
            # show a warning that this version of SubstanceDesigner isn't yet fully tested
            # with Shotgun:
            msg = (
                "The Shotgun Pipeline Toolkit has not yet been fully "
                "tested with %s %s.  "
                "You can continue to use Toolkit but you may experience "
                "bugs or instability."
                "\n\n" % (APPLICATION_NAME, substancedesigner_build_version)
            )

            # determine if we should show the compatibility warning dialog:
            show_warning_dlg = self.has_ui and SHOW_COMP_DLG not in os.environ

            if show_warning_dlg:
                # make sure we only show it once per session
                os.environ[SHOW_COMP_DLG] = "1"

                # split off the major version number - accommodate complex
                # version strings and decimals:
                major_version_number_str = substancedesigner_build_version.split(".")[0]
                if major_version_number_str and major_version_number_str.isdigit():
                    # check against the compatibility_dialog_min_version
                    # setting
                    min_ver = self.get_setting("compatibility_dialog_min_version")
                    if int(major_version_number_str) < min_ver:
                        show_warning_dlg = False

            if show_warning_dlg:
                # Note, title is padded to try to ensure dialog isn't insanely
                # narrow!
                show_info(msg)

            # always log the warning to the script editor:
            self.logger.warning(msg)

            # In the case of Windows, we have the possibility of locking up if
            # we allow the PySide shim to import QtWebEngineWidgets.
            # We can stop that happening here by setting the following
            # environment variable.

            # Note that prior PySide2 v5.12 this module existed, after that it has
            # been separated and would not cause any issues. Since it is no
            # harm if the module is not there, we leave it just in case older
            # versions of SubstanceDesigner were using previous versions of PyQt
            # https://www.riverbankcomputing.com/software/pyqtwebengine/intro
            if is_windows():
                self.logger.debug(
                    "This application on Windows can deadlock if QtWebEngineWidgets "
                    "is imported. Setting "
                    "SHOTGUN_SKIP_QTWEBENGINEWIDGETS_IMPORT=1..."
                )
                os.environ["SHOTGUN_SKIP_QTWEBENGINEWIDGETS_IMPORT"] = "1"

        # check that we can load the GUI libraries
        self._init_pyside()

        # default menu name is Shotgun but this can be overriden
        # in the configuration to be Sgtk in case of conflicts
        self._menu_name = "Shotgun"
        if self.get_setting("use_sgtk_as_menu_name", False):
            self._menu_name = "Sgtk"

    def __get_active_package_context_switch(self):
        """
        Returns the status of the automatic context switch.
        """
        if not hasattr(sd.shotgun, "active_package_context_switch"):
            self.active_package_context_switch = self.get_setting(
                "active_package_context_switch", False
            )

        return sd.shotgun.active_package_context_switch

    def __set_active_package_context_switch(self, value):
        """
        Sets the status of the automatic context switch.
        """
        sd.shotgun.active_package_context_switch = value

        self.log_info("set_active_package_context_switch: %s" % value)

        if not value:
            self.active_package_timer.stop()
        else:
            self.active_package_timer.start(1000)

    active_package_context_switch = property(
        __get_active_package_context_switch, __set_active_package_context_switch
    )

    def toggle_active_package_context_switch(self):
        """
        Toggles the automatic switch context when the view is changed. If the
        filename of the view is different than the current one, we restart the
        engine with a new context if different than the current.
        """
        self.active_package_context_switch = not self.active_package_context_switch

        return self.active_package_context_switch

    def create_shotgun_menu(self, disabled=False):
        """
        Creates the main shotgun menu in SubstanceDesigner.
        Note that this only creates the menu, not the child actions
        :return: bool
        """

        # only create the shotgun menu if not in batch mode and menu doesn't
        # already exist
        if self.has_ui:
            # create our menu handler
            tk_substancedesigner = self.import_module("tk_substancedesigner")
            if tk_substancedesigner.can_create_menu():
                self.logger.debug("Creating shotgun menu...")
                self._menu_generator = tk_substancedesigner.MenuGenerator(
                    self, self._menu_name
                )
                self._menu_generator.create_menu(disabled=disabled)
            else:
                self.logger.debug("Waiting for menu to be created...")
                from sgtk.platform.qt import QtCore

                QtCore.QTimer.singleShot(200, self.create_shotgun_menu)
            return True

        return False

    def post_app_init(self):
        """
        Called when all apps have initialized
        """
        tank.platform.engine.set_current_engine(self)

        # create the shotgun menu
        self.create_shotgun_menu()

        # let's close the windows created by the engine before exiting the
        # application
        from sgtk.platform.qt import QtGui

        app = QtGui.QApplication.instance()
        app.aboutToQuit.connect(self.destroy_engine)

        # apply a fix to multi python console if loaded
        # pythonconsole_app = self.apps.get("tk-multi-pythonconsole")
        # if pythonconsole_app:
        #     _fix_tk_multi_pythonconsole(self.logger)

        # Run a series of app instance commands at startup.
        self._run_app_instance_commands()

    def post_context_change(self, old_context, new_context):
        """
        Runs after a context change. The SubstanceDesigner event watching will be stopped
        and new callbacks registered containing the new context information.

        :param old_context: The context being changed away from.
        :param new_context: The new context being changed to.
        """

        # apply a fix to multi python console if loaded
        # pythonconsole_app = self.apps.get("tk-multi-pythonconsole")
        # if pythonconsole_app:
        #     _fix_tk_multi_pythonconsole(self.logger)

        if self.get_setting("automatic_context_switch", True):
            # finally create the menu with the new context if needed
            if old_context != new_context:
                self.create_shotgun_menu()

    def _run_app_instance_commands(self):
        """
        Runs the series of app instance commands listed in the
        'run_at_startup' setting of the environment configuration YAML file.
        """

        # Build a dictionary mapping app instance names to dictionaries of
        # commands they registered with the engine.
        app_instance_commands = {}
        for (cmd_name, value) in self.commands.items():
            app_instance = value["properties"].get("app")
            if app_instance:
                # Add entry 'command name: command function' to the command
                # dictionary of this app instance.
                cmd_dict = app_instance_commands.setdefault(
                    app_instance.instance_name, {}
                )
                cmd_dict[cmd_name] = value["callback"]

        # Run the series of app instance commands listed in the
        # 'run_at_startup' setting.
        for app_setting_dict in self.get_setting("run_at_startup", []):
            app_instance_name = app_setting_dict["app_instance"]

            # Menu name of the command to run or '' to run all commands of the
            # given app instance.
            setting_cmd_name = app_setting_dict["name"]

            # Retrieve the command dictionary of the given app instance.
            cmd_dict = app_instance_commands.get(app_instance_name)

            if cmd_dict is None:
                self.logger.warning(
                    "%s configuration setting 'run_at_startup' requests app"
                    " '%s' that is not installed.",
                    self.name,
                    app_instance_name,
                )
            else:
                if not setting_cmd_name:
                    # Run all commands of the given app instance.
                    for (cmd_name, command_function) in cmd_dict.items():
                        msg = (
                            "%s startup running app '%s' command '%s'.",
                            self.name,
                            app_instance_name,
                            cmd_name,
                        )
                        self.logger.debug(msg)

                        command_function()
                else:
                    # Run the command whose name is listed in the
                    # 'run_at_startup' setting.
                    command_function = cmd_dict.get(setting_cmd_name)
                    if command_function:
                        msg = (
                            "%s startup running app '%s' command '%s'.",
                            self.name,
                            app_instance_name,
                            setting_cmd_name,
                        )
                        self.logger.debug(msg)

                        command_function()
                    else:
                        known_commands = ", ".join("'%s'" % name for name in cmd_dict)
                        self.logger.warning(
                            "%s configuration setting 'run_at_startup' "
                            "requests app '%s' unknown command '%s'. "
                            "Known commands: %s",
                            self.name,
                            app_instance_name,
                            setting_cmd_name,
                            known_commands,
                        )

    def destroy_engine(self):
        """
        Let's close the windows created by the engine before exiting the
        application
        """
        self.logger.debug("%s: Destroying...", self)
        self.close_windows()

    def _init_pyside(self):
        """
        Checks if we can load PySide2 in this application
        """

        # import QtWidgets first or we are in trouble
        try:
            import PySide2.QtWidgets
        except Exception as e:
            traceback.print_exc()
            self.logger.error(
                "PySide2 could not be imported! Apps using UI"
                " will not operate correctly!"
                "Error reported: %s",
                e,
            )

    def _get_dialog_parent(self):
        """
        Get the QWidget parent for all dialogs created through
        show_dialog & show_modal.
        """
        ctx = sd.getContext()
        app = ctx.getSDApplication()
        uiMgr = app.getQtForPythonUIMgr()

        return uiMgr.getMainWindow()

    def show_panel(self, panel_id, title, bundle, widget_class, *args, **kwargs):
        """
        Docks an app widget in a SubstanceDesigner Docket, (conveniently borrowed from the
        tk-3dsmax engine)
        :param panel_id: Unique identifier for the panel, as obtained by register_panel().
        :param title: The title of the panel
        :param bundle: The app, engine or framework object that is associated with this window
        :param widget_class: The class of the UI to be constructed.
                             This must derive from QWidget.
        Additional parameters specified will be passed through to the widget_class constructor.
        :returns: the created widget_class instance
        """
        self.logger.debug("show_panel: %s" % panel_id)

        from sgtk.platform.qt import QtGui, QtCore

        ctx = sd.getContext()
        app = ctx.getSDApplication()
        uiMgr = app.getQtForPythonUIMgr()
        main_window = uiMgr.getMainWindow()

        dock_widget_id = "sgtk_dock_widget_" + panel_id
        widget_id = dock_widget_id + "_widget_instance"

        dock_widget = main_window.findChild(QtGui.QWidget, dock_widget_id)

        # create the dock widget if it does not exists
        if not dock_widget:
            self.logger.debug("Creating Dock widget with id: %s" % dock_widget_id)
            dock_widget = uiMgr.newDockWidget(dock_widget_id, title)
            dock_widget.setObjectName(dock_widget_id)
            dock_layout = QtGui.QVBoxLayout()
            dock_widget.setLayout(dock_layout)
        else:
            self.logger.debug("Found Dock widget with id: %s" % dock_widget_id)

        # get the shotgun widget if it already exists
        widget_instance = None
        for widget in QtGui.QApplication.allWidgets():
            if widget.objectName() == widget_id:
                self.logger.debug("Found shotgun widget with id: %s" % widget_id)
                widget_instance = widget
                break

        # or create it if it does not
        if not widget_instance:
            self.logger.debug("Creating shotgun widget with id: %s" % widget_id)
            widget_instance = widget_class(*args, **kwargs)
            widget_instance.setObjectName(widget_id)
            self._apply_external_styleshet(bundle, widget_instance)

        # reparent the shotgun toolkit widget under the application
        # to prevent it from being deleted.
        parent = self._get_dialog_parent()
        widget_instance.setParent(parent)

        # Finally add the shotgun widget to the dock
        dock_widget.layout().addWidget(widget_instance)

        # it is actually the parent the one that is a QDockWidget
        dock_widget.parent().show()

        return widget_instance

    @property
    def has_ui(self):
        """
        Detect and return if SubstanceDesigner is running in batch mode
        """
        return True

    def close_windows(self):
        """
        Closes the various windows (dialogs, panels, etc.) opened by the
        engine.
        """
        self.logger.debug("Closing all engine dialogs...")

        # Make a copy of the list of Tank dialogs that have been created by the
        # engine and are still opened since the original list will be updated
        # when each dialog is closed.
        opened_dialog_list = self.created_qt_dialogs[:]

        # Loop through the list of opened Tank dialogs.
        for dialog in opened_dialog_list:
            dialog_window_title = dialog.windowTitle()
            try:
                # Close the dialog and let its close callback remove it from
                # the original dialog list.
                dialog.close()
            except Exception as exception:
                traceback.print_exc()
                self.logger.error(
                    "Cannot close dialog %s: %s", dialog_window_title, exception
                )

        # Close all dock widgets previously added.
        for dock_widget in self._dock_widgets[:]:
            dock_widget.close()
