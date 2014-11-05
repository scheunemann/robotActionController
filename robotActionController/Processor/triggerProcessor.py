from TriggerInterface import TriggerInterface
from robotActionController.ActionRunner import ActionManager
from robotActionController.Processor.event import Event
from datetime import datetime, timedelta
from collections import namedtuple
import logging
from gevent.greenlet import Greenlet
from gevent import sleep


__all__ = ['TriggerProcessor', ]

TriggerActivatedEventArg = namedtuple('TriggerActivatedEvent', ['trigger_id', 'value', 'action', 'type'])


class TriggerProcessor(object):
    triggerActivated = Event('Trigger activated event')

    def __init__(self, triggers, robot, maxUpdateInterval=None):
        self._logger = logging.getLogger(self.__class__.__name__)
        self._handlers = []
        self._robot = robot
        self._maxUpdateInterval = maxUpdateInterval
        self._running = False

        if len(triggers):
            self.setTriggers(triggers)

    def start(self):
        self._running = True
        self._logger.info("Starting trigger handlers")
        map(lambda h: h.start(), self._handlers)

    def stop(self):
        self._running = False
        self._logger.info("Stopping trigger handlers")
        map(lambda h: h.kill(), self._handlers)

    def setTriggers(self, triggers):
        running = self._running
        if running:
            self.stop()
        
        self._handlers = []
        for trigger in triggers:
            try:
                handler = _TriggerHandler(trigger, self.triggerActivated, self._robot, self._maxUpdateInterval, timedelta(seconds=self._maxUpdateInterval.seconds / 10.0))
                self._handlers.append(handler)
            except Exception:
                self._logger.warning("Error handling trigger! %s" % trigger, exc_info=True)
                continue
        
        self._logger.debug("Handlers: %s" % self._handlers)
        if running:
            self.start()

    def __del__(self):
        self.stop()


class _TriggerHandler(Greenlet):

    def __init__(self, trigger, activatedEvent, robot, maxUpdateInterval=None, maxPollRate=None):
        super(_TriggerHandler, self).__init__()
        self._logger = logging.getLogger(self.__class__.__name__)
        self._triggerId = trigger.id
        self._triggerInt = TriggerInterface.getTriggerInterface(trigger, robot)
        self._action = ActionManager.getManager(robot).getRunable(trigger.action)
        self._maxUpdateInterval = maxUpdateInterval
        self._maxPollRate = maxPollRate or timedelta(milliseconds=100)
        self._activatedEvent = activatedEvent

    def _run(self, *args, **kwargs):
        last_update = datetime.utcnow()
        last_value = False
        self._logger.debug("Handler for %s Starting" % self._triggerInt)
        while True:
            value = self._triggerInt.getActive()
            if value != last_value and datetime.utcnow() - last_update >= self._maxUpdateInterval:
                last_update = datetime.utcnow()
                last_value = value
                # Fire the handlers in thread to prevent long handlers from interrupting the loop
                #Thread(target=self._activatedEvent, args=(TriggerActivatedEventArg(self._trigger, value), )).start()
                self._activatedEvent(TriggerActivatedEventArg(self._triggerId, value, self._action, self._triggerInt.supportedClass))

            sleepTime = max(self._maxUpdateInterval - (datetime.utcnow() - last_update), self._maxPollRate).total_seconds()
            sleep(sleepTime)
