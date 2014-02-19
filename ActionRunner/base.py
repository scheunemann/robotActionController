import logging
import time
from datetime import datetime, timedelta
from threading import Thread
from multiprocessing.pool import ThreadPool
from Data.Model import Action
from Data.storage import StorageFactory


class Runner(object):

    class ExecutionHandle(Thread):

        def __init__(self, action):
            super(Runner.ExecutionHandle, self).__init__()
            self._logger = logging.getLogger(self.__class__.__name__)
            self._action = action
            self._actionId = action.id
            self._handles = []
            self._handle = None
            self._result = False
            self._output = []
            self._done = False

        @property
        def actionId(self):
            return self._actionId

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
            Thread().start()
            # Wait for the sub-thread to start
            while not self._safeHandles and not self._done:
                time.sleep(0.01)

            results = map(lambda h: h.waitForComplete(), self._safeHandles)

            self._result = all(results)
            return self._result

        def runInternal(self, action):
            return False

        def start(self, callback=None):
            self._done = False
            self._callback = callback
            super(Runner.ExecutionHandle, self).start()

        def run(self):
            session = StorageFactory.getNewSession()
            action = session.merge(self._action, load=False)
            self._output.append((datetime.now(), '%s: Starting %s' % (self.__class__.__name__, action.name)))

            starttime = datetime.now()
            try:
                self._result = self._runInternal(action, session)
            except Exception as e:
                self._logger.critical("Error running action: %s" % action)
                self._logger.critical("%s: %s" % (e.__class__.__name__, e))
                import traceback
                self._logger.debug(traceback.format_exc())
                self._result = False
            else:
                endtime = datetime.now()
                if action.minLength and timedelta(seconds=action.minLength) > (starttime - endtime):
                    sleeptime = (starttime - endtime).total_seconds()
                    self._logger.info("%s: Sleeping for %s seconds" % self.__class__.__name__, sleeptime)
                    time.sleep(sleeptime)

                if self._result:
                    self._output.append((datetime.now(), '%s: Completed %s' % (self.__class__.__name__, action.name)))
                else:
                    self._output.append((datetime.now(), '%s: Failed %s' % (self.__class__.__name__, action.name)))
            finally:
                self._done = True
                session.close()
            
            if self._callback:
                self._callback(self)

        def stop(self):
            handles = [h for h in self._safeHandles if h.isAlive()]
            if handles:
                pool = ThreadPool(processes=len(handles))
                pool.map(lambda h: h.stop(), handles)

    supportedClass = Action

    def __init__(self, robot):
        self._robot = robot
        self._logger = logging.getLogger(self.__class__.__name__)

    @staticmethod
    def isValid(action):
        return action != None

    def _getHandle(self, action):
        return Runner.ExecutionHandle(action)

    def execute(self, action):
        handle = self._getHandle(action)
        handle.start()
        handle.waitForComplete()
        return handle.result

    def executeAsync(self, action, callback=None):
        handle = self._getHandle(action)
        handle.start(callback)
        time.sleep(0.01)
        return handle
