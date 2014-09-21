from triggerInterface import TriggerInterface
from collections import namedtuple
import logging


class CompoundTrigger(TriggerInterface):
    supportedClass = 'CompoundTrigger'
    Runable = namedtuple('CompoundTrigger', TriggerInterface.Runable._fields + ('requireAll', 'triggers', ))

    def __init__(self, trigger, robot, **kwargs):
        super(CompoundTrigger, self).__init__(trigger, **kwargs)
        self._logger = logging.getLogger(self.__class__.__name__)
        self._interfaces = [TriggerInterface.getTriggerInterface(t, robot) for t in trigger.triggers]
        self._requireAll = trigger.requireAll

    @staticmethod
    def getRunable(trigger):
        if trigger.type == CompoundTrigger.supportedClass:
            triggers = [TriggerInterface.getRunable(t) for t in trigger.triggers]
            return CompoundTrigger.Runable(trigger.name, trigger.id, trigger.type, trigger.requireAll, triggers)
        else:
            logger = logging.getLogger(CompoundTrigger.__name__)
            logger.error("Trigger: %s has an unknown trigger type: %s" % (trigger.name, trigger.type))
            return None

    def getActive(self):
        if self._requireAll:
            return all([i.getActive() for i in self._interfaces])
        else:
            return any([i.getActive() for i in self._interfaces])
