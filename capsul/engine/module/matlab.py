#import os
#import weakref

#from soma.controller import Controller
#from traits.api import File, Undefined, Instance

    
def init_settings(capsul_engine):
    with capsul_engine.settings as settings:
        settings.ensure_module_fields('matlab',
        [dict(name='executable',
              type='string',
              description='Full path of the matlab executable'),
         ])


def check_configurations():
    '''
    Check if the activated configuration is valid for Matlaband return
    an error message if there is an error or None if everything is good.
    '''
    matlab_executable = capsul.engine.configurations.get('matalb',{}).get('executable')
    if not matlab_executable:
        return 'MATLAB_EXECUTABLE is not defined'
    if not os.path.exists(matlab_executable):
        return 'Matlab executable is defined as "%s" but this path does not exist' % matlab_executable
    return None

    



