
import re, types

reStr    = r'"((?:[^\\]|\\["\\nrt])*)"'
reNum    = r'(-?\d+)'
reOptNum = r'(none|-?\d+)'
rePos    = r'(\d+/\d+)'
reBool   = r'(T|F)'
reOptMsg   = r'(.+)?'
argDescReDict = {
    'STR': reStr,
    'PATH': reStr,
    'NUM': reNum,
    'OPTNUM': reOptNum,
    'POS':  rePos,
    'BOOL': reBool,
    'OPTMSG': reOptMsg,
}

def parseNetbeanArgs( netbeanArgs, argDesc ):
    '''Parse a netbean reply string netbeanArgs according to argDesc and return a tuple containing
    the parse results.

    argDesc is a string containing the type of the expected argument concatenated with spaces.

    Possible types, with their associated return value:
    STR     --> the string without the quotes, with backslashing removed
    PATH    --> the path without the quotes, with backslashing removed
    NUM     --> a number
    OPTNUM  --> None or a number
    POS     --> a tuple (line,col)
    BOOL    --> a boolean
    OPTMSG  --> None or a string
    '''
    try:
        argDescList = argDesc.split(' ')
        argDescReList = [ argDescReDict[i] for i in argDescList ]
        reArg = re.compile( ' '.join( argDescReList) + '$' )
        mo = reArg.match( netbeanArgs )
        if not mo:
            raise ValueError( 'TypeError, could not match netbeanArgs \'%s\' with re \'%s\'' % (netbeanArgs, reArg.pattern) )
        ret = []
        # dbg( 'mo=%s', str(mo.groups()) )
        for argType, argVal in zip( argDescList, mo.groups()[0:] ):
            if   argType == 'STR'    : ret.append( simplifyBackslash( argVal ) )
            elif argType == 'PATH'   : ret.append( simplifyBackslash( argVal ) ) 
            elif argType == 'NUM'    : ret.append( int(argVal) )
            elif argType == 'OPTNUM' : ret.append( None if argVal =='none' else int(argVal) )
            elif argType == 'POS' : ret.append( tuple( [ int(i) for i in argVal.split('/') ] ) )
            elif argType == 'BOOL' : ret.append( { 'T':True, 'F':False }[ argVal] )
            elif argType == 'OPTMSG' : ret.append( argVal )
            else:
                raise ValueError( 'Can not grok type \'%s\' for argument \'%s\'' % (argType, argVal) )
        return tuple(ret)
        
    except KeyError:
        raise ValueError( 'TypeError, wrongly formatted argument list: %s' % argDesc )

def simplifyBackslash( s ):
    r'''Return s with \" \n \t \\ converted into single char.'''
    l = list(s)
    i = 0
    while i < len(l)-1:
        if l[i] == '\\':
            if l[i+1] == '\\': l[i:i+2] = '\\'
            elif l[i+1] == 'n': l[i:i+2] = '\n'
            elif l[i+1] == 't': l[i:i+2] = '\t'
            elif l[i+1] == 'r': l[i:i+2] = '\r'
            elif l[i+1] == '"': l[i:i+2] = '"'
            else: raise ValueError( 'Unknown escape sequence: %s' % str(l[i:i+2]) )
        i += 1
    s = ''.join(l)
    return s

def backslashEscape( s ):
    r'''Return s with characters \ \n \t \r " espcaped with a \ '''
    l = list(s)
    i = 0
    while i < len(l):
        if l[i] == '\\': 
            l[i:i+1] = ['\\', '\\' ]
            i += 2
            continue
        elif l[i] == '\n': 
            l[i:i+1] = ['\\', 'n' ]
            i += 2
            continue
        elif l[i] == '\t': 
            l[i:i+1] = ['\\', 't' ]
            i += 2
            continue
        elif l[i] == '\r': 
            l[i:i+1] = ['\\', 'r' ]
            i += 2
            continue
        elif l[i] == '"': 
            l[i:i+1] = ['\\', '"' ]
            i += 2
            continue
        i += 1
    s = ''.join(l)
    return s
        
    

def packArgs( *args ):
    '''Return all the argument converted into netbean format, as a string.

    123             -> 123
    (12,34)         -> 12,34
    some_string     -> "some_string", with special characters backslashed
    True or False   -> T or F

    A space is added at the beginning of the string if it is not empty.
    '''
    retList = []
    for v in args:
        if   type(v) is types.IntType:    retList.append( '%d' % v )
        elif type(v) is types.TupleType:  
            if len(v) != 2: raise ValueError( 'Tuple argument must be of length 2: %s' % str(v) )
            if type(v[0]) is types.IntType and type(v[1]) is types.IntType:
                retList.append( '%d/%d' % v )
            else:
                raise ValueError( 'Tuple must contain two integers: %s' % str(v) )
        elif type(v) is types.StringType: retList.append( '"%s"' % backslashEscape( v ) )
        elif type(v) is types.BooleanType: retList.append( 'T' if v else 'F' )
        else:
            raise ValueError( 'Incorrect argument type: %s' % str(v) )

    # add space if list is not empty
    if len(retList): retList.insert( 0, '' )
    return ' '.join( retList )
    
    

