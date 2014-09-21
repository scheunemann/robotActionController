from threading import Thread
from TriggerInterface import TriggerInterface
from ActionRunner import ActionRunner
from datetime import datetime, timedelta
from collections import namedtuple
import time
import event
import logging


__all__ = ['TriggerProcessor', ]

TriggerActivatedEventArg = namedtuple('TriggerActivatedEvent', ['trigger_id', 'value', 'action'])


class TriggerProcessor(object):
    triggerActivated = event.Event('Trigger activated event')

    def __init__(self, triggers, robot, maxUpdateInterval=None):
        self._logger = logging.getLogger(self.__class__.__name__)
        self._handlers = []
        for trigger in triggers:
            try:
                handler = _TriggerHandler(trigger, self.triggerActivated, robot, maxUpdateInterval, timedelta(seconds=maxUpdateInterval.seconds / 10.0))
                self._handlers.append(handler)
            except Exception:
                self._logger.warning("Error handling trigger! %s" % trigger, exc_info=True)
                continue

    def start(self):
        map(lambda h: h.start(), self._handlers)

    def stop(self):
        map(lambda h: h.stop(), self._handlers)

    def __del__(self):
        self.stop()


class _TriggerHandler(Thread):

    def __init__(self, trigger, activatedEvent, robot, maxUpdateInterval=None, maxPollRate=None):
        super(_TriggerHandler, self).__init__()
        self._triggerId = trigger.id
        self._triggerInt = TriggerInterface.getTriggerInterface(trigger, robot)
        self._action = ActionRunner.getRunable(trigger.action)
        self._maxUpdateInterval = maxUpdateInterval
        self._maxPollRate = maxPollRate or timedelta(milliseconds=100)
        self._activatedEvent = activatedEvent
        self._cancel = False

    def start(self):
        super(_TriggerHandler, self).start()

    def stop(self):
        self._cancel = True
        if self.isAlive():
            self.join()

    def run(self, *args, **kwargs):
        last_update = datetime.utcnow()
        last_value = False
        while not self._cancel:
            value = self._triggerInt.getActive()
            if value != last_value and datetime.utcnow() - last_update >= self._maxUpdateInterval:
                last_update = datetime.utcnow()
                last_value = value
                # Fire the handlers in thread to prevent long handlers from interrupting the loop
                #Thread(target=self._activatedEvent, args=(TriggerActivatedEventArg(self._trigger, value), )).start()
                self._activatedEvent(TriggerActivatedEventArg(self._triggerId, value, self._action))

            sleepTime = max(self._maxUpdateInterval - (datetime.utcnow() - last_update), self._maxPollRate).total_seconds()
            time.sleep(sleepTime)
