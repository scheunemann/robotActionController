import time
import threading
from Data.Model import Sound
from base import Runner
import pygame.mixer  # apt-get install python-pygame


class SoundRunner(Runner):

    class SoundHandle(Runner.ExecutionHandle):

        def __init__(self, sound):
            super(SoundRunner.SoundHandle, self).__init__(sound)

        def _runInternal(self, action, session):
            s = pygame.mixer.Sound(action.data)
            channel = s.play()
            while channel.get_busy() and not self._cancel:
                time.sleep(0.001)

            if self._cancel:
                s.stop()
                result = False
            else:
                result = True

            return result

        def waitForComplete(self):
            if not self is threading.current_thread():
                self.join()

            return self._result

        def stop(self):
            self._cancel = True
            self.waitForComplete()

    supportedClass = Sound

    def __init__(self, robot):
        super(SoundRunner, self).__init__(robot)
        pygame.mixer.init()

    def isValid(self, sound):
        return len(sound.data) > 0

    def _getHandle(self, sound):
        return SoundRunner.SoundHandle(sound)
