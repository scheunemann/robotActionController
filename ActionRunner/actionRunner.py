from base import Runner

class ActionRunner(Runner):
    
    class ActionExecutionHandle(Runner.ExecutionHandle):
        
        def __init__(self, action, runner):
            super(ActionRunner.ActionExecutionHandle, self).__init__(action)
            self._runner = runner
        
        def run(self):
            self._handle = self._runner.executeAsync(self._action)
            return self.waitForComplete()
    
    _runnerClasses = None
    
    def __init__(self, robot):
        super(ActionRunner, self).__init__(robot)

    def isValid(self, action):
        return self._getRunner(action).isValid(action)
    
    def _getHandle(self, action):
        try:
            return ActionRunner.ActionExecutionHandle(action, ActionRunner._getRunners()[type(action)](self._robot))
        except:
            self._logger.critical("Could not determine action runner for type %s" % (type(action)))
            raise ValueError("Could not determine action runner for type %s" % (type(action)))
    
    @staticmethod
    def _getRunners():
        if ActionRunner._runnerClasses == None:
            ActionRunner._runnerClasses = ActionRunner.loadModules(ofType=Runner)
        
        return ActionRunner._runnerClasses

    @staticmethod
    def registerRunner(type_, runner):
        ActionRunner._runners[type_] = runner
        
    @staticmethod
    def loadModules(path=None, ofType=None):
        """loads all modules from the specified path or the location of this file if none"""
        """returns a dictionary of loaded modules {name: type}"""
        import os, re, sys, inspect
    
        if path == None:
            path = os.path.dirname(__file__)

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
                for _, type_ in inspect.getmembers(module, inspect.isclass):
                    if issubclass(type_, ofType) and not type_ == ofType:
                        ret[type_.supportedClass] = type_

            except Exception as e:
                print >> sys.stderr, "Unable to import module %s, Exception: %s" % (module, e)

        return ret