import logging
from threading import RLock

__all__ = ['TriggerInterface', ]


class TriggerInterface(object):
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
    def getTriggerInterface(trigger, robot):
        with TriggerInterface._globalLock:
            if trigger not in TriggerInterface._interfaces:
                try:
                    triggerInt = TriggerInterface._getInterfaceClasses()[trigger.type]
                except:
                    logging.getLogger(__name__).critical("No known interface for trigger type: %s", trigger.type)
                    raise ValueError("No known interface for trigger type: %s" % trigger.type)
                else:
                    triggerInt = triggerInt(trigger=trigger, robot=robot)

                TriggerInterface._interfaces[trigger] = triggerInt

            return TriggerInterface._interfaces[trigger]

    def __init__(self, trigger, **kwargs):
        self._trigger = trigger
        self._logger = logging.getLogger(self.__class__.__name__)

    def getActive(self):
        return False
