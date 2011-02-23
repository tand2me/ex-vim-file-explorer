
from   logSystem import *
from   netbeanArgs import *
import random, errno, re

from myTcpServer import *

dbg = getLogger('NetbeanServer').debug
err = getLogger('NetbeanServer').error

NETBEAN_PORT = 5678

class NetbeanProtocolError(Exception): pass



class NetbeanServer( MyTcpServer ):
    '''Class to handle the netbean protocol.

    The class handles the minimum events necessary to establish a communication
    with a netbean editor client:
        - authentication
        - send and receive message
        - disconnection

    The events related to the editor itself (new documents, ...) should
    be managed in an upper layer.

    To use me:
    netbeanServer = NetbeanServer()
    netbeanServer.startServer()
    # launch netbean client
    netbean.waitForConnection()

    while 1:
        netbean.processRequest()

    netbean.closeServer()
    '''

    def __init__(self, **kwargs ):
        self.netbeanPwd = kwargs.get('netbeanPwd', '')
        self.netbeanPort = kwargs.get('netbeanPort', NETBEAN_PORT)

        self.server = MyTcpServer.__init__(self, self.netbeanPort )

        if self.netbeanPwd == '':
            self.netbeanPwd = ''.join( [ random.choice('abcdefghijklmnopqrstuvwxyz') for i in range(8) ] )

        self.authDone = False
        self.startupDone = False
        self.startupDelayedCmd = []
        self.seqId = 0
        self.waitForReply = None
        self.replyInfo = None

        self.eventHandlerList = []

        self.handlerTable = [
            (self.reAuth, self.handleAuth),
            (self.reEvent, self.handleEvent),
            (self.reReply, self.handleReply),
        ]

        self.eventTable = {
            'startupDone':  self.handleEventStartupDone,
            'version':      self.handleEventVersion,
        }

    def startServer( self ):
        MyTcpServer.startServer( self )
        self.netbeanPort = self.port

    def waitStartupDone( self ):
        '''Wait until startup is finished.'''
        dbg('...')
        while not (self.authDone and self.startupDone):
            self.processRequest(True) # blocking
        dbg('Done')

    #######################################################################
    #                               Inherited
    #
    # def startServer(self)
    # def waitForConnection(self)
    # def closeServer(self)
    # def isConnected(self)


    #######################################################################
    #                               Main loop
    #######################################################################


    def readOneLine( self, blocking=True ):
        '''Read one line from the socket.

        If blocking is false, return either the line read or an empty
        line.

        if blocking is True, blocks until either data is available
        and then return it, or wait until socket is closed and then
        return an empty line.
        '''
        while 1:
            try:
                line = self.rfile.readline()[:-1]
                return line

            except socket.timeout, v:
                if blocking:
                    time.sleep( 0.1 )
                    continue
                else:
                    # no data was available
                    return ''

            except socket.error, v:
                # this is probably not portable, but no other solution available
                # python doc says that the error in that case is OS dependent.
                # need to add errno values for Linux and MacOS...

                if type(v) == type((1,2)):
                    eno, msg = v
                    if eno == errno.EWOULDBLOCK:
                        if blocking:
                            time.sleep( 0.1 )
                            continue
                        else:
                            # no data was available
                            return ''
                    else:
                        err( "Read error from socket: eno=%s" % str(eno) )
                        return ''
                else:
                    err( "Read error from socket: %s" % str(v) )
                    return ''

            except IOError, e:
                # IOError occurs when socket has closed
                return ''

    def processRequest(self, blocking=True):
        '''Handle 0 or 1 request.
        
        Return the number of request handled.
        '''

        # deepdbg('Waiting for request (%s) ...' % { False: 'non blocking', True:'blocking' }[blocking] )
        if self.rfile == None or self.wfile == None or not self.isConnected():
            raise NetbeanProtocolError( 'Server has not accepted connections yet.' )

        line = self.readOneLine( blocking )

        if line == '':
            if blocking:
                # this means the connection has closed
                dbg( 'Connection closed, closing the server.' )
                self.closeServer()

            return 0

        dbg( 'Handling: \'%s\'' % line )

        mo = None
        for (re,func) in self.handlerTable:
            mo = re.match( line )
            if mo: 
                func( line, mo )
                break

        if not mo:
            dbg( 'Could not find handler for: %s', line )
        return 1

    def processVimEvents( self, nbEvents=-1 ):
        '''Call this function regularly to receive all events sent by vim and disptach them
        internally.  The function will process vim events in the queue if present . If no events are
        present, it will return immediately.

        The idea is to call this function inside the global event loop of the application.

        Arguments:
        ==========
        - nbEvents:
            -1:     process all events in the vim queue, if any.
            number: process number events in the vim queue, if they are presents.


        Return: the number of processed events.
        '''
        # dbg('nbEvents=%d', nbEvents)
        processedEvents = self.processRequest( False )
        if nbEvents == -1:
            delta = processedEvents
            while delta:
                # dbg('processed so far: %d', processedEvents)
                delta = self.processRequest( False )
                processedEvents += delta
        else:
            while processedEvents < nbEvents:
                processedEvents += self.processRequest( False )
        return processedEvents
        


    #######################################################################
    #                               Handlers
    #######################################################################


    reAuth = re.compile( 'AUTH\\s+(.*)\\s*' )
    def handleAuth( self, line, mo ):
        '''Handle the AUTH msg.'''
        pwd = mo.group(1)
        if pwd != self.netbeanPwd:
            err( "Wrong password: got '%s', expected '%s'" % (pwd, self.netbeanPwd) )
            self.authDone = False
        self.authDone = True

    reReply = re.compile( r'(\d+)(\s+(.*))*' )
    def handleReply( self, line, mo ):
        seqId = int(mo.group(1))
        args = mo.group(3) or ''
        dbg( 'Reply: seqId=%d, args=\'%s\'', seqId, args )

        if self.waitForReply != seqId:
            msg = 'Received reply for seqId %d while waiting for seqId %d' % (seqId, self.waitForReply)
            err( msg )
            raise NetbeanProtocolError( msg )

        self.replyInfo = args


    reEvent = re.compile( '(\\d+):(\\w+)=(\\d+)(\\s+(.*))*' )
    def handleEvent( self, line, mo ):
        '''Handle any events sent by vim.'''
        eventBufId  = int(mo.group(1))
        eventName   = mo.group(2)
        eventSeqId  = int(mo.group(3))
        eventArgs   = mo.group(5)

        f = self.eventTable.get( eventName, None )
        if f:
            dbg( 'Event handler: ' +  f.__name__ )
            return f(eventBufId, eventName, eventSeqId, eventArgs)
        else:
            self._notifyEvent( eventBufId, eventName, eventArgs )

    def _notifyEvent( self, eventBufId, eventName, eventArgs ):
        '''Internal function to notify all the event handlers of a coming event.'''
        for h in self.eventHandlerList:
            h( eventBufId, eventName, eventArgs )

    def addEventHandler( self, f ):
        '''Add a function to be called when an event arrives from Vim.

        Protocol events are already handled by this class (version, startupDone, ...). The
        events that are passed here are editor events (new buffer, ...).

        The signature of f must be: f( eventBufId, eventName, eventArgs) with
        - eventBufId: number, buffer id
        - eventName: string, event name
        - eventArgs: string, space separated list of event arguments.
        '''
        self.eventHandlerList.append( f )

    def handleEventStartupDone( self, bufId, name, seqId, args ): 
        dbg( 'Vim Startup event received.' )
        self.startupDone = True
        for c in self.startupDelayedCmd:
            dbg( 'Sending delayed commands: %s', c )
            self.sendStr( c )
        self.startupDelayedCmd = []

    def handleEventVersion( self, bufId, name, seqId, args ):
        version = args.strip()[1:-1]
        v = 0
        try:
            v = float(version)
        except ValueError:
            raise NetbeanProtocolError('Invalid version string: %s' % version)
        if v < 2.0:
            raise NetbeanProtocolError('Protocol is too old, we need at least 2.0 and we have %f' % v )
        dbg( 'Netbean protocol v%s activated.' % version )


    #######################################################################
    #                               Send Messages
    #######################################################################


    def sendStr(self, cmd, force=False):
        '''Send something to gvim. 
       
        force:
        - False:
            . raise an exception if not authenticated.
            . if startup event has not been received yet, postpone the command.
            . if authentication has occured and startup event has been received, send the command.

        - True:
            . always send the command (typically, a disconnect).
        '''

        if not force and not self.authDone:
            msg = 'Trying to send \'%s\' but vim is not authententicated.' % cmd
            err( msg )
            raise NetbeanProtocolError( msg )

        if not force and not self.startupDone:
            dbg( 'Vim has not started, postponing cmd \'%s\'' % cmd )
            self.startupDelayedCmd.append( cmd )
        else:
            if force: forceMsg = '(by force)' 
            else: forceMsg = ''
            dbg( "Sending command %s '%s' to GVim" % (forceMsg, cmd) )
            self.wfile.write(cmd + '\n')

    def sendCmd(self, bufId, cmd, *args ): 
        '''Send a command to gvim.
           If "arg" is given it must start with a space!'''
        self.seqId += 1
        self.sendStr("%d:%s!%d%s" % (bufId, cmd, self.seqId, packArgs( *args )))

    def sendCmdWithReply( self, bufId, cmd, *args ):
        '''Send the command to gvim and process incoming events until a reply to the command
        is received.

        Raises an exception if not authenticated or if startup is not done.

        Return the reply string.
        '''
        
        if not self.authDone or not self.startupDone:
            msg = 'Trying to send \'%s\' but vim is not authententicated or has not started up.' % cmd
            err( msg )
            raise NetbeanProtocolError( msg )

        
        self.seqId += 1
        self.sendStr("%d:%s/%d%s" % (bufId, cmd, self.seqId, packArgs( *args )) )
        self.waitForReply = self.seqId
        self.replyInfo = None

        # in theory, we get a reply immediately but let's be precautious
        infiniteLoopDetector = 300
        while self.replyInfo == None:
            dbg( 'Reply loop=%d' % infiniteLoopDetector )
            # blocking request handler
            self.processRequest( True )
            infiniteLoopDetector -= 1
            if infiniteLoopDetector == 0:
                msg = 'Infinite loop while waiting for reply to \'%d\'' % self.waitForReply
                err( msg )
                raise NetbeanProtocolError( msg )

        # we have our reply in self.replyInfo
        ret = self.replyInfo
        self.replyInfo = None
        return ret

    def call( self, bufId, cmd, replyFmt, *args ):
        '''Send a command with a reply to Vim, check the reply value
        against a reply format specified in replyFmt.

        replyFmt is a string with space separated speficiations of formats:
        - STR
        - PATH
        - NUM
        - OPTNUM
        - POS
        - BOOL
        - OPTMSG

        See the netbean documentation and the parseNetbeanArgs() function for details.

        Each reply argument is converted into an appropriate type and is returned inside
        a tuple.

        In case of incorrect format specified, NetbeanProtocolError is raised.
        '''
        self.processVimEvents()
        s = self.sendCmdWithReply( bufId, cmd, *args )
        try:
            ret = parseNetbeanArgs( s, replyFmt )
            return ret
        except ValueError:
            raise NetbeanProtocolError( 'Unexpected response format: %s for format %s' % (s, replyFmt ) )

    def pingConnection( self ):
        '''Return True if connection is alive, else False.

        Uses the getDot command to check the connection status.
        '''
        try:
            # ping requiers a connection
            if self.isConnected() == False: return False

            self.call( 0, 'getCursor', 'NUM NUM NUM NUM')
            return True
        except NetbeanProtocolError:
            # we assume this is a network error
            return False

    def sendDisconnect(self):
        '''Send disconnect message to vim, set the stop flag in our server.'''
        dbg( 'Disconnecting from vim' )
        self.sendStr("DISCONNECT", True)

