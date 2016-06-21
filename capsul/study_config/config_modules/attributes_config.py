##########################################################################
# CAPSUL - Copyright (C) CEA, 2016
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

import os
import six
from traits.api import Bool, Str, Undefined, List
from capsul.study_config.study_config import StudyConfigModule
from capsul.attributes_factory import AttributesFactory
from capsul.attributes_schema import AttributesSchema
from capsul.attributes.completion_engine \
    import ProcessCompletionEngineFactory, PathCompletionEngineFactory


class AttributesConfig(StudyConfigModule):
    '''Attributes-based completion configuration module for StudyConfig
    '''

    dependencies = []

    def __init__(self, study_config, configuration):
        super(AttributesConfig, self).__init__(study_config, configuration)
        default_paths = ['capsul.attributes.completion_engine',
                         'capsul.attributes.fom_completion_engine']
        self.study_config.add_trait(
            'attributes_schema_paths',
            List(default_paths, Str(Undefined, output=False), output=False,
            desc='attributes shchema module name'))


    def initialize_module(self):
        '''
        '''
        factory = AttributesFactory()
        factory.class_types['schema'] = AttributesSchema
        factory.class_types['process_completion'] \
          = ProcessCompletionEngineFactory
        factory.class_types['path_completion'] \
          = PathCompletionEngineFactory

        self.study_config.modules_data.attributes_factory = factory
        factory.module_path = self.study_config.attributes_schema_paths


    def initialize_callbacks(self):
        self.study_config.on_trait_change(
            self.initialize_module,
            ['attributes_schema', 'process_completion_model',
             'path_completion_model'])

