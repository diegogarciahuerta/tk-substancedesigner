# Copyright (c) 2018 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

# This is great trick from:
#   Barbara Laigneau <barbara@dark-shot.com>

# It allows to customize the name that we use for when we save the session.
# Originally only one name can be specified in the configuration yml file,
# but if a hook name is specified in the form:
# hook:<name of the core hook>
# if gets executed as a hook. This has allow us to figure out the name field
# fr when we save the session based of either the file path that is saved to
# or the graphs that it contains.


import os
from sgtk import Hook


class SaveAsDefaultName(Hook):
    """"""

    def execute(self, setting, bundle_obj, extra_params, **kwargs):
        """
        Get a name from the current context

        :param setting: The name of the setting for which we are evaluating
                        In our example above, it would be template_snapshot.

        :param bundle_obj: The app, engine or framework object that the setting
                           is associated with.

        :param extra_params: List of options passed from the setting. If the settings
                             string is "hook:hook_name:foo:bar", extra_params would
                             be ['foo', 'bar']

        returns: needs to return the name of the file, as a string
        """

        import sd

        ctx = sd.getContext()
        app = ctx.getSDApplication()
        pm = app.getPackageMgr()
        uiMgr = app.getQtForPythonUIMgr()
        current_graph = uiMgr.getCurrentGraph()

        graph_ids = []
        if current_graph:
            pck = current_graph.getPackage()
            pck_path = pck.getFilePath()
            if pck_path:
                pck_filename = os.path.basename(pck_path)
                name_field, _ = os.path.splitext(pck_filename)
                return name_field

            if pck:
                for resource in pck.getChildrenResources(False):
                    if isinstance(resource, sd.api.sdgraph.SDGraph):
                        graph_ids.append(resource.getIdentifier())

        if graph_ids:
            name_field = "_".join(graph_ids)
        else:
            name_field = "scene"

        return name_field
