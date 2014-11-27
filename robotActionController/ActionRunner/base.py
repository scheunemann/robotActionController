import logging
import abc
from collections import namedtuple
from datetime import datetime
import gevent
from gevent.lock import RLock


class ActionRunner(gevent.greenlet.Greenlet):
    __metaclass__ = abc.ABCMeta

    Runable = namedtuple('Action', ('name', 'id', 'type'))

    def __init__(self, action, runner=None):
        super(ActionRunner, self).__init__()
        self._logger = logging.getLogger(self.__class__.__name__)
        if not isinstance(action, tuple):
            raise Exception('Action must be a runnable type')
        self._action = action
        self._output = []

    @property
    def action(self):
        return self._action

    @property
    def result(self):
        return self.value if self.dead else None

    @property
    def output(self):
        try:
            return sorted(self._output, key=lambda (ts, _): ts)
        except:
            return sorted(self._output)

    @abc.abstractmethod
    def _runInternal(self, action):
        pass

    @abc.abstractmethod
    def isValid(self, action):
        pass

    @staticmethod
    def getRunable(action):
        """
            Convert a DAO action into a minimised cacheable action for running
        """
        if action == None:
            return None

        logger = logging.getLogger(ActionRunner.__name__)
        runners = ActionManager._getRunners()
        actionType = action.get('type', None) if type(action) == dict else action.type
        actionName = action.get('name', None) if type(action) == dict else action.name
        if actionType in runners:
            return runners[actionType].getRunable(action)
        elif actionType == 'Action':
            logger.warn("Action: %s is abstract!" % (actionName, actionType))
            return None
        else:
            logger.error("Action: %s has an unknown action type: %s" % (actionName, actionType))
            return None

    def execute(self):
        self.start()
        self.waitForComplete()
        return self.value

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
        self.join()

    def _run(self):
        self._output.append((datetime.utcnow(), '%s: Starting %s' % (self.__class__.__name__, self._action.name)))
        self._logger.debug('%s: Starting %s' % (self.__class__.__name__, self._action.name))

        result = True
        try:
            self._result = self._runInternal(self._action)
        except Exception as e:
            self._logger.critical("Error running action: %s" % self._action.name, exc_info=True)
            self._logger.critical("%s: %s" % (e.__class__.__name__, e))
            result = False
        except gevent.GreenletExit:
            endtime = datetime.utcnow()
            self._output.append((endtime, '%s: Cancelled %s' % (self.__class__.__name__, self._action.name)))
            self._logger.debug('%s: Cancelled %s' % (self.__class__.__name__, self._action.name))
            raise
        else:
            endtime = datetime.utcnow()
            if result:
                self._output.append((endtime, '%s: Completed %s' % (self.__class__.__name__, self._action.name)))
                self._logger.debug('%s: Completed %s' % (self.__class__.__name__, self._action.name))
            else:
                self._output.append((endtime, '%s: Failed %s' % (self.__class__.__name__, self._action.name)))
                self._logger.debug('%s: Failed %s' % (self.__class__.__name__, self._action.name))

        return result

    def stop(self):
        gevent.kill(self)
        self.waitForComplete()


class ActionManager(object):

    # Increase memory usage but hopefully reduce CPU usage...
    # TODO: When to expire cached items?
    _runnerClasses = None
    __managers = {}

    def __init__(self, robot):
        self._logger = logging.getLogger(self.__class__.__name__)
        self._robot = robot
        self.__actionCache = {}
        self.__cacheLock = RLock()
        ActionManager._getRunners()

    @property
    def robot(self):
        return self._robot

    @staticmethod
    def getManager(robot):
        if not robot.id in ActionManager.__managers:
            ActionManager.__managers[robot.id] = ActionManager(robot)
        return ActionManager.__managers[robot.id]

    @staticmethod
    def _getRunners():
        if ActionManager._runnerClasses == None:
            ActionManager._runnerClasses = ActionManager.loadModules(ofType=ActionRunner)

        return ActionManager._runnerClasses

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
        logger = logging.getLogger(ActionManager.__name__)
        for moduleName in toLoad:
            try:
                module = __import__(moduleName, globals(), locals())
                for _, type_ in inspect.getmembers(module, inspect.isclass):
                    if issubclass(type_, ofType) and not type_ == ofType:
                        ret[type_.supportedClass] = type_
                        logger.debug("Registering runner for type %s" % type_.supportedClass)

            except Exception as e:
                logger.critical("Unable to import module %s, Exception: %s" % (module, e))

        return ret

    def cacheActions(self, actions):
        for action in actions:
            self.getRunable(action)

    def clearCache(self):
        with self.__cacheLock:
            self.__actionCache.clear()

    def getCachedActionByName(self, actionName):
        with self.__cacheLock:
            actions = filter(lambda x: x.name==actionName, self.__actionCache.itervalues())
        return actions[0] if actions else None

    def getCachedActionById(self, actionId):
        with self.__cacheLock:
            return self.__actionCache.get(actionId, None)

    def executeAction(self, action):
        if type(action) == str:
            aName = action
            action = self.getCachedActionByName(aName)
        
        if type(action) == int:
            aId = action
            action = self.getCachedActionById(aId)

        if not action:
            self._logger.warning("Got NULL action to start")
            return False
        
        self._logger.debug("Starting %s Sync" % action.name)
        runner = self.__getRunner(action)
        return runner.execute()

    def executeActionAsync(self, action, callback=None, callbackData=None):
        if type(action) == str:
            aName = action
            action = self.getCachedActionByName(aName)
        
        if type(action) == int:
            aId = action
            action = self.getCachedActionById(aId)

        if not action:
            self._logger.warning("Got NULL action to start")
            return None

        self._logger.debug("Starting %s Async" % action.name)
        runner = self.__getRunner(action)
        runner.executeAsync(callback, callbackData)
        return runner

    def getRunable(self, action):
        """
            Convert a DAO action into a minimised cacheable action for running
        """
        with self.__cacheLock:
            if action.id not in self.__actionCache:
                runable = ActionRunner.getRunable(action)
                if runable:
                    self.__actionCache[action.id] = runable
                else:
                    return None
            else:
                self._logger.debug("Using cached action: %s" % action.name)

            return self.__actionCache[action.id]

    def __getRunner(self, action):
        try:
            self._logger.debug("Getting action runner for %s (%s)" % (action.name, action.type))
            return ActionManager._getRunners()[action.type](action, self._robot)
        except Exception:
            self._logger.critical("Could not determine action runner for type %s" % action.type, exc_info=True)
            raise ValueError("Could not determine action runner for type %s" % action.type)

