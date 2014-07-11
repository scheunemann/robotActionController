import threading
from Data.Model import SoundAction
from base import Runner
import pyaudio
import cStringIO
import wave


class SoundRunner(Runner):

    class SoundHandle(Runner.ExecutionHandle):

        def __init__(self, sound):
            super(SoundRunner.SoundHandle, self).__init__(sound)
            self._cancel = True

        def _runInternal(self, action, session):
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

    supportedClass = SoundAction

    def __init__(self, robot):
        super(SoundRunner, self).__init__(robot)

    def isValid(self, sound):
        return len(sound.data) > 0

    def _getHandle(self, sound):
        return SoundRunner.SoundHandle(sound)

if __name__ == '__main__':
    h = SoundRunner.SoundHandle(None)
    h._runInternal(None, None)
