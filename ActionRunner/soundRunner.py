import threading
from base import ActionRunner, ActionExecutionHandle
from collections import namedtuple
import logging
import pyaudio
import cStringIO
import wave


class SoundExeuctionHandle(ActionExecutionHandle):

    def __init__(self, sound):
        super(SoundExeuctionHandle, self).__init__(sound)
        self._cancel = True

    def _runInternal(self, action):
        CHUNK = 1024
        p = pyaudio.PyAudio()
        cb = cStringIO.StringIO(action.data)
        wf = wave.open(cb, 'rb')
        stream = p.open(format=p.get_format_from_width(wf.getsampwidth()), channels=wf.getnchannels(), rate=wf.getframerate(), output=True)
        data = wf.readframes(CHUNK)
        while data != '':
            stream.write(data)
            data = wf.readframes(CHUNK)

        stream.stop_stream()
        stream.close()
        p.terminate()

        return not self._cancel

    def waitForComplete(self):
        if not self is threading.current_thread():
            self.join()

        return self._result

    def stop(self):
        self._cancel = True
        self.waitForComplete()


class SoundRunner(ActionRunner):
    supportedClass = 'SoundAction'
    Runable = namedtuple('SoundAction', ActionRunner.Runable._fields + ('data',))

    @staticmethod
    def getRunable(action):
        if action.type == SoundRunner.supportedClass:
            return SoundRunner.Runable(action.name, action.id, action.type, action.minLength, action.data)
        else:
            logger = logging.getLogger(SoundRunner.__name__)
            logger.error("Action: %s has an unknown action type: %s" % (action.name, action.type))
            return None

    def __init__(self, robot):
        super(SoundRunner, self).__init__(robot)

    def isValid(self, sound):
        return len(sound.data) > 0

    def _getHandle(self, sound):
        return SoundExeuctionHandle(sound)
