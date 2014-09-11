import threading
from base import ActionRunner, ActionExecutionHandle
from collections import namedtuple
import logging
import pyaudio
import cStringIO
import wave
import time


class SoundExecutionHandle(ActionExecutionHandle):

    CHUNK = 1024
    __audio = None

    def __init__(self, sound):
        super(SoundExecutionHandle, self).__init__(sound)
        self._cancel = True

    @property
    def _audio(self):
        if SoundExecutionHandle.__audio == None:
            #TODO: when to call PyAudio.terminate()?
            SoundExecutionHandle.__audio = pyaudio.PyAudio()
        return SoundExecutionHandle.__audio

    def _runInternal(self, action):
        p = self._audio
        cb = cStringIO.StringIO(action.data)
        wf = wave.open(cb, 'rb')
        stream = p.open(format=p.get_format_from_width(wf.getsampwidth()), channels=wf.getnchannels(), rate=wf.getframerate(), output=True)
        data = wf.readframes(SoundExecutionHandle.CHUNK)
        while data != '':
            if self._cancel:
                break
            stream.write(data)
            #python Y U NO THREAD!!?
            #sleep to, hopefully briefly, release the GIL so other threads can execute
            #important for simultaneous running, i.e. groups, but potentially causes audio distortion
            time.sleep(0.0001)
            data = wf.readframes(SoundExecutionHandle.CHUNK)

        stream.stop_stream()
        stream.close()

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
        return SoundExecutionHandle(sound)
