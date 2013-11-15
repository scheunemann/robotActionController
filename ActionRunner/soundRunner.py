import time
from Data.Model import Sound
from base import Runner
import pygame.mixer  # apt-get install python-pygame

class SoundRunner(Runner):

    class SoundHandle(Runner.ExecutionHandle):

        def __init__(self, sound):
            super(SoundRunner.SoundHandle, self).__init__(sound)
            self._sound = sound

        def run(self):
            s = pygame.mixer.Sound(self._sound.data)
            channel = s.play()
            while channel.get_busy() and not self._cancel:
                time.sleep(0.001)

            if self._cancel:
                s.stop()
                self._result = False
            else:
                self._result = True

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
        handle = SoundRunner.SoundHandle(sound)
        return handle
