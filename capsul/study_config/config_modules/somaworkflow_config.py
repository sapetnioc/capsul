##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

from traits.api import Bool, Str, Undefined, List, Dict, File
from capsul.study_config.study_config import StudyConfigModule
from soma.controller import Controller, ControllerTrait, OpenKeyController


class SomaWorkflowConfig(StudyConfigModule):

    class ResourceController(Controller):
        def __init__(self):
            super(SomaWorkflowConfig.ResourceController, self).__init__()
            self.add_trait(
                'queue',
                Str(Undefined, output=False,
                    desc='Jobs queue to be used on the computing resource for '
                    'workflow submissions'))
            self.add_trait(
                'transfer_paths', List(
                    [],
                    output=False,
                    desc='list of paths where files have to be transferred '
                    'by soma-workflow'))
            self.add_trait(
                'path_translations',
                ControllerTrait(
                    OpenKeyController(
                        value_trait=List(trait=Str(), value=('', ''),
                        minlen=2, maxlen=2)),
                    output=False,
                    desc='Soma-workflow paths translations mapping: '
                    '{local_path: (identifier, uuid)}'))

    def __init__(self, study_config, configuration):

        super(SomaWorkflowConfig, self).__init__(study_config, configuration)
        study_config.add_trait('use_soma_workflow', Bool(
            False,
            output=False,
            desc='Use soma workflow for the execution'))
        study_config.add_trait(
            'somaworkflow_computing_resource',
            Str(
                Undefined,
                output=False,
                desc='Soma-workflow computing resource to be used to run processing'))
        study_config.add_trait(
            'somaworkflow_config_file',
            File(Undefined, output=False, optional=True,
                 desc='Soma-Workflow configuration file. '
                 'Default: $HOME/.soma_workflow.cfg'))
        study_config.add_trait(
            'somaworkflow_keep_failed_workflows',
            Bool(
                True,
                desc='Keep failed workflows after pipeline execution through '
                'StudyConfig'))
        study_config.add_trait(
            'somaworkflow_keep_succeeded_workflows',
            Bool(
                False,
                desc='Keep succeeded workflows after pipeline execution '
                'through StudyConfig'))
        study_config.add_trait(
            'somaworkflow_computing_resources_config',
            ControllerTrait(
                OpenKeyController(
                    value_trait=ControllerTrait(
                        SomaWorkflowConfig.ResourceController(),
                        output=False, allow_none=False,
                        desc='Computing resource config')),
                output=False, allow_none=False,
                desc='Computing resource config'))
        self.study_config.modules_data.somaworkflow = {}

    def initialize_callbacks(self):
        self.study_config.on_trait_change(
            self.initialize_module, 'use_soma_workflow')

    def get_resource_id(self, resource_id=None, set_it=False):
        if resource_id is None:
            resource_id = self.study_config.somaworkflow_computing_resource
        else:
            self.study_config.somaworkflow_computing_resource = resource_id
        if resource_id in (None, Undefined, 'localhost'):
            import socket
            resource_id = socket.gethostname()
        if set_it:
            self.study_config.somaworkflow_computing_resource = resource_id
        return resource_id

    def set_computing_resource_password(self, resource_id, password=None,
                                        rsa_key_password=None):
        resource_id = self.get_resource_id(resource_id)
        r = self.study_config.modules_data.somaworkflow.setdefault(
            resource_id, Controller())
        if password:
            r.password = password
        if rsa_key_password:
            r.rsa_key_password = rsa_key_password

    def get_workflow_controller(self, resource_id=None):
        resource_id = self.get_resource_id(resource_id)

        r = self.study_config.modules_data.somaworkflow.setdefault(
            resource_id, Controller())
        wc = getattr(r, 'workflow_controller', None)
        return wc

    def connect_resource(self, resource_id=None, force_reconnect=False):
        ''' Connect a soma-workflow computing resource.

        Sets the current resource to the given resource_id (transformed by
        get_resource_id() if None or "localhost" is given, for instance).

        Parameters
        ----------
        resource_id: str (optional)
            resource name, may be None or "localhost". If None, the current
            one (study_config.somaworkflow_computing_resource) is used, or
            the localhost if none is configured.
        force_reconnect: bool (optional)
            if True, if an existing workflow controller is already connected,
            it will be disconnected (deleted) and a new one will be connected.
            If False, an existing controller will be reused without
            reconnection.
        '''
        import soma_workflow.client as swclient

        resource_id = self.get_resource_id(resource_id, True)

        if force_reconnect:
            self.disconnect_resource(resource_id)

        r = self.study_config.modules_data.somaworkflow.setdefault(
            resource_id, Controller())

        if not force_reconnect:
            wc = self.get_workflow_controller(resource_id)
            if wc is not None:
                return wc

        conf_file = self.study_config.somaworkflow_config_file
        if conf_file in (None, Undefined):
            conf_file \
                = swclient.configuration.Configuration.search_config_path()
        login = swclient.configuration.Configuration.get_logins(
            conf_file).get(resource_id)
        password = getattr(r, 'password', None)
        rsa_key_pass = getattr(r, 'rsa_key_password', None)
        wc = swclient.WorkflowController(
            resource_id=resource_id,
            login=login,
            password=password,
            rsa_key_pass=rsa_key_pass)
        r.workflow_controller = wc

    def disconnect_resource(self, resource_id=None):
        resource_id = self.get_resource_id(resource_id, True)
        wc = self.get_workflow_controller(resource_id)
        if wc:
            wc.disconnect()
            del self.study_config.modules_data.somaworkflow[
                self.study_config.somaworkflow_computing_resource
                ].workflow_controller

