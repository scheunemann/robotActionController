import time
from Data.Model import Sound
from base import Runner
from pygame.mixer import Sound as pySound #apt-get install python-pygame

class SoundRunner(Runner):
    
    @property
    @staticmethod
    def supportedClass():
        return Sound
    
    def __init__(self, robot):
        super(SoundRunner, self).__init__(robot)
        
    def isValid(self, sound):
        return len(sound.data) > 0
        
    def execute(self, sound):
        s = pySound(sound.data)
        channel = s.play()
        while channel.get_busy():
            time.sleep(0.001)