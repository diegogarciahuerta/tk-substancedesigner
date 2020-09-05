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
import sys
import cgitb


import sgtk
from sgtk.platform import SoftwareLauncher, SoftwareVersion, LaunchInformation
from sgtk.pipelineconfig_utils import get_sgtk_module_path


__author__ = "Diego Garcia Huerta"
__contact__ = "https://www.linkedin.com/in/diegogh/"


ENGINE_NAME = "tk-substancedesigner"
APPLICATION_NAME = "Substance Designer"

logger = sgtk.LogManager.get_logger(__name__)

# Let's enable cool and detailed tracebacks
cgitb.enable(format="text")


# adapted from:
# https://stackoverflow.com/questions/2270345/finding-the-version-of-an-application-from-python
def get_file_info(filename, info):
    """
    Extract information from a file.
    """
    import array
    from ctypes import windll, create_string_buffer, c_uint, string_at, byref

    # Get size needed for buffer (0 if no info)
    size = windll.version.GetFileVersionInfoSizeA(filename, None)
    # If no info in file -> empty string
    if not size:
        return ""

    # Create buffer
    res = create_string_buffer(size)
    # Load file informations into buffer res
    windll.version.GetFileVersionInfoA(filename, None, size, res)
    r = c_uint()
    l = c_uint()
    # Look for codepages
    windll.version.VerQueryValueA(res, "\\VarFileInfo\\Translation", byref(r), byref(l))
    # If no codepage -> empty string
    if not l.value:
        return ""

    # Take the first codepage (what else ?)
    codepages = array.array("H", string_at(r.value, l.value))
    codepage = tuple(codepages[:2].tolist())

    # Extract information
    windll.version.VerQueryValueA(
        res, ("\\StringFileInfo\\%04x%04x\\" + info) % codepage, byref(r), byref(l)
    )
    return string_at(r.value, l.value)


class SubstanceDesignerLauncher(SoftwareLauncher):
    """
    Handles launching application executables. Automatically starts up
    the shotgun engine with the current context in the new session
    of the application.
    """

    # Named regex strings to insert into the executable template paths when
    # matching against supplied versions and products. Similar to the glob
    # strings, these allow us to alter the regex matching for any of the
    # variable components of the path in one place
    COMPONENT_REGEX_LOOKUP = {
        "platform": r"\(x86\)|\(x64\)",
        "platform_version": r"\(x86\)|\(x64\)",
    }

    # This dictionary defines a list of executable template strings for each
    # of the supported operating systems. The templates are used for both
    # globbing and regex matches by replacing the named format placeholders
    # with an appropriate glob or regex string.
    # Worse case we use to a env variable "$SUBSTANCEDESIGNER_BIN" so it can be
    # configured externally

    EXECUTABLE_TEMPLATES = {
        "darwin": [
            "$SUBSTANCEDESIGNER_BIN",
            "/Applications/Allegorithmic/Substance Designer.app",
        ],
        "win32": [
            "$SUBSTANCEDESIGNER_BIN",
            "C:/Program Files/Allegorithmic/Substance Designer/Substance Designer.exe",
        ],
        "linux2": [
            "$SUBSTANCEDESIGNER_BIN",
            "/usr/Allegorithmic/Substance_Designer/Substance Designer",
            "/usr/Allegorithmic/Substance Designer",
            "/opt/Allegorithmic/Substance_Designer/Substance Designer",
        ],
    }

    def prepare_launch(self, exec_path, args, file_to_open=None):
        """
        Prepares an environment to launch in that will automatically
        load Toolkit and the engine when the application starts.

        :param str exec_path: Path to application executable to launch.
        :param str args: Command line arguments as strings.
        :param str file_to_open: (optional) Full path name of a file to open on
                                            launch.
        :returns: :class:`LaunchInformation` instance
        """
        required_env = {}

        resources_plugins_path = os.path.join(
            self.disk_location, "resources", "plugins"
        )
        required_env["SBS_DESIGNER_PYTHON_PATH"] = os.path.join(
            resources_plugins_path, "shotgun_bridge"
        )

        # Run the engine's init.py file when the application starts up
        startup_path = os.path.join(self.disk_location, "startup", "init.py")
        required_env["SGTK_SUBSTANCEDESIGNER_ENGINE_STARTUP"] = startup_path.replace(
            "\\", "/"
        )

        # Prepare the launch environment with variables required by the
        # classic bootstrap approach.
        self.logger.debug(
            "Preparing %s Launch via Toolkit Classic methodology ..." % APPLICATION_NAME
        )

        required_env["SGTK_ENGINE"] = ENGINE_NAME
        required_env["SGTK_CONTEXT"] = sgtk.context.serialize(self.context)
        required_env["SGTK_SUBSTANCEDESIGNER_SGTK_MODULE_PATH"] = get_sgtk_module_path()

        if file_to_open:
            # Add the file name to open to the launch environment
            required_env["SGTK_FILE_TO_OPEN"] = file_to_open

        os.chdir(os.path.dirname(os.path.dirname(exec_path)))
        return LaunchInformation(path=exec_path, environ=required_env)

    def _icon_from_engine(self):
        """
        Use the default engine icon as the application does not supply
        an icon in their software directory structure.

        :returns: Full path to application icon as a string or None.
        """

        # the engine icon
        engine_icon = os.path.join(self.disk_location, "icon_256.png")
        return engine_icon

    def scan_software(self):
        """
        Scan the filesystem for the application executables.

        :return: A list of :class:`SoftwareVersion` objects.
        """
        self.logger.debug("Scanning for %s executables..." % APPLICATION_NAME)

        supported_sw_versions = []
        for sw_version in self._find_software():
            supported_sw_versions.append(sw_version)

        return supported_sw_versions

    def _find_software(self):
        """
        Find executables in the default install locations.
        """

        # all the executable templates for the current OS
        executable_templates = self.EXECUTABLE_TEMPLATES.get(
            "darwin"
            if sgtk.util.is_macos()
            else "win32"
            if sgtk.util.is_windows()
            else "linux"
            if sgtk.util.is_linux()
            else []
        )

        # all the discovered executables
        found = False
        sw_versions = []

        for executable_template in executable_templates:
            self.logger.debug("PreProcessing template %s.", executable_template)
            executable_template = os.path.expanduser(executable_template)
            executable_template = os.path.expandvars(executable_template)

            self.logger.debug("Processing template %s.", executable_template)

            executable_matches = self._glob_and_match(
                executable_template, self.COMPONENT_REGEX_LOOKUP
            )

            # Extract all products from that executable.
            for (executable_path, key_dict) in executable_matches:
                # extract the matched keys form the key_dict (default to None
                # if not included)
                self.logger.debug(
                    "Processing executable_path: %s | dict %s",
                    executable_path,
                    key_dict,
                )

                if sgtk.util.is_windows():
                    executable_version = get_file_info(executable_path, "FileVersion")
                    # make sure we remove those pesky \x00 characters
                    executable_version = executable_version.strip("\x00")
                else:
                    # no way to extract the version from this application, so no
                    # version is available to display
                    executable_version = " "

                sw_versions.append(
                    SoftwareVersion(
                        executable_version,
                        APPLICATION_NAME,
                        executable_path,
                        self._icon_from_engine(),
                    )
                )
                # TBR DGH010720
                # break here if you found one executable, at least until we
                # find a way to track different versions of Substance Designer.
                found = True
                break

            if found:
                break

        return sw_versions
