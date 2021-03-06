import importlib
from uuid import uuid4

'''
This module provides classes to store CapsulEngine settings for several execution environment and choose a configuration for a given execution environment. Setting management in Capsul has several features that makes it different from classical ways to deal with configuration:
- CapsulEngine must be able to deal with several configurations for the same software. For instance, one can configure both SPM 8 and SPM 12 and choose later the one to use.
- A single pipeline may use various configurations of a software. For instance a pipeline could compare the results of SPM 8 and SPM 12.
- Settings definition must be modular. It must be possible to define possible settings values either in Capsul (for well known for instance) or in external modules that can be installed separately.
- Capsul must deal with module dependencies. For instance the settings of SPM may depends on the settings of Matlab. But this dependency exists only if a non standalone SPM version is used. Therefore, dependencies between modules may depends on settings values.
- CapsulEngine settings must provide the possibility to express a requirement on settings. For instance a process may require to have version of SPM greater or equal to 12.
- The configuration of a module can be defined for a specific execution environment. Settings must allow to deal with several executions environments (e.g. a local machine and a computing cluster). Each environment may have different configuration (for instance the SPM installation directory is not the same on local computer and on computing cluster).

To implement all these features, it was necessary to have a settings storage system providing a query language to express requirements such as `spm.version >= 12`. Populse_db was thus choosen as the storage and query system for settings. Some of the settings API choices had been influenced by populse_db API.

CapsulEngine settings are organized in modules. Each module defines and document the schema of values that can be set for its configuration. Typically, a module is dedicated to a software. For instance the module for SPM accepts confiurations containing a version (a string), an install directory (a string), a standalone/matlab flag (a boolean), etc. This schema is used to record configuration documents for the module. There can be several configuration document per module. Each document correspond to a full configuration of the module (for instance a document for SPM 8 configuration and another for SPM 12, or one for SPM 12 standalone and another for SPM 12 with matlab).

Settings cannot be used directly to configure the execution of a software. It is necessary to first select a single configuration document for each module. This configurations selection step is done by `select_configurations()` method.

'''
class Settings:
    '''
    Main class for the management of CapsulEngine settings. Since these settings are always stored in a populse_db database, it is necessary to activate a settings session in order to read or modify settings. This is done by using a with clause:
    
    ```
    from capsul.api import capsul_engine
    
    # Create a CapsulEngine
    ce = capsul_engine() 
    with ce.settings as settings:
        # Read or modify settings here
    ```
    '''
    
    global_environment = 'global'
    collection_prefix = 'settings/'
    environment_field = 'config_environment'
    config_id_field = 'config_id'
    
    def __init__(self, populse_db):
        '''
        Create a settins instance using the given populse_db instance
        '''
        self.populse_db = populse_db
        self._dbs = None
        
    def __enter__(self):
        '''
        Starts a session to read or write settings
        '''
        dbs = self.populse_db.__enter__()
        return SettingsSession(dbs)

    def __exit__(self, *args):
        self.populse_db.__exit__(*args)
        self._dbs = None
    
    @staticmethod
    def module_name(module_name):
        '''
        Return a complete module name (which must be a valid Python module
        name) given a possibly abbreviated module name. This method must
        be used whenever a module name is written by a user (for instance
        in a configuration file.
        This method add the prefix `'capsul.engine.module.'` if the module
        name does not contain a dot.
        '''
        if '.' not in module_name:
            module_name = 'capsul.engine.module.' + module_name
        return module_name
    
    def select_configurations(self, environment, uses=None):
        '''
        Select a configuration for a given environment. A configuration is
        a dictionary whose keys are module names and values are
        configuration documents. The returned set of configuration per module
        can be activaded with `capsul.api.activate_configurations()`.
        
        The `uses` parameter determine which modules
        must be included in the configuration. If not given, this method 
        considers all configurations for every module defined in settings.
        This parameter is a dictionary whose keys are a module name and
        values are populse_db queries used to select module.
        
        The enviroment parameter defines the execution environment in which
        the configurations will be used. For each module, configurations are
        filtered with the query. First, values are searched in the given
        environment and, if no result is found, the `'global'` enviroment
        (the value defined in `Settings.global_environment`) is used.
        
        example
        -------
        To select a SPM version greater than 8 for an environment called
        `'my_environment'` one could use the following code:
        ```
        config = ce.select_configurations('my_environment',
                                          uses={'spm': 'version > 8'})
        ```
        '''
        configurations = {}
        with self as settings:
            if uses is None:
                uses = {}
                for collection in (i.collection_name 
                                   for i in 
                                   settings._dbs.get_collections()):
                    if collection.startswith(Settings.collection_prefix):
                        module_name = \
                            collection[len(Settings.collection_prefix):]
                        uses[module_name] = 'ALL'
            uses_stack = list(uses.items())
            while uses_stack:
                module, query = uses_stack.pop(-1)
                module = self.module_name(module)
                if module in configurations:
                    continue
                configurations.setdefault('capsul_engine', 
                                          {}).setdefault('uses', 
                                                         {})[module] = query
                selected_config = None
                full_query = '%s == "%s" AND (%s)' % (
                    Settings.environment_field, environment, (
                        'ALL' if query == 'any' else query))
                collection = '%s%s' % (Settings.collection_prefix, module)
                if settings._dbs.get_collection(collection):
                    docs = list(settings._dbs.filter_documents(collection, 
                                                               full_query))
                else:
                    docs = []
                if len(docs) == 1:
                    selected_config = docs[0]
                elif len(docs) > 1:
                    if query == 'any':
                        selected_config = docs[0]
                    else:
                        raise EnvironmentError('Cannot create configurations '
                            'for environment "%s" because settings returned '
                            '%d instances for module %s' % (environment, 
                                                            len(docs), module))
                else:
                    full_query = '%s == "%s" AND (%s)' % (Settings.environment_field,
                                                          Settings.global_environment,
                                                          ('ALL' if query == 'any' 
                                                           else query))
                    if settings._dbs.get_collection(collection):
                        docs = list(settings._dbs.filter_documents(collection, 
                                                                   full_query))
                    else:
                        docs = []
                    if len(docs) == 1:
                        selected_config = docs[0]
                    elif len(docs) > 1:
                        if query == 'any':
                            selected_config = docs[0]
                        else:
                            raise EnvironmentError('Cannot create '
                                'configurations for environment "%s" because '
                                'global settings returned %d instances for '
                                'module %s' % (environment, len(docs),
                                               module))
                if selected_config:
                    # Remove values that are None
                    for k, v in list(selected_config.items()):
                        if v is None:
                            del selected_config[k]
                    configurations[module] = selected_config
                    python_module = importlib.import_module(module)
                    config_dependencies = getattr(python_module, 
                                                  'config_dependencies', 
                                                  None)
                    if config_dependencies:
                        d = config_dependencies(selected_config)
                        if d:
                            uses_stack.extend(list(d.items()))
        return configurations
    
    
