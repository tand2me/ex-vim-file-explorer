
from logSystem import *
import socket
import random

dbg = getLogger('MyTcpServer').debug
err = getLogger('MyTcpServer').error

class MyTcpServer:

    address_family = socket.AF_INET
    socket_type = socket.SOCK_STREAM
    request_queue_size = 5
    allow_reuse_address = False

    def __init__( self, port ):
        self.port = port
        self.socket = None
        self.rfile = None
        self.wfile = None
        self.connected = False

    def startServer( self ):
        dbg('Starting server on port %d' % self.port)
        try:
            self._startSocket()

        except Exception, e:
            dbg('Start failed.')
            if string.find(str(e), "ddress already in use") >= 0:

                # Port number already in use, retry with another port number.
                random.seed()
                self.port = self.port + random.randint( 1,100 )
                dbg('Start failed. Second attempt on port %d' % self.port )
                self._startSocket()
            else:
                err( "Could not start socket server: " + str( e ) )
                raise
        dbg('Server started...')

    def waitForConnection( self ):
        '''Wait until a connection has been made.'''
        self._acceptRequest()

    def closeServer(self):
        self.connected = False
        self.socket.close()
        if self.rfile: self.rfile.close()
        if self.wfile: self.wfile.close()
        self.rfile = None
        self.wfile = None

    def isConnected( self ): return self.connected

    #######################################################################
    #                         Private API
    #######################################################################

    def _startSocket( self ):
        if self.socket: self.socket.close()
        self.socket = socket.socket(self.address_family, self.socket_type)
        if self.allow_reuse_address:
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind( ('', self.port) )
        self.socket.listen(self.request_queue_size)

    def _acceptRequest(self):
        '''Block until the a request is received.

        After the connection is accepted, rfile and wfile are file-like objects to read from the
        socket and write to the socket.

        The socket is put in non-blocking mode.
        '''
        (self.conn, addr) =  self.socket.accept()
        self.conn.settimeout( 0.2 ) # 0.2 s
        self.connected = True

        rbufsize = -1   # buffered for read
        self.rfile = self.conn.makefile('rb', rbufsize)

        wbufsize = 0    # unbuffered for write
        self.wfile = self.conn.makefile('wb', wbufsize)



