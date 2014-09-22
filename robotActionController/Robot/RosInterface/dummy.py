import time
import robot
import random
import logging


class DummyRobot(robot.Robot):
    _imageFormats = ['BMP', 'EPS', 'GIF', 'IM', 'JPEG', 'PCD', 'PCX', 'PDF', 'PNG', 'PPM', 'TIFF', 'XBM', 'XPM']

    def __init__(self, name):
        super(DummyRobot, self).__init__(name, DummyInterface, '', '')
        self._states = {}

    def getCameraAngle(self):
        time.sleep(random.randrange(0, 10, 1) / 10.0)
        return 0

    def getComponentState(self, componentName, dontResolveName=False):
        if componentName in self._states:
            return (self._states[componentName], self._states[componentName])
        return ('', None)

    def play(self, fileName, blocking=True):
        self.executeFunction("play", {
                                      'parameter_name': fileName,
                                      'blocking': blocking
                                      })

    def say(self, text, languageCode="en-gb", blocking=True):
        self.executeFunction("say", {
                                     'parameter_name': [text, ],
                                     'blocking': blocking})

    def sleep(self, milliseconds):
        self.executeFunction("sleep", {'duration': milliseconds / 1000.0})


class DummyInterface(object):

    def __init__(self):
        self._logger = logging.getLogger(self.__class__.__name__)
        pass

    def runFunction(self, funcName, kwargs):
        self._logger.info("Dummy is pretending to run function: %s" % funcName)
        blocking = True
        if 'blocking' in kwargs:
            blocking = bool(kwargs['blocking'])
        if blocking:
            time.sleep(random.randrange(1, 10, 1) / 2.0)
            return 3
        else:
            return 1

    def initComponent(self, name):
        return 3

    def runComponent(self, name, value, mode=None, blocking=True):
        self._logger.info("Dummy is pretending to move %s to %s" % (name, value))
        if(blocking):
            time.sleep(random.randrange(1, 10, 1) / 2.0)
            return 3
        else:
            return 1
