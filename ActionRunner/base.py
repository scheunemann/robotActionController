import logging
import time
from threading import Thread
from multiprocessing.pool import ThreadPool
from Data.Model import Action

class Runner(object):

    class ExecutionHandle(Thread):

        def __init__(self, action):
            super(Runner.ExecutionHandle, self).__init__()
            self._action = action
            self._handles = []
            self._handle = None
            self._result = False

        @property
        def result(self):
            return self._result

        def waitForComplete(self):
            handles = self._handles or [self._handle, ] if self._handle else []
            while any([h.isAlive() for h in handles]):
                time.sleep(0.01)

            self._result = all([h.result for h in handles])

        def stop(self):
            handles = self._handles or [self._handle, ] if self._handle else []
            handles = [h for h in handles if h.isAlive()]
            pool = ThreadPool(processes=len(handles))
            pool.map(lambda h: h.stop(), handles)

    supportedClass = Action

    def __init__(self, robot):
        self._robot = robot;
        self._logger = logging.getLogger(__name__)

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
        return handle
