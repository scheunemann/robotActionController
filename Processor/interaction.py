import multiprocessing
from Robot.runners import ActionRunner
from trigger import TriggerProcessor
from Data.Storage import StorageFactory

class InteractionProcessor(object):
    
    def __init__(self, robot, user):
        self._robot = robot
        self._user = user
        self._run = False
        self._ds = StorageFactory.getNewSession()
        self._thread = multiprocessing.Process(target=self.process)
    
    def start(self):
        self._run = True
        self._thread.start()

    def process(self):
        triggerProcessor = TriggerProcessor(self._robot)
        actionRunner = ActionRunner(self._robot)
        while(self._run):
            for trigger in triggerProcessor.getTriggers(self._user):
                if not self._run:
                    break
                
                if triggerProcessor.isActive(trigger):
                    actionRunner.execute(trigger.action, self._user)

    def stop(self):
        self._run = False
        self._thread.join()
