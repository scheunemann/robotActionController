from base import Runner

class ActionRunner(Runner):
    
    _runnerClasses = None
    
    @property
    @staticmethod
    def _runners():
        if ActionRunner._runnerClasses == None:
            ActionRunner._runnerClasses = ActionRunner.loadModules(ofType=Runner)
        
        return ActionRunner._runnerClasses

    def __init__(self, robot):
        super(ActionRunner, self).__init__(robot)

    def execute(self, action):
        self._getRunner(action).execute(action)

    def isValid(self, action):
        return self._getRunner(action).isValid(action)
    
    def _getRunner(self, action):
        try:
            return ActionRunner._runners[type(action)](self._robot)
        except:
            self._logger.critical("Could not determine action runner for type %s" % (type(action)))
            raise ValueError("Could not determine action runner for type %s" % (type(action)))
    
    @staticmethod
    def registerRunner(type_, runner):
        ActionRunner._runners[type_] = runner
        
    @staticmethod
    def loadModules(path=None, ofType=None):
        """loads all modules from the specified path or the location of this file if none"""
        """returns a dictionary of loaded modules {name: type}"""
        import os, re, sys, inspect
    
        if path == None:
            path = __file__

        path = os.path.realpath(path)
        modules = []
            
        find = re.compile(".*\.py$", re.IGNORECASE)
        if os.path.isdir(path):
            toLoad = map(lambda f: os.path.splitext(f)[0], filter(find.search, os.listdir(path)))
        else:
            toLoad = [os.path.splitext(os.path.basename(path))[0]]
        sys.path.append(os.path.dirname(path))        
        
        ret = {}
        for moduleName in toLoad:
            try:
                module = __import__(moduleName, globals(), locals())
                predicate = lambda t: True if type_ != None else lambda t: issubclass(t, ofType) and not t == ofType
                for _, type_ in inspect.getmembers(module, inspect.isclass, predicate=predicate):
                    ret[type_.supportedClass] = type_

            except Exception as e:
                print >> sys.stderr, "Unable to import module %s, Exception: %s" % (module, e)

        return ret