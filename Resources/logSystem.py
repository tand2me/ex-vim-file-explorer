
import platform
from logging import *
from logging.handlers import *
import sys
import tempfile


# one more level of debugging, disabled by default
DEEPDEBUG = 1
def deepDebug( msg, *args, **kwargs ):
    return log( DEEPDEBUG, msg, *args, **kwargs )

class Win32DebugStream:
    def __init__(self):
        self._isWindows = platform.system() == 'Windows'
        self._outputDebugString = None
        try:
            from win32api import OutputDebugString
            self._outputDebugString = OutputDebugString
        except ImportError:
            pass

    def write(self, *args):
        if not self._isWindows or not self._outputDebugString: return
        self._outputDebugString( ''.join(args) )

    def close(self):
        pass

    def flush(self):
        pass

class NullStream:
    def write(self, *args): pass
    def flush(self): pass

def initLogSystem( defaultStream=NullStream() ):
    #stream=Win32DebugStream(),
    #stream=sys.stderr
    #stream=NullStream()

    basicConfig( format='%(name)15s.%(funcName)s %(message)s',
                 level=DEBUG , 
                 stream=defaultStream
                ) 
    rootLog = getLogger()

    # stderr debugging
    if 0:
        # there is alrady a default stderr formatter
        stderrHandler = StreamHandler( sys.stderr )
        formatter = logging.Formatter('%(name)15s.%(funcName)s %(message)s')
        stderrHandler.setFormatter(formatter)

        # choice to make
        stderrHandler.setLevel( WARNING )
        stderrHandler.setLevel( DEBUG )
        rootLog.addHandler( stderrHandler )

    # tmp file debugging
    if 0:
        tempdir = tempfile.gettempdir()
        tmpfile = tempdir + '/vy-debug.log'
        tmpfileHandler = FileHandler( tmpfile )
        tmpfileHandler.setLevel( DEBUG )
        # rootLog.addHandler( tmpfileHandler )


