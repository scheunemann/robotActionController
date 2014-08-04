import logging
from collections import namedtuple
from threading import RLock

__all__ = ['TriggerInterface', ]


class TriggerInterface(object):
    supportedClass = 'Trigger'
    Runable = namedtuple('Trigger', ('name', 'id', 'type'))
    _interfaceClasses = None
    _servoInterfaces = {}
    _globalLock = RLock()
    _interfaces = {}
    disconnected = False

    """have to do it this way to get around circular referencing in the parser"""
    @staticmethod
    def _getInterfaceClasses():
        if TriggerInterface._interfaceClasses == None:
            from time import TimeTrigger
            from button import ButtonTrigger
            from sensor import SensorTrigger
            TriggerInterface._interfaceClasses = {
                                 'TimeTrigger': TimeTrigger,
                                 'ButtonTrigger': ButtonTrigger,
                                 'SensorTrigger': SensorTrigger,
                                 }

        return TriggerInterface._interfaceClasses

    @staticmethod
    def getTriggerInterface(trigger, robot=None):
        with TriggerInterface._globalLock:
            if trigger.id not in TriggerInterface._interfaces:
                if not issubclass(trigger.__class__, TriggerInterface.Runable):
                    trigger = TriggerInterface.getRunable(trigger)

                try:
                    triggerIntClass = TriggerInterface._getInterfaceClasses()[trigger.type]
                except:
                    logging.getLogger(__name__).critical("No known interface for trigger type: %s", trigger.type)
                    raise ValueError("No known interface for trigger type: %s" % trigger.type)
                else:
                    triggerInt = triggerIntClass(trigger=trigger, robot=robot)

                TriggerInterface._interfaces[trigger.id] = triggerInt

            return TriggerInterface._interfaces[trigger.id]

    @staticmethod
    def getRunable(trigger):
        """
            Convert a DAO trigger into a minimised cacheable trigger for running
        """
        logger = logging.getLogger(TriggerInterface.__name__)
        interfaceClasses = TriggerInterface._getInterfaceClasses()
        if trigger.type in interfaceClasses:
            return interfaceClasses[trigger.type].getRunable(trigger)
        elif trigger.type == 'Trigger':
            logger.warn("Trigger: %s has an undefined trigger type: %s" % (trigger.name, trigger.type))
            return TriggerInterface.Runable(trigger.name, trigger.id, trigger.type)
        else:
            logger.error("Trigger: %s has an unknown trigger type: %s" % (trigger.name, trigger.type))
            return None

    def __init__(self, trigger, **kwargs):
        self._trigger = trigger
        self._logger = logging.getLogger(self.__class__.__name__)

    def getActive(self):
        return False
