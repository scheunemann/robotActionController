from threading import Thread
from TriggerInterface import TriggerInterface
from datetime import datetime, timedelta
from collections import namedtuple
import time
import event


__all__ = ['TriggerProcessor', ]

TriggerActivatedEventArg = namedtuple('TriggerActivatedEvent', ['trigger_id', 'value'])


class TriggerProcessor(object):

    triggerActivated = event.Event('Trigger activated event')

    def __init__(self, triggers, maxUpdateInterval=None):
        self._handlers = []
        for trigger in triggers:
            handler = _TriggerHandler(trigger, self.triggerActivated, maxUpdateInterval, timedelta(seconds=maxUpdateInterval.seconds / 10.0))
            self._handlers.append(handler)

    def start(self):
        map(lambda h: h.start(), self._handlers)

    def stop(self):
        map(lambda h: h.stop(), self._handlers)

    def __del__(self):
        self.stop()


class _TriggerHandler(Thread):

    def __init__(self, trigger, activatedEvent, maxUpdateInterval=None, maxPollRate=None):
        super(_TriggerHandler, self).__init__()
        self._triggerId = trigger.id
        self._triggerInt = TriggerInterface.getTriggerInterface(trigger)
        self._maxUpdateInterval = maxUpdateInterval
        self._maxPollRate = maxPollRate or timedelta(milliseconds=100)
        self._activatedEvent = activatedEvent
        self._cancel = False

    def stop(self):
        self._cancel = True
        if self.isAlive():
            self.join()

    def run(self):
        last_update = datetime.now()
        last_value = None
        while not self._cancel:
            value = self._triggerInt.getActive()
            if value != last_value and datetime.now() - last_update >= self._maxUpdateInterval:
                last_update = datetime.now()
                last_value = value
                # Fire the handlers in (yet another) thread to prevent long handlers from interrupting the loop
                Thread(target=self._activatedEvent, args=TriggerActivatedEventArg(self._triggerId, value)).start()

            sleepTime = max(self._maxUpdateInterval - (datetime.now() - last_update), self._maxPollRate).total_seconds()
            time.sleep(sleepTime)
