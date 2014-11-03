import logging
import abc
from collections import namedtuple
from datetime import datetime, timedelta
import gevent
from gevent.lock import RLock


class ActionRunner(gevent.greenlet.Greenlet):
    __metaclass__ = abc.ABCMeta

    def __init__(self, action, runner=None):
        super(ActionRunner, self).__init__()
        self._logger = logging.getLogger(self.__class__.__name__)
        if not isinstance(action, tuple):
            raise Exception('Action must be a runnable type')
        self._action = action
        self._handles = []
        self._handle = None
        self._output = []
        self._runner = runner

    @property
    def action(self):
        return self._action

    @property
    def result(self):
        return self.value

    @property
    def output(self):
        output = self._output
        output.extend([o for h in self._safeHandles for o in h.output])
        output.sort(key=lambda (ts, _): ts)
        return output

    @property
    def _safeHandles(self):
        return self._handles or [self._handle, ] if self._handle else []
    
    @abc.abstractmethod
    def _runInternal(self, action):
        pass
    
    @abc.abstractmethod
    def isValid(self, action):
        pass
    
    @abc.abstractmethod
    def getRunable(self, action):
        pass
    
    def execute(self):
        return self._run()
    
    def executeAsync(self, callback=None, callbackData=None):
        if callback:
            args = callbackData or ()
            if not isinstance(args, (list, tuple)):
                args = (args,)
            cb = lambda x: callback(x, *args)
            self.link(cb)
        self.start()
        return self

    def waitForComplete(self):
        gevent.joinall(self._safeHandles)

    def _run(self):
        self._output.append((datetime.utcnow(), '%s: Starting %s' % (self.__class__.__name__, self._action.name)))

        result = True
        starttime = datetime.utcnow()
        try:
            self._result = self._runInternal(self._action)
        except Exception as e:
            self._logger.critical("Error running action: %s" % self._action.name, exc_info=True)
            self._logger.critical("%s: %s" % (e.__class__.__name__, e))
            result = False
        else:
            endtime = datetime.utcnow()
            if self._action.minLength and timedelta(seconds=self._action.minLength) > (starttime - endtime):
                sleeptime = (starttime - endtime).total_seconds()
                self._logger.info("%s: Sleeping for %s seconds" % self.__class__.__name__, sleeptime)
                gevent.sleep(sleeptime)

            if result:
                self._output.append((datetime.utcnow(), '%s: Completed %s' % (self.__class__.__name__, self._action.name)))
            else:
                self._output.append((datetime.utcnow(), '%s: Failed %s' % (self.__class__.__name__, self._action.name)))

        return result

    def stop(self):
        gevent.killall(self._safeHandles)
        self.waitForComplete()


class ActionManager(object):    

    # Increase memory usage but hopefully reduce CPU usage...
    # TODO: When to expire cached items?
    _runnerClasses = None

    def __init__(self, robot):
        self._logger = logging.getLogger(self.__class__.__name__)
        self._robot = robot
        self.__actionCache = {}
        self.__cacheLock = RLock()
        ActionManager._getRunners()

    @property
    def robot(self):
        return self._robot

    def clearCache(self):
        with self.__cacheLock:
            self.__actionCache.clear()
            
    def cacheActions(self, actions):
        for action in actions:
            self.getRunable(action)

    def getRunable(self, action):
        """
            Convert a DAO action into a minimised cacheable action for running
        """
        if action == None:
            return None
        
        with self.__cacheLock:
            if action.id not in self.__actionCache:
                runners = ActionManager._getRunners()
                if action.type in runners:
                    runable = runners[action.type].getRunable(action)
                    self.__actionCache[action.id] = runable
                elif action.type == 'Action':
                    self._logger.warn("Action: %s is abstract!" % (action.name, action.type))
                    return None
                else:
                    self._logger.error("Action: %s has an unknown action type: %s" % (action.name, action.type))
                    return None
            else:
                self._logger.debug("Using cached action: %s" % action.name)

        return self.__actionCache[action.id]

    @staticmethod
    def _getRunners():
        if ActionRunner._runnerClasses == None:
            ActionRunner._runnerClasses = ActionRunner.loadModules(ofType=ActionRunner)

        return ActionRunner._runnerClasses

    @staticmethod
    def loadModules(path=None, ofType=None):
        """loads all modules from the specified path or the location of this file if none"""
        """returns a dictionary of loaded modules {name: type}"""
        import os
        import re
        import sys
        import inspect

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
                logger = logging.getLogger(ActionRunner.__name__)
                logger.critical("Unable to import module %s, Exception: %s" % (module, e))

        return ret

    def __getRunner(self, action):
        try:
            self._logger.debug("Getting action runner for %s (%s)" % (action.name, action.type))
            return ActionRunner._getRunners()[action.type](self._robot)
        except Exception:
            self._logger.critical("Could not determine action runner for type %s" % action.type, exc_info=True)
            raise ValueError("Could not determine action runner for type %s" % action.type)
        
    def executeAction(self, action):
        self._logger.debug("Starting %s Sync" % action.name)
        runner = self.__getRunner(action)
        return runner.execute()

    def executeActionAsync(self, action, callback=None, callbackData=None):
        self._logger.debug("Starting %s Async" % action.name)
        runner = self.__getRunner(action)
        runner.executeAsync(callback, callbackData)
        return runner
