from multiprocessing import RLock


class Arbiter(object):
#TODO:

    _instances = {}

    @staticmethod
    def getArbiterFor(robot):
        try:
            return Arbiter._instances[robot]
        except:
            Arbiter._instances[robot] = Arbiter(robot)
            return Arbiter._instances[robot]

    def __init__(self, robot):
        self._robot = robot
        self._requestedActions = {}
        self._runningActions = []
        self._updateLock = RLock()

    def addAction(self, action, priority, callback=None):
        pass

    def cancelAction(self, action):
        pass
