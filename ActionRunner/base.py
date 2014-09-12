import logging
import time
from collections import namedtuple
from datetime import datetime, timedelta
from threading import Thread
from multiprocessing.pool import ThreadPool


class ActionExecutionHandle(Thread):

    def __init__(self, action, runner=None):
        super(ActionExecutionHandle, self).__init__()
        self._logger = logging.getLogger(self.__class__.__name__)
        if not isinstance(action, tuple):
            raise Exception('Action must be a runnable type')
        self._action = action
        self._handles = []
        self._handle = None
        self._result = False
        self._output = []
        self._done = False
        self._callback = None
        self._callbackData = None
        self._runner = runner

    @property
    def action(self):
        return self._action

    @property
    def _safeHandles(self):
        return self._handles or [self._handle, ] if self._handle else []

    @property
    def result(self):
        return self._result if self._done else None

    @property
    def output(self):
        output = self._output
        output.extend([o for h in self._safeHandles for o in h.output])
        output.sort(key=lambda (ts, _): ts)
        return output

    def waitForComplete(self):
        # Wait for the sub-thread to start
        while not self._safeHandles and not self._done:
            time.sleep(0.01)

        results = map(lambda h: h.waitForComplete(), self._safeHandles)

        self._result = all(results)
        return self._result

    def start(self, callback=None, callbackData=None):
        self._done = False
        self._callback = callback
        self._callbackData = callbackData
        super(ActionExecutionHandle, self).start()

    def _runInternal(self, action):
        if self._runner:
            return self._runner.execute(action)
        else:
            return False

    def run(self):
        self._output.append((datetime.utcnow(), '%s: Starting %s' % (self.__class__.__name__, self._action.name)))

        starttime = datetime.utcnow()
        try:
            self._result = self._runInternal(self._action)
        except Exception as e:
            self._logger.critical("Error running action: %s" % self._action.name, exc_info=True)
            self._logger.critical("%s: %s" % (e.__class__.__name__, e))
            self._result = False
        else:
            endtime = datetime.utcnow()
            if self._action.minLength and timedelta(seconds=self._action.minLength) > (starttime - endtime):
                sleeptime = (starttime - endtime).total_seconds()
                self._logger.info("%s: Sleeping for %s seconds" % self.__class__.__name__, sleeptime)
                time.sleep(sleeptime)

            if self._result:
                self._output.append((datetime.utcnow(), '%s: Completed %s' % (self.__class__.__name__, self._action.name)))
            else:
                self._output.append((datetime.utcnow(), '%s: Failed %s' % (self.__class__.__name__, self._action.name)))
        finally:
            self._done = True

        if self._callback:
            try:
                args = self._callbackData or ()
                if not isinstance(args, (list, tuple)):
                    args = (args,)
                self._callback(self, *args)
            except Exception as e:
                self._logger.error("Error calling callback function: %s" % e, exc_info=True)

    def stop(self):
        handles = [h for h in self._safeHandles if h.isAlive()]
        if handles:
            pool = ThreadPool(processes=len(handles))
            pool.map(lambda h: h.stop(), handles)


class ActionRunner(object):

    # Increase memory usage but hopefully reduce CPU usage...
    # TODO: When to expire cached items?
    _actionCache = {}
    _runnerClasses = None
    supportedClass = 'Action'
    Runable = namedtuple('Action', ('name', 'id', 'type', 'minLength'))

    def __init__(self, robot):
        self._logger = logging.getLogger(self.__class__.__name__)
        self._robot = robot

    @property
    def robot(self):
        return self._robot

    def isValid(self, action):
        return self._getRunner(action).isValid(action)

    @staticmethod
    def getRunable(action):
        """
            Convert a DAO action into a minimised cacheable action for running
        """
        logger = logging.getLogger(ActionRunner.__name__)
        if action.id not in ActionRunner._actionCache:
            runners = ActionRunner._getRunners()
            if action.type in runners:
                return runners[action.type].getRunable(action)
                #ActionRunner._actionCache[action.id] = runners[action.type].getRunable(action)
                pass
            elif action.type == 'Action':
                logger.warn("Action: %s has an undefined action type: %s" % (action.name, action.type))
                return ActionRunner.Runable(action.name, action.id, action.type, action.minLength)
            else:
                logger.error("Action: %s has an unknown action type: %s" % (action.name, action.type))
                return None
        else:
            logger.debug("Using cached action: %s" % action.name)

        return ActionRunner._actionCache[action.id]

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

    def _getHandle(self, action):
        try:
            return ActionExecutionHandle(action, ActionRunner._getRunners()[action.type](self._robot))
        except Exception:
            self._logger.critical("Could not determine action runner for type %s" % action.type, exc_info=True)
            raise ValueError("Could not determine action runner for type %s" % action.type)

    def _getRunner(self, action):
        try:
            self._logger.debug("Building runnable action for %s (%s)" % (action.name, action.type))
            return ActionRunner._getRunners()[action.type](self._robot)
        except Exception:
            self._logger.critical("Could not determine action runner for type %s" % action.type, exc_info=True)
            raise ValueError("Could not determine action runner for type %s" % action.type)

    def execute(self, action):
        runner = self._getRunner(action)
        handle = runner._getHandle(action)
        handle.run()
        return handle.result

    def executeAsync(self, action, callback=None, callbackData=None):
        runner = self._getRunner(action)
        handle = runner._getHandle(action)
        handle.start(callback, callbackData)
        return handle
