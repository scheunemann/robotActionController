from base import ActionRunner
from collections import namedtuple
import logging
import pyaudio
import audioop
import cStringIO
import wave
import math
from gevent import sleep


class SoundRunner(ActionRunner):
    supportedClass = 'SoundAction'
    Runable = namedtuple('SoundAction', ActionRunner.Runable._fields + ('data','uuid','volume'))
    __audio = None
    _CHUNKSIZE = 1024

    def __init__(self, sound, *args, **kwargs):
        super(SoundRunner, self).__init__(sound)
        self._cancel = True
        self._logger = logging.getLogger(self.__class__.__name__)
        self._file = None

    @property
    def _audio(self):
        if SoundRunner.__audio == None:
            #TODO: when to call PyAudio.terminate()?
            SoundRunner.__audio = pyaudio.PyAudio()
        return SoundRunner.__audio

    #def __callback(self, in_data, frame_count, time_info, status):
    def _callback(self, frame_count, frame_width, volume):
        if self._cancel:
            ret = (None, pyaudio.paAbort)
        else:
            data = self._file.readframes(frame_count)
            data = audioop.mul(data, frame_width, volume)
            ret = (data, pyaudio.paContinue if data else pyaudio.paComplete)
        return ret

    def _runInternal(self, action):
        p = self._audio
        try:
            volume = (action.volume / 100.0) or 1
            volMul = (math.exp(volume)-1)/(math.e-1)
            print "Volume: %s, Raw: %s (%s), %s" % (volMul, action.volume, (action.volume / 100.0), type(action.volume))
            data = cStringIO.StringIO(action.data)
            self._file = wave.open(data, 'rb')
            frame_width = self._file.getsampwidth()
            callback = lambda in_data, frame_count, time_info, status: self._callback(SoundRunner._CHUNKSIZE, frame_width, volMul)
            self._cancel = False
            stream = p.open(format=p.get_format_from_width(frame_width),
                            channels=self._file.getnchannels(),
                            rate=self._file.getframerate(), 
                            output=True,
                            stream_callback=callback)
        except Exception:
            self._logger.error("Error in portaudio: ", exc_info=True)
            return False

        stream.start_stream()
        try:
            while stream.is_active():
                sleep(0.001)
        except:
            self._cancel = True
            raise
        finally:
            stream.stop_stream()
            stream.close()

            self._file.close()
            self._file = None

        return not self._cancel


    @staticmethod
    def getRunable(action):
        if action.type == SoundRunner.supportedClass:
            return SoundRunner.Runable(action.name, action.id, action.type, action.data, action.uuid, action.volume)
        else:
            logger = logging.getLogger(SoundRunner.__name__)
            logger.error("Action: %s has an unknown action type: %s" % (action.name, action.type))
            return None

    def isValid(self, sound):
        return len(sound.data) > 0