class SettingsSession:
    def __init__(self, populse_session):
        '''
        SettingsSession are created with Settings.__enter__ using a `with`
        statement.
        '''
        self._dbs = populse_session

    @staticmethod
    def collection_name(module):
        '''
        Return the name of the populse_db collection corresponding to a
        settings module. The result is the full name of the module 
        prefixed by Settings.collection_prefix (i.e. `'settings/'`).
        '''
        module = Settings.module_name(module)
        collection = '%s%s' % (Settings.collection_prefix, module)
        return collection
    
    def ensure_module_fields(self, module, fields):
        '''
        Make sure that the given module exists in settings and create the given fields if they do not exist. `fields` is a list of dictionaries with three items:
        - name: the name of the key
        - type: the data type of the field (in populse_db format)
        - description: the documentation of the field
        '''
        collection = self.collection_name(module)
        if self._dbs.get_collection(collection) is None:
            self._dbs.add_collection(collection, Settings.config_id_field)
            self._dbs.add_field(collection, 
                                Settings.environment_field, 
                                'string', index=True)
        for field in fields:
            name = field['name']
            if self._dbs.get_field(collection, name) is None:
                self._dbs.add_field(collection, name=name,
                                    field_type=field['type'],
                                    description=field['description'])
        return collection
    
    def new_config(self, module, environment, values):
        '''
        Creates a new configuration document for a module in the given 
        environment. Values is a dictionary used to set values for the 
        document. The document mut have a unique string identifier in 
        the `Settings.config_id_field` (i.e. `'config_id'`), if None is
        given in `values` a unique random value is created (with 
        `uuid.uuid4()`).
        '''
        document = {
            Settings.environment_field: environment}
        document.update(values)
        id = document.get(Settings.config_id_field)
        if id is None:
            id = str(uuid4())
            document[Settings.config_id_field] = id
        collection = self.collection_name(module)
        self._dbs.add_document(collection, document)
        return SettingsConfig(self._dbs, collection, id)

    def configs(self, module, environment):
        '''
        Returns a generator that iterates over all configuration
        documents created for the given module and environment.
        '''
        collection = self.collection_name(module)
        if self._dbs.get_collection(collection) is not None:
            for d in self._dbs.find_documents(collection, 
                                              '%s=="%s"' % (
                                                  Settings.environment_field,
                                                  environment)):
                id = d[Settings.config_id_field]
                yield SettingsConfig(self._dbs, collection, id)


class SettingsConfig(object):
    def __init__(self, populse_session, collection, id):
        super(SettingsConfig, self).__setattr__('_dbs', populse_session)
        super(SettingsConfig, self).__setattr__('_collection', collection)
        super(SettingsConfig, self).__setattr__('_id', id)

    def __setattr__(self, name, value):
        self._dbs.set_value(self._collection, self._id, name, value)
    
    def __getattr__(self, name):
        return self._dbs.get_value(self._collection, self._id, name)
    
