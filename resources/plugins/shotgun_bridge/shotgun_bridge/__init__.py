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

# Designer imports
import sd

#
# Plugin entry points.
#

import os
import imp
import sys

import logging

__author__ = "Diego Garcia Huerta"
__contact__ = "https://www.linkedin.com/in/diegogh/"


# Create a logger.
logger = logging.getLogger("shotgun_bridge")

# Add a handler to redirect logging to Designer's console panel.
ctx = sd.getContext()
logger.addHandler(ctx.createRuntimeLogHandler())

# Do not propagate log messages to Python's root logger.
logger.propagate = False

# Set the default log level if needed.
logger.setLevel(logging.DEBUG)


SGTK_MODULE_PATH = os.environ.get("SGTK_SUBSTANCEDESIGNER_SGTK_MODULE_PATH")
if SGTK_MODULE_PATH and SGTK_MODULE_PATH not in sys.path:
    sys.path.insert(0, SGTK_MODULE_PATH)


def start_plugin():
    # only bootstrap if we are in a shotgun environment
    if SGTK_MODULE_PATH:
        bootstrap()
    else:
        logger.warning(
            "[SubstanceDesigner Shotgun Engine] "
            "SubstanceDesigner was not run within a Shotgun Environment. "
            "Skipping ShotgunBridge Extension."
        )


def close_plugin():
    pass


def bootstrap():
    engine_startup_path = os.environ.get("SGTK_SUBSTANCEDESIGNER_ENGINE_STARTUP")
    engine_startup = imp.load_source(
        "sgtk_substancedesigner_engine_startup", engine_startup_path
    )

    # Fire up Toolkit and the environment engine when there's time.
    engine_startup.start_toolkit()


def initializeSDPlugin():
    logger.info("Shotgun Engine initializeSDPlugin")
    start_plugin()


def uninitializeSDPlugin():
    logger.info("Shotgun Engine uninitializeSDPlugin")
