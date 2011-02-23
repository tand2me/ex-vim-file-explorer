
import random
import subprocess 
import time
import os

from logSystem import *

dbg = getLogger('VimLauncher').debug
err = getLogger('VimLauncher').error

class VimLauncherError( Exception ): pass

class VimLauncher:
    def __init__(self, **kwargs):
        '''Init the vim launcher.

        Keyword arguments: 
        - vimExec: path the vim executable file
        - netbeanPwd: netbean password. If not provided, generated on the fly.
        - netbeanPort: port number of the netbean server. Default to 5678
        - netbeanHost: host on which the netbean server is running. Default to localhost.
        - useNetbean:  connect to a netbean host on startup
        '''
        self.vimExec = kwargs.get('vimExec', '')
        self.netbeanPwd = kwargs.get('netbeanPwd', '')
        self.netbeanPort = kwargs.get('netbeanPort', 5678)
        self.netbeanHost = kwargs.get('netbeanHost', 'localhost' )
        self.useNetbean = kwargs.get('useNetbean', True )

        self.delayFirstCommand = 1 # 1 second by default
        self.serverName = 'VIM_WRAPPER'
        self.argServer = [ '--servername', self.serverName ]

        self.vim = None
        self.vimStarted = False
        self.startupTime = 0

        if len(self.netbeanPwd) == 0:
            self.netbeanPwd = ''.join( [ 
                random.choice( 'abcdefghijklmnopqrstuvwzyz0123456789' ) for i in range(8) ] )

    def findVimExecutable( self ):
        '''Try to locate the vim executable on the path.'''
        if len(self.vimExec):
            if os.path.exists( self.vimExec): return
            else:
                msg = 'Vim executable file does not exist: \'%s\'' % self.vimExec
                err( msg )
                raise ValueError( msg )
        # look for gvim executable on the path

    def startVim( self ):
        self.findVimExecutable()
        if len(self.vimExec) == 0:
            raise Exception( 'Can not find vim executable !\n' )

        if self.useNetbean:
            argsNetbean = [ '-nb:localhost:%d:%s' % (self.netbeanPort,self.netbeanPwd) ]
        else:
            argsNetbean = []

        self.serverName = 'VIM_WRAPPER' + ''.join( [ random.choice( '0123456789' * 3 ) for i in
            range(3) ] )
        self.argServer = [ '--servername', self.serverName ]

        self.startupTime = time.time()
        vimCmdLine = [ self.vimExec ] + argsNetbean + self.argServer
        env = dict(os.environ)
        env['SPRO_GVIM_DEBUG']='netbeans.log'
        env['SPRO_GVIM_DLEVEL']='0xffffffff'

        dbg( 'Starting vim with: "%s"', str(vimCmdLine) )
        self.vim = subprocess.Popen( vimCmdLine, shell=False, env=env )
        self.vimStarted = True

    def isVimRunning( self ):
        if not self.vimStarted: return False
        if not self.vim: return False
        return (self.vim.returncode == None)

    def sendKeys( self, keys ):
        '''Send the string keys to the remote Vim.'''
        if not self.isVimRunning():
            raise VimLauncherError( 'Sending keys "%s" to a non running server' % keys )

        vimCmdLine = [ self.vimExec ] + self.argServer + [ '--remote-send', keys ]

        t = time.time()
        deltaTime = t - self.startupTime
        if deltaTime < self.delayFirstCommand:
            deltaTime += 1
            dbg( 'Sleeping %d s to give vim some time to start' % deltaTime )
            time.sleep( deltaTime )

        dbg( 'Sending key to vim: "%s"', keys )
        subprocess.call( vimCmdLine )

    def sendKeysNormalMode( self, keys ):
        '''Send keys but ensure previously that vim is in normal mode to receive them.'''
        self.sendKeys( '<C-\><C-N>' + keys )

    def evalExpr( self, expr ):
        '''Eval expr on the remote Vim. Return the result of the evaluation.'''
        raise VimLauncherError( 'Not working!' )

        if not self.isVimRunning():
            raise VimLauncherError( 'Sending expr "%s" to a non running server' % expr )

        vimCmdLine = [ self.vimExec ] + self.argServer + [ '--remote-expr', expr ]
        dbg( 'Evaluating expr in vim: "%s"', vimCmdLine )
        subprocess.call( vimCmdLine )

        response = self.vim.stdout.readline()
        return response

    def shutDown( self ):
        '''Ask vim to quit.'''
        if not self.isVimRunning(): return
        dbg( 'Shutting down vim' )

        self.sendKeysNormalMode( ':q!<CR>' )
        self.vimStarted = False





