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
            self._handles = []
            self._handle = None
            self._result = False
            self._output = []

        @property
        def _safeHandles(self):
            return self._handles or [self._handle, ] if self._handle else []

        @property
        def result(self):
            return self._result

        @property
        def output(self):
            output = self._output
            output.extend([o for h in self._safeHandles for o in h.output])
            output.sort(key=lambda (ts, _): ts)
            return output

        def waitForComplete(self):
            # Wait for the sub-thread to start
            while not self._safeHandles:
                time.sleep(0.01)

            results = map(lambda h: h.waitForComplete(), self._safeHandles)

            self._result = all(results)
            return self._result

        def runInternal(self, action):
            return False

        def run(self):
            session = StorageFactory.getNewSession()
#             action = session.query(Action).get(self._actionId)
#             action = self._action
            action = session.merge(self._action, load=False)
            self._output.append((datetime.now(), '%s: Starting %s' % (self.__class__.__name__, action.name)))

            starttime = datetime.now()
            try:
                self._result = self._runInternal(action, session)
            except:
                self._logger.critical("Error running action: %s" % action)
                import traceback
                self._logger.critical(traceback.format_exc())
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
                session.close()

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

    def executeAsync(self, action):
        handle = self._getHandle(action)
        handle.start()
        time.sleep(0.01)
        return handle
