
from vimLauncher import VimLauncher
from netbeanServer import NetbeanServer, parseNetbeanArgs
from logSystem import getLogger
from bufferMgr import BufferMgr

dbg = getLogger('VimWrapper').debug

class VimWrapper:
    '''The frontend for wrapping vim. It will launch vim and initiate the netbean communication.
    
    It provides easy-to-use members to interact with vim, be notified about vim events, ...
    '''

    def __init__(self, **kwargs):
        '''Init the vim wrapper.

        Keyword arguments: 
        - vimExec: path the vim executable file
        '''
        self.server = None
        self.vimLauncher = None
        self.vimExec = kwargs['vimExec']
        self.bufInfo = BufferMgr()
        self.ignoreNextOpenFile = 0

    def start( self ):
        '''Start the netbean server and vim client.'''
        dbg( '...' )    
        self.server = NetbeanServer()
        self.server.startServer()
        self.server.addEventHandler( self.eventReceived )
    
        self.vimLauncher = VimLauncher( vimExec=self.vimExec, netbeanPort=self.server.netbeanPort, netbeanPwd=self.server.netbeanPwd )
        self.vimLauncher.startVim()

        self.server.waitForConnection()
        self.server.waitStartupDone()
        dbg( 'done' )    

    def close( self ):
        '''Close vim and the netbean server.'''
        if self.server and self.server.isConnected():
            self.server.sendDisconnect()
            self.server.closeServer()
        self.bufInfo.clear()

    def processVimEvents( self, nbEvents=-1 ):
        self.server.processVimEvents( nbEvents )
    
    #######################################################################
    #                               Vim Access Functions
    #######################################################################
    
    # For all the functions here, the following applies:
    # - line numbering starts at 1.
    # - column starts at 0 and is byte based. A tab for example counts for one column increment a
    # single character with double bytes will count for two columns.
    # - offset starts at 0 and is byte based. A double-byte char will bring offset to two.


    ##########  Buffer info, properties

    def _getCursor( self ):
        '''Return the current (bufId, cursorLine, cursorCol, cursorFileOffset ).'''
        s = self.server.call( 0, 'getCursor', 'NUM NUM NUM NUM')
        return s

    def getBufId( self ): return self._getCursor()[0]
    def getCursorLine( self ): return self._getCursor()[1]
    def getCursorCol(  self ): return self._getCursor()[2]
    def getCursorLineCol( self ): return self._getCursor()[1:3]
    def getCursorOffset( self ): return self._getCursor()[3]

    def getLength( self, bufId ):
        '''Length of the content of the current buffer.'''
        return self.server.call( bufId, 'getLength', 'NUM' )[0]

    def setModified( self, bufId, modified):
        '''Mark the buffer as modified.'''
        return self.server.sendCmd( bufId, 'setModified', bool(modified) )

    def isBufferModified( self, bufId ):
        '''Return True if the buffer bufId is modified.'''
        ret = self.server.call( bufId, 'getModified', 'NUM' )[0]
        return ret == 1

    def numberBufferModified( self ):
        '''Return the number of currently modified buffer. When this number is 0
        it is safe to tell vim to exit.'''
        return self.server.call( 0, 'getModified', 'NUM' )


    def setCurrentBuffer( self, bufId ):
        '''Set bufId as the current buffer.'''
        self.server.sendCmd( bufId, 'setVisible', True )

    def setCurrentBufferByPath( self, path ):
        '''Set path as the current buffer.'''
        bufId = self.bufInfo.bufIdOfPath( path )
        self.server.sendCmd( bufId, 'setVisible', True )

    def setCurrentBufferOffset( self, bufId, offset ):
        '''Make bufId the current buffer and position the cursor at offset.'''
        self.server.sendCmd( bufId, 'setDot', offset )

    def setCurrentBufferLineCol( self, bufId, line, col ):
        '''Make bufId the current buffer and position the cursor at (line,col)'''
        self.server.sendCmd( bufId, 'setDot', (line,col) )

    def setBufferReadonly( self, bufId ):
        '''Set the bufId as readOnly.'''
        self.server.sendCmd( bufId, 'setReadOnly' )

    ######### Text manipulation


    def text( self, bufId ):
        '''Return the content of the buffer bufId.'''
        return self.server.call( bufId, 'getText', 'STR' )[0]

    def insertText( self, bufId, offset, text ):
        '''Make bufId the current buffer and insert text at the offset.

        Warning, this will not change the isBufferModified status. The status
        must be changed explicitely.

        Return: None on success, message on failure.'''
        return self.server.call( bufId, 'insert', 'OPTMSG', offset, text )[0]

    def removeText( self, bufId, offset, length ):
        '''Delete text starting from offset, up to length. Make bufId the current buffer.

        Warning, this will not change the isBufferModified status. The status
        must be changed explicitely.

        Return None upon success, or an error message upon failure.
        '''
        return self.server.call( bufId, 'remove', 'OPTMSG', offset, length )[0]


    ########## Buffer manipulation

    def openFile( self, path ):
        '''Open the specified file.

        Return the bufId of the new buffer.
        '''
        bufId = self.bufInfo.createBufId()
        self.ignoreNextOpenFile += 1
        self.server.sendCmd( bufId , 'editFile', path )
        self.processVimEvents()
        self.server.sendCmd( bufId, 'setFullName', path )
        self.server.sendCmd( bufId, 'initDone' )
        self.bufInfo.addBuffer( bufId, path )
        return bufId

    def createBuffer( self, path ):
        '''Create a new buffer in Vim with the bufId specified. 

        Return the bufId of the new buffer.
        '''
        bufId = self.bufInfo.createBufId()

        if 1:
            self.server.sendCmd( bufId, 'create' )
            self.server.sendCmd( bufId, 'setTitle', path )
            self.server.sendCmd( bufId, 'setFullName', path )
            self.server.sendCmd( bufId, 'initDone' )
        else:
            # optional alternative implemtation
            self.server.sendCmd( bufId, 'editFile', path )
            self.server.sendCmd( bufId, 'setFullpath', path )
            self.server.sendCmd( bufId, 'initDone' )

        self.bufInfo.addBuffer( bufId, path )
        # fetch the fileOpened event
        self.processVimEvents()

        return bufId

    def closeBuffer( self, bufId ):
        '''Close the current buffer, assigns the next available buffer as current buffer.

        If this is the last buffer, we are without current buffer.

        No return value.
        '''
        curBufId = self.getBufId()
        nextBufId = self.bufInfo.nextBuffer( bufId )
        self.bufInfo.rmBufferByBufId( bufId )
        self.server.sendCmd( bufId, 'close' )
        if curBufId == bufId:
            self.setCurrentBuffer( nextBufId )

    def assignBufId( self, bufId, path ):
        '''Assign the bufId to the path, for recently opened buffers.'''
        self.server.sendCmd( bufId, 'putBufferNumber', path )

    def saveBuffer( self, bufId ):
        '''Save the buffer and display message saved.'''
        self.server.sendCmd( bufId, 'save' )
        self.server.sendCmd( bufId, 'saveDone' ) # display 'buffer saved' in vim

    def saveAndExit( self ):
        '''Save all the modified buffers and tell vim to exit.

        Return:
        -  0: success vim closes the connection.
        -  n > 0: user has canceled the operation, n buffer still contain modifications.
        '''
        return self.server.call( 0, 'saveAndExit', 'OPTNUM' )

    def addEventHandler( self, hlr ):
        '''Add an event handler to receive buffer created/deleted events.'''
        self.bufInfo.addEventHandler( hlr )

    ########### Keys

    def setSpecialKeys( self, keys ):
        '''Set netbeans hotkeys.'''
        self.server.sendCmd( 0, 'specialKeys', keys )
 
    def sendKeys( self, keys ):
        '''Send the key string keys to vim.'''
        self.vimLauncher.sendKeys( keys )

    def sendKeysNormalMode( self, keys ):
        '''Send the key string keys to vim, but ensure that Vim is normal mode previously.'''
        self.vimLauncher.sendKeysNormalMode( keys )


    ########### Other

    def raiseVim( self ):
        '''Raise the vim window to ght foreground.'''
        self.server.sendCmd( 0, 'raise' )

    ########### Events

    def eventReceived( self, bufId, name, args ):
        '''Called when a vim event is received.'''
        dbg( '%d %s \'%s\'' % (bufId, name, args ) )
       
        f = self.eventMap.get( name, VimWrapper.eventIgnore ) 
        f( self, bufId, name, args )

    def eventIgnore( self, bufId, name, args ):
        '''Ignore the event!'''
        pass
            
    def eventFileOpened( self, bufId, name, args ):
        if bufId != 0:
            # file is already associated
            return

        if bufId == 0 and self.ignoreNextOpenFile > 0:
            dbg( 'Ignoring event because of self.ignoreNextOpenFile = %d', self.ignoreNextOpenFile )
            self.ignoreNextOpenFile -= 1
            return

        # need to associate the file
        path, opened, modified = parseNetbeanArgs( args, 'STR BOOL BOOL' )
        dbg( 'path="%s"', path )
        bufId = self.bufInfo.createBufId()
        self.assignBufId( bufId, path )
        self.bufInfo.addBuffer( bufId, path )

    def eventFileClosed( self, bufId, name, args ):
        dbg( '%d %s \'%s\'' % (bufId, name, args ) )
        self.bufInfo.rmBufferByBufId( bufId )
        

    def eventKeyAtPos( self, bufId, name, args ):
        '''Triggered when a netbeans hotkey is pressed along with <Pause>'''
        dbg( '%d %s \'%s\'' % (bufId, name, args ) )
        key, offset, (line,col) = parseNetbeanArgs( args, 'STR NUM POS' )
        self.bufInfo.notifyEvent( 'Hotkey', (bufId, key, offset, (line,col) ) )

    def eventKeyCommand(self, bufId, name, args ):
        keyName = parseNetbeanArgs( args, 'STR' )
        alert(keyName)


    eventMap = {
        'fileOpened':       eventFileOpened,
        'killed':           eventFileClosed,
        'newDotAndMark':    eventIgnore,
        'keyCommand':       eventKeyCommand,
        'keyAtPos':         eventKeyAtPos,
    }

