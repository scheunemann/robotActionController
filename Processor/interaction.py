from threading import RLock, Thread
from ActionRunner import ActionRunner
from trigger import TriggerProcessor
from Data.storage import StorageFactory


class InteractionProcessor(Thread):

    def __init__(self, robot, user):
        self._robot = robot.id
        self._user = user.id
        self._run = False

    def __del__(self):
        if self._ds:
            self._ds.close()

    def start(self):
        self._run = True
        ds = StorageFactory.getNewSession()
        robot = ds.merge(self._robot, False)
        user = ds.merge(self._user, False)
        triggerProcessor = TriggerProcessor(robot)
        triggers = triggerProcessor.getTriggers(user)
        actionRunner = ActionRunner(robot)
        while(self._run):
            for trigger in triggers:
                if not self._run:
                    break

                if triggerProcessor.isActive(trigger):
                    actionRunner.execute(trigger.action, user)
