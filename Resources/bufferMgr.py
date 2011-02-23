 
#######################################################################
#                               Buffer info
#######################################################################

EVT_BUFFER_CREATED = 'BufferCreated'
EVT_BUFFER_DELETED = 'BufferDeleted'


class BufferItem:
    '''A class to hold information about a vim buffer.

    It contains two properties:
    bufId: vim bufId for this buffer
    path: absolute path to this buffer
    '''

    def __init__(self, bufId=None, path=None ):
        self.bufId = bufId
        self.path = path

class BufferMgr:

    def __init__( self ):
        self.bufferList = []    
        self.nextBufId = 1
        self.eventHandlerList = []

    def createBufId( self ):
        '''Create a new bufId for later use in addBuffer.'''
        bufId = self.nextBufId
        self.nextBufId += 1
        return bufId
        
    def addBuffer( self, bufId, path ):
        '''Add a buffer, get a new bufId for it and return it.'''
        if self.hasPath( path ): return self.bufIdOfPath( path )
        item = BufferItem( bufId, path )
        self.bufferList.append(  item )
        self.notifyEvent( EVT_BUFFER_CREATED, (bufId, path ) )
        return bufId

    def rmBufferByBufId( self, bufId ):
        '''Remove the buffer identified with bufId.'''
        target = [ (i,item) for (i,item) in enumerate(self.bufferList) if item.bufId == bufId ]
        if len(target) == 0:
            raise IndexError( 'Could not find bufId %d' % bufId )
        if len(target) > 1:
            raise IndexError( 'More than one buffer with bufId %d' % bufId )
        
        i,item = target[0]
        del self.bufferList[i]
        self.notifyEvent( EVT_BUFFER_DELETED, ( item.bufId, item.path ) )

    def firstBufId( self ):
        if len(self.bufferList): 
            return self.bufferList[0].bufId
        else: 
            return None

    def pathOfBufId( self, bufId ):
        '''Return the path associated with bufid.'''
        return [ item.path for item in self.bufferList if item.bufId == bufId ][0]

    def bufIdOfPath( self, path ):
        '''Return the bufId associated with the path.'''
        return [ item.bufId for item in self.bufferList if item.path == path ][0]

    def hasBufId( self, bufId ):
        '''Return true if bufId already exists.'''
        return len([ item for item in self.bufferList if item.bufId == bufId ]) >= 1
        
    def hasPath( self, path ):
        '''Return true if path already exists.'''
        return len([ item for item in self.bufferList if item.path == path ]) >= 1

    def nextBuffer( self, bufId ):
        '''Return the bufId after this bufId to activate the next buffer.'''
        for i,item  in enumerate( self.bufferList ):
            if item.bufId == bufId:
                break
        else:
            raise IndexError( 'No such bufId: %d' % bufId )
        i = (i + 1) % len(self.bufferList)
        return self.bufferList[i].bufId 

    def clear( self ):
        '''Clear the content.'''
        self.bufferList = []
        # should we reset nextBufId too ?

    def bufferNb( self ):
        '''Return the number of buffer'''
        return len(self.bufferList)

    def __str__(self):
        return str(self.bufferList)

    def addEventHandler( self, eventHlr ):
        '''Add an event handler that will receive buffer creation and deletion events.

        Events are formatted as (EventName, EventArgs):
        EventName       |   Args
        ----------------------------------
        BufferCreated   | Path of the buffer
        BufferDeleted   | Path of the buffer
        '''
        self.eventHandlerList.append( eventHlr )

    def notifyEvent( self, eventName, eventArgs ):
        for hlr in self.eventHandlerList:
            hlr( eventName, eventArgs )

        



