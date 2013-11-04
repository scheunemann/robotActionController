import logging
from Data.Model import Action

class Runner(object):
    
    @property
    @staticmethod
    def supportedClass():
        return Action
        
    def __init__(self, robot):
        self._robot = robot;
        self._logger = logging.getLogger(__name__)
        
    @staticmethod
    def isValid(action):
        return action != None
    
    def execute(self, action):
        pass
