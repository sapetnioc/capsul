##########################################################################
# CAPSUL - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

from traits.api import Bool, Str, Undefined, Instance, List, Dict
from capsul.study_config.study_config import StudyConfigModule
from soma.controller import Controller


class SomaWorkflowConfig(StudyConfigModule):

    class ResourceController(Controller):
        def __init__(self, dummy=None):
            super(SomaWorkflowConfig.ResourceController, self).__init__()
            self.add_trait(
                'transfer_paths', List(
                    [],
                    output=False,
                    desc='list of paths where files have to be transferred '
                    'by soma-workflow'))
            self.add_trait(
                'path_translations', Dict(
                    value={},
                    key_trait=Str(),
                    value_trait=Str(),
                    output=False,
                    desc='Soma-workflow paths translations mapping: '
                    '{local_path: remote_path}'))

    def __init__(self, study_config, configuration):
        super(SomaWorkflowConfig, self).__init__(study_config, configuration)
        study_config.add_trait('use_soma_workflow', Bool(
            False,
            output=False,
            desc='Use soma workflow for the execution'))
        study_config.add_trait('somaworkflow_computing_resource', Str(
            Undefined,
            output=False,
            desc='Soma-workflow computing resource to be used to run processing'))

        study_config.add_trait(
            'somaworkflow_computing_resources_config',
                Instance(Controller,
                    output=False, allow_none=False,
                    desc='Computing resource config'))
        study_config.somaworkflow_computing_resources_config = Controller()
        study_config.somaworkflow_computing_resources_config.add_trait(
            'localhost',
            Instance(SomaWorkflowConfig.ResourceController,
                output=False, allow_none=False,
                desc='Computing resource config'))
        study_config.somaworkflow_computing_resources_config.localhost = \
            SomaWorkflowConfig.ResourceController()

        #study_config.add_trait(
            #'somaworkflow_computing_resources_config',
            #Dict(
                #key_trait=Str(
                    #'localhost',
                    #output=False, desc='Computing resource name',
                    #allow_none=False),
                #value_trait=Instance(
                    #SomaWorkflowConfig.ResourceController,
                    #output=False, allow_none=False,
                    #dummy=None,
                    #desc='Computing resource config'),
                #output=False,
                #desc='Soma-workflow computing resources configs',
                #allow_none=False))

        #study_config.add_trait(
            #'somaworkflow_computing_resources_config',
            #Instance(Controller,
                #output=False,
                #desc='Soma-workflow computing resources configs',
                #allow_none=False))
        #study_config.somaworkflow_computing_resources_config = Controller()
        #study_config.somaworkflow_computing_resources_config.add_trait(
            #'transfer_paths', List(
                #[],
                #output=False,
                #desc='list of paths where files have to be transferred by '
                #'soma-workflow'))
        #study_config.somaworkflow_computing_resources_config.add_trait(
            #'path_translations', Dict(
                #{},
                #output=False,
                #desc='Soma-workflow paths translations mapping: '
                #'{local_path: remote_path}'))

    def initialize_callbacks(self):
        self.study_config.on_trait_change(
            self.initialize_module, 'use_soma_workflow')
