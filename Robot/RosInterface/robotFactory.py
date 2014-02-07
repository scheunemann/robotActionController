import sys
import logging


class Factory(object):

    _interfaces = {}

    @staticmethod
    def getRobotInterface(robot):
        if robot.name not in Factory._interfaces:
            logger = logging.getLogger(Factory.__name__) 
            logger.info("Building class for robot named: %s" % robot.name)
            robotInt = None
            try:
                qualifiedName = robot.model.extraData['className']
                if qualifiedName.rfind('.') > 0:
                    class_ = qualifiedName[qualifiedName.rfind('.') + 1:]
                    module = qualifiedName[:qualifiedName.rfind('.')]
                else:
                    class_ = []
                    
                ns = __import__(module, globals(), locals(), [class_, ])
                robotClass = getattr(ns, class_)
                if robot.model.extraData.has_key('classArgs'):
                    kwargs = robot.model.extraData['classArgs']
                else:
                    kwargs = {}
                
                robotInt = robotClass(robot.name, **kwargs)
            except ImportError as e:
                logger.critical("Unknown robot type %s" % robot.model.name)
            except Exception as e:
                logger.critical("An error occured while loading robot %s" % (robot))
                logger.critical(e)
                return None
    
            Factory._interfaces[robot.name] = robotInt
            logger.info("Finished building class %s" % robotInt.__class__.__name__)
        
        return Factory._interfaces[robot.name]
