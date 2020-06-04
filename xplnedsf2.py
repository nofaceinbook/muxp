#******************************************************************************
#
# xplnedsf2.py        Version 0.5.6  for muxp
# ---------------------------------------------------------
# Python module for reading and writing X_Plane DSF files.
#
#
# WARNIG: This code is still under development and may still have some errors.
#         In case you use it be very careful!
#
# Copyright (C) 2020 by schmax (Max Schmidt)
#
# This source is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation; either version 3 of the License, or (at your option)
# any later version.
#
# This code is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR 
# A PARTICULAR PURPOSE.  See the GNU General Public License for more details.  
#
# A copy of the GNU General Public License is available at:
#   <http://www.gnu.org/licenses/>. 
#
#******************************************************************************

### NEW 0.5.4: Encoding PORP Atom, correct decoding of V32 pools/scaling using
###            correct max_int for modulo unwrapping, and encoding 32bit pools
### NEW 0.5.6: Added separate function isDSFoverlay(file) to test whether a dsf file is an overlay
###            Checking out of bound when packing raster values (might be removed again!)

from os import path, stat #required to retrieve length of dsf-file
from struct import pack, unpack #required for binary pack and unpack
from hashlib import md5 #required for md5 hash in dsf file footer
from logging import StreamHandler, getLogger, Formatter #for output to console and/or file
from io import BytesIO #required to go through bytes of a read 7ZIP-File
from math import sin, cos, sqrt, atan2, radians # for distance calculation etc.

try:
    import py7zlib
except ImportError:
    PY7ZLIBINSTALLED = False
else:
    PY7ZLIBINSTALLED = True



class XPLNEpatch:
    def __init__(self, flag, near, far, poolIndex, defIndex):
        ################# TBD: poolIndex not required, can be removed and defintion of poolIndex with first command can be done by trias2cmds as updated below ######################################
        self.flag = flag
        self.near = near
        self.far = far
        self.defIndex = defIndex
        self.cmds = []
    def triangles(self): #returns triangles as a list l of [3 x vertexes] that are defined by commands c of thte patch where each vertex of triangle is a pair of index to pool p and vertex        
        l = []
        p = None #current pool needs to be defined with first command
        for c in self.cmds:
            if c[0] == 1: # Pool index changed within patch, so change
                p = c[1]
            elif c[0] == 23: # PATCH TRIANGLE
                for v in range (1, len(c), 3): #skip value (command id)
                    l.append( [ [p, c[v]], [p, c[v + 1]], [p, c[v + 2]] ])
            elif c[0] == 24: # PATCH TRIANGLE CROSS POOL
                for v in range (1, len(c), 6): #skip value (command id)
                    l.append( [ [c[v], c[v+1]], [c[v+2], c[v+3]], [c[v+4], c[v+5]] ] )
            elif c[0] == 25: # PATCH TRIANGLE RANGE 
                for v in range(c[1], c[2] - 1, 3): #last index has one added 
                    l.append( [ [p, v], [p, v + 1], [p, v + 2] ] )
            elif c[0] == 26: # PATCH TRIANGLE STRIP
                for v in range (3, len(c)): #skip first three values - including command id are not needed any more
                    if v % 2: ##### NEW: Strip 1,2,3,4,5 refers to triangles 1,2,3 2,4,3 3,4,5 
                        l.append( [ [p, c[v-2]], [p, c[v-1]], [p, c[v]] ] )  
                    else:                                                    
                        l.append( [ [p, c[v-2]], [p, c[v]], [p, c[v-1]] ] )  
            elif c[0] == 27: # PATCH TRIANGLE STRIP CROSS POOL             
                for v in range (6, len(c), 2): #skip first values - including command id are not needed any more
                    if v % 4: ##### NEW: Strip 1,2,3,4,5 refers to triangles 1,2,3 2,4,3 3,4,5 
                        l.append( [ [c[v-5], c[v-4]], [c[v-3], c[v-2]], [c[v-1], c[v]] ] )  
                    else:                                                                   
                        l.append( [ [c[v-5], c[v-4]], [c[v-1], c[v]], [c[v-3], c[v-2]] ] )  
            elif c[0] == 28:  # PATCH TRIANGLE STRIP RANGE
                for v in range(c[1], c[2] - 2): # last index has one added so -2 as we go 2 up and last in range is not counted
                    if (v - c[1]) % 2:  ##### NEW: Strip 1,2,3,4,5 refers to triangles 1,2,3 2,4,3 3,4,5 
                        l.append( [ [p, v], [p, v + 2], [p, v + 1] ] ) 
                    else:                                              
                        l.append( [ [p, v], [p, v + 1], [p, v + 2] ] ) 
            elif c[0] == 29: # PATCH TRIANGLE FAN                          ##(all FAN commands not yet tested!!!!!!!!)##
                for v in range (3, len(c)): #skip first three values - including command id are not needed any more
                    l.append( [ [p, c[1]], [p, c[v-1]], [p, c[v]] ] ) #at c[1] is the center point id of the fan
            elif c[0] == 30: # PATCH TRIANGLE FAN CROSS POOL
                for v in range (6, len(c), 2): #skip first values - including command id are not needed any more
                    l.append( [ [c[1], c[2]], [c[v-3], c[v-2]], [c[v-1], c[v]] ] ) #at c[1] is the pool index for fan center and at c[2] the point id
            elif c[0] == 31:  # PATCH FAN RANGE
                for v in range(c[1], c[2] - 2): # at c[1] center point; last index has one added so -2 as we go 2 up and last in range is not counted
                    l.append( [ [p, c[1]], [p, v + 1], [p, v + 2] ] )                    
        return l
              
    def trias2cmds(self, trias): ############## UPDATE FOR MEXP to allow definition of own trias 
        ### For the moment only uses single tirangle CMDS for different pools ## To be updeated
        if len(self.cmds) > 0: ############### NEW 03.04.2020 ####################################
            self.cmds = [self.cmds[0]] #just stay with pool defintion in first command
        else: #first command not yet set
            self.cmds = [[1, trias[0][0][0]]] #take pool from first vertex in first tria as first command to define pool
        i = 0 #counts number of trias
        c = [] #builds single commands
        for t in trias:
            if (i % 85) == 0: #start new triangle command at beginning and when max length is reached (3 value pairs per triangle, so 255 / 3 = 85)
                if len(c) > 1: #are there already values for commands
                    self.cmds.append(c) #append them the the commands
                c = [24]
            c.extend(t[0])
            c.extend(t[1])
            c.extend(t[2])
            i += 1
        if len(c) > 1:
            self.cmds.append(c) #add the final command


class XPLNEraster: #Stores data of Raster Atoms (each dsf could have serverl raster layers)
    def __init__(self):
        self.ver = None #Version of Raster
        self.bpp = None #bytes per pixel in raster data
        self.flags = None #flags about Raster centricity and what data type used
        self.width = None #of area in pixel
        self.height = None #of area in pixel
        self.scale = None #scale factor for height values
        self.offset = None #offset for heigt values
        self.data = [] #will store final raster heigt values (after scaling and adding offset) in 2-dimensional list: [pixel x] [pixel y]
        

class XPLNEDSF:   
    def __init__(self, logname='__XPLNEDSF__', statusfunction = "stdout"):
        if logname != "_keep_logger_": self._log_ = self._setLogger_(logname)
        if statusfunction != "_keep_statusfunction_": self._statusfunction_ = statusfunction
        self._DEBUG_ = True if self._log_.getEffectiveLevel() < 20 else False #have DEBUG value in order to call only logger for debug if DEBUG enabled  --> saves time
        self._progress_ = [0, 0, 0] #progress as 3 list items (amount of bytes read/written in percant and shown, read/written but not yet shown as number of bytes) and number of bytes to be processed in total
        self._Atoms_ = {} #dictonary containg for every atom in file the according strings
        self._AtomStructure_ = {'DAEH' : ['PORP'], 'NFED' : ['TRET', 'TJBO', 'YLOP', 'WTEN', 'NMED'], 'DOEG' : ['LOOP', 'LACS', '23OP', '23CS'], 'SMED' : ['IMED', 'DMED'], 'SDMC' : []}
        self._AtomList_ = ['DAEH', 'NFED', 'DOEG', 'SMED', 'SDMC', 'PORP', 'TRET', 'TJBO', 'YLOP', 'WTEN', 'NMED', 'LOOP', 'LACS', '23OP', '23CS', 'IMED', 'DMED']
        self._AtomOfAtoms_ = ['DAEH', 'NFED', 'DOEG', 'SMED']
        self._MultiAtoms_ = ['LOOP', 'LACS', '23OP', '23CS', 'IMED', 'DMED'] #These Atoms can occur severl times and therefore are stored as list in self._Atoms_
        self._CMDStructure_ = {1 : ['H'], 2 : ['L'], 3 : ['B'], 4 : ['H'], 5 : ['L'], 6 : ['B'], 7 : ['H'], 8 : ['HH'], 9 : ['', 'B', 'H'], 10 : ['HH'], 11 : ['', 'B', 'L'], 12 : ['H', 'B', 'H'], 13 : ['HHH'], 15 : ['H', 'B', 'H'], 16 : [''], 17 : ['B'], 18 : ['Bff'], 23 : ['', 'B', 'H'], 24 : ['', 'B', 'HH'], 25 : ['HH'], 26 : ['', 'B', 'H'], 27 : ['', 'B', 'HH'], 28 : ['HH'], 29 : ['', 'B', 'H'], 30 : ['', 'B', 'HH'], 31 : ['HH'], 32 : ['', 'B', 'c'], 33 : ['', 'H', 'c'], 34 : ['', 'L', 'c']}
        self._CMDStructLen_ = {1 : [2], 2 : [4], 3 : [1], 4 : [2], 5 : [4], 6 : [1], 7 : [2], 8 : [4], 9 : [0, 1, 2], 10 : [4], 11 : [0, 1, 4], 12 : [2, 1, 2], 13 : [6], 15 : [2, 1, 2], 16 : [0], 17 : [1], 18 : [9], 23 : [0, 1, 2], 24 : [0, 1, 4], 25 : [4], 26 : [0, 1, 2], 27 : [0, 1, 4], 28 : [4], 29 : [0, 1, 2], 30 :  [0, 1, 4], 31 : [4], 32 : [0, 1, 1], 33 : [0, 2, 1], 34 : [0, 4, 1]}
        self.FileHash = "" #Hash value of dsf file read
        self.CMDS = [] #unpacked commands
        self.Patches = [] #mesh patches, list of objects of class XPLNEpatch
        self.V = [] # 3 dimensional list of all vertices whith V[PoolID][Vertex][xyz etc coordinates]
        self.V32 = [] # same as V but for 32-bit coordinates
        self.Scalings = [] # 3 dimensional list of all scale multipliers and offsets for all pools and planes with Scalings[PoolID][coordinate Plane][m / o]
        self.Scal32 = [] # same as Scalings but for vertices with 32-bit coordinates
        self.Raster = [] #raster layers of file
        self.Polygons = [] #for each Polygon Definition (same order as in DefPolygon) a list of PoolId, CommandData values of Polygon
        self.Objects = [] #for each Object Definition (same order as in DefObjects) a list of PoolId, CommandData values of Polygon
        self.Networks = [] #list of network junks where in first positions road subtype, Junction offset, PoolIndex are stored, following by commands for these settings
        self.Properties = {} #dictionary containing the properties of the dsf file stored in HEAD -> PROP
        self.DefTerrains = {} #dictionary containing for each index number (0 to n-1) the name of Terrain definition file
        self.DefObjects = {}  #dictionary containing for each index number (0 to n-1) the name of Object definition file
        self.DefPolygons = {}  #dictionary containing for each index number (0 to n-1) the name of Polygon definition file
        self.DefNetworks = {}  #dictionary containing for each index number (0 to n-1) the name of Network definition file; actually just one file per dsf-file
        self.DefRasters = {}   #dictionary containing for each index number (0 to n-1) the name of Raster definition (for the moment assuing "elevaiton" is first with index 0)
        self._log_.info("Class XPLNEDSF initialized.")

    def _setLogger_(self, logname):
        if logname == '__XPLNEDSF__': #define default logger if nothing is set
            logger = getLogger('XPLNEDSF')
            logger.setLevel('INFO')
            logger.handlers = []  # Spyder/IPython currently does not remove existing loggers, this does the job
            stream_handler = StreamHandler()
            stream_handler.setLevel('INFO')
            formatter = Formatter('%(levelname)s: %(message)s')
            stream_handler.setFormatter(formatter)
            logger.addHandler(stream_handler)
        else:
            logger = getLogger(logname + '.' + __name__) #use name of existing Logger in calling module to get logs in according format or change basicConfig for logs
        return logger

    def _updateProgress_(self, bytes): #updates progress with number of read/written bytes and calls show-function
        self._progress_[1] += bytes
        if self._progress_[2] <= 0:
            return 1 #size to be reached not set; no sense to track progress
        currentprogress = round(100 * self._progress_[1] / self._progress_[2])
        if currentprogress:
            self._progress_[0] += currentprogress
            if self._progress_[0] > 100:
                self._progress_[0] = 100 #stopp at 100%
                self._progress_[1] = 0
            else:
                self._progress_[1] -= int (currentprogress * self._progress_[2] / 100)
            if self._statusfunction_ == "stdout":
                print ('[{}%]'.format(self._progress_[0]), end='', flush = True)
            elif self._statusfunction_ != None:
                self._statusfunction_(self._progress_[0])
    
    
    def _TopAtomLength_(self, id): #calculates the lengthe of an AtomOfAtoms with name id including all sub-atoms
        l = 0
        for sub_id in self._AtomStructure_[id]:
            if sub_id in self._MultiAtoms_:
                if sub_id in self._Atoms_: #check that sub-atom is really present 
                    for a in self._Atoms_[sub_id]: #for multiple atoms we have to add length of each instance
                        l += len(a) + 8  # add 8 bytes for each AtomID + Length header
            else: #for single atoms just lengths of atom
                l += len(self._Atoms_[sub_id]) + 8 # add 8 bytes for AtomID + Length header
        return l + 8  # add 8 for header of TopAtom itself

    
    def _GetStrings_(self, atom): #Returning a list of strings packed in a string table atom
        l = []
        i = 0
        while i < len(atom):
            j = i
            while atom[j] != 0 and j < len(atom):
                j += 1
            l.append(atom[i:j].decode("utf-8"))
            i = j + 1
        return l
    
    def _PutStrings_(self, d): #encodes strings in dictionary d to binary to be stored in updated atom   ########## NEW 5 #############
        b = b'' #binary encoding to be returned
        for i in range(len(d)):
            b += d[i].encode("utf-8")
            b += b'\x00'
        return b
            
            
    def _extractProps_(self): #extracts the properties of the dsf file stored in atom PROP within atom HEAD; stores them to dictionary Properties
        l = self._GetStrings_(self._Atoms_['PORP'])
        for i in range(0, len(l), 2):
            self.Properties[l[i]] = l[i+1] #the list contains property(dictionary key) and values one after each other
            
    def _encodeProps_(self): #encodes the properties of the dsf and stores them in PORP atom
        b = b'' #binary encoding to be stored in PORP
        for prop in self.Properties:
            b += prop.encode("utf-8")
            b += b'\x00'
            b += self.Properties[prop].encode("utf-8")
            b += b'\x00'
        self._Atoms_['PORP'] = b

     
    def _extractDefs_(self): #extracts the definition (DEFN) atoms TERT, OBJT, POLY, NETW, DEMN and stores them in dictionarys
        l = self._GetStrings_(self._Atoms_['TRET'])
        self.DefTerrains = dict(zip(range(len(l)), l))
        l = self._GetStrings_(self._Atoms_['TJBO'])
        self.DefObjects = dict(zip(range(len(l)), l))
        l = self._GetStrings_(self._Atoms_['YLOP'])
        self.DefPolygons = dict(zip(range(len(l)), l))
        l = self._GetStrings_(self._Atoms_['WTEN'])
        self.DefNetworks = dict(zip(range(len(l)), l))        
        l = self._GetStrings_(self._Atoms_['NMED'])
        self.DefRasters = dict(zip(range(len(l)), l))
        self._updateProgress_(self._TopAtomLength_('NFED'))

        
    def _encodeDefs_(self): #encodes the definition dictionaries in dsf object to (DEFN) atoms     
        self._Atoms_['TRET'] = self._PutStrings_(self.DefTerrains)
        self._Atoms_['TJBO'] = self._PutStrings_(self.DefObjects)
        self._Atoms_['YLOP'] = self._PutStrings_(self.DefPolygons)
        self._Atoms_['WTEN'] = self._PutStrings_(self.DefNetworks)
        self._Atoms_['NMED'] = self._PutStrings_(self.DefRasters)


        
    def _extractPools_(self, bit = 16):  
        if bit == 32:
            self._log_.info("Start to unpack and extract {} pools ({} bit)...".format(len(self._Atoms_['23OP']), bit))
            atomstring = self._Atoms_['23OP']
            V = self.V32
            ctype = "<L"
            size = 4 #bytes read per coordinate in 32 bit pool
            max_int = 4294967296
        else: #assuming the standard 16bit Pool case
            self._log_.info("Start to unpack and extract {} pools ({} bit)...".format(len(self._Atoms_['LOOP']), bit))
            atomstring = self._Atoms_['LOOP']
            V = self.V
            ctype = "<H"
            size = 2 #bytes read per coordinate in 16 bit pool
            max_int = 65536
        for s in atomstring: #goes through all Pools read; string s has to be unpacked
            nArrays, nPlanes = unpack('<IB', s[0:5])
            if self._DEBUG_: self._log_.debug("Pool number {} has {} Arrays (vertices) with {} Planes (coordinates per vertex)!".format(len(V), nArrays, nPlanes))
            V.append([]) #the current pool starts empty
            for i in range(nArrays): ## span up multi-dimensional array for the new pool of required size (number of vertices in pool)
                V[-1].append([])
            pos = 5 #position in string s
            for n in range(nPlanes):
                encType, = unpack('<B', s[pos : pos + 1])
                pos += 1
                if self._DEBUG_: self._log_.debug("Plane {} is encoded: {}".format(n, encType))
                if encType < 0 or encType > 3: #encoding not defined
                    self._log_.error("Stopp reading pool because not known encoding of plane found!!!")
                    return [] ##This means we return empty pool, which can be used to detect error        
                i = 0  #counts how many arrays = vertices have been read in plane n
                while i < nArrays:
                    if encType >= 2: #this means data is run-length encoded
                        runLength, = unpack('<B', s[pos : pos + 1])
                        pos += 1
                    else: #no run-length encoding (not tested yet!!!!!)
                        runLength = 1 #just read single values until end of this plane  
                    if runLength > 127: #means the following value is repeated
                        v, = unpack(ctype, s[pos : pos + size]) #repeated value
                        pos += size
                        runLength -= 128 #only value without 8th bit gives now the number of repetitions
                        while runLength > 0:
                            V[-1][i].append(v)
                            runLength -= 1
                            i += 1
                    else:
                        while runLength > 0: #now just reading individual values
                            v, = unpack(ctype, s[pos : pos + size])
                            pos += size
                            V[-1][i].append(v)
                            runLength -= 1
                            i += 1
                if encType == 1 or encType == 3: #values are also stored differenced
                    for i in range (1, nArrays):  
                        V[-1][i][n] = (V[-1][i][n] + V[-1][i-1][n]) % max_int  #undo differntiation and modulo for wrapping two byte unsigned integer
                                                         ##### NEW TBD #### FOR 32 Bit Pools adapt Moduls ??!! #################### NEW TBD ######################## NEW TBD ########
            self._updateProgress_(len(s))


    def _encodeRunLength_(self, l):  # yields runlength encoded value pairs of list l
        count = 1 #counting repetitions
        prev = l[0] #the previous value in list starts with first value in the list
        l.append('_END_') #as end of list symbol
        individuals = [] #list of individual values (non repeating ones)
        for value in l[1:]:
            if value != prev or count == 127: #non repeating value or maximum of repeating values reached
                if len(individuals) == 127:  #if maximum length of indivdiual values is reached
                    yield(len(individuals),individuals)
                    individuals = []
                if count > 1:  #we have now repeating values
                    if len(individuals): #individual values before have to be returned if existent
                        yield(len(individuals), individuals) 
                    yield(count + 128, [prev]) #now return the repeating values with highest bit (128) set of byte
                    individuals = []
                else: #non repeating values, so add previous to the individuals
                    individuals.append(prev)
                count = 0
            prev = value
            count += 1
        if len(individuals): #return still existing values in list
            yield(len(individuals), individuals)
        
    
    def _encodePools_(self, bit = 16): #overwrites current 16 (default) or 32 bit Pool atom with actual values of all vertices
        if bit == 32:
            atom = '23OP'
            V = self.V32
            ctype = "<L"
            max_int = 4294967296
        else: #assuming the standard 16bit Pool case
            atom = 'LOOP'
            V = self.V
            ctype = "<H"
            max_int = 65536            
        self._log_.info("Start to encode {}  {}bit pools... (read values of vertices are overwritten)".format(len(V), bit))
        self._Atoms_[atom] = [] #start new (future version also think of creating Pool atom in case it new dsf file will be created !!!!!!!!!!)
        ####### This version only stores pools in differentiated run-length encoding !!! #############
        ## Start with differentiation of all values ##
        for p in V: # go through all pools
            if len(p) == 0: #some standard dsf files have empty pools, keep them
                self._log_.info("Empty pool number {} encoded.".format(V.index(p)))
                encpool = pack("<IB",0,0) #pool has no vertices with no planes (is empty)
                self._Atoms_[atom].append(encpool)
                continue
            encpool = bytearray() ### NEW ###
            encpool.extend(pack("<IB",len(p),len(p[0]))) ### NEW ###  ## start string of binary encoded pool number of arrays and number of planes (taken from first vertex)
            #encpool = pack("<IB",len(p),len(p[0])) ## start string of binary encoded pool number of arrays and number of planes (taken from first vertex)
            for n in range(len(p[0])): # go through all planes; number of planes just taken from first vertex in pool
                #if atom=="23OP": self._log_.info("Encoding plane: {}".format(n)) ###### ERROR 32 bit pool checking ####################
                plane = [p[0][n]] #set plane to first value (for starts with second value to calculete differences)
                for i in range(1, len(p)): #go through all values of a plane for differntiation and append to current plane
                    plane.append((p[i][n] - p[i-1][n]) % max_int)  #Calculate difference to previous value AND take care of wrapping for two byte unsigned integer
                #encpool += pack('<B',3) #plane will be encoded differntiated + runlength
                encpool.extend(pack('<B',3)) #### NEW ### #plane will be encoded differntiated + runlength
                if p[0][n] < 0:  #### NEW 4.3 #####
                    self._log_.warning("In pool {} negative value {} to be encoded. Set to 0.".format(self.V.index(p), p[0][n]))   
                    p[0][n] = 0
                if p[0][n] >= max_int: #### NEW 4.3 #####
                    self._log_.warning("In pool {} exceeding value {}  to be encoded. Set to {}.".format(self.V.index(p), p[0][n], max_int-1))
                    p[0][n] = max_int - 1 
                pack(ctype,p[0][n])  ########### WHAT IS THIS FOR ??? ################
                ## Now perform run-length encoding ##
                #encdata = bytearray() ##### NEW ####
                #encdata.extend(encpool) #### NEW ####
                for rlpair in self._encodeRunLength_(plane):
                    #encpool += pack('<B', rlpair[0]) #encode runlength value  ### OLD ###
                    encpool.extend(pack('<B', rlpair[0]))  ### NEW ###
                    for v in rlpair[1]:
                        if v < 0:   #### NEW 4.3 #####
                            self._log_.warning("In pool {} negative value {} to be encoded. Set to 0.".format(self.V.index(p), v))  
                            v = 0
                        if v >= max_int: #### NEW 4.3 #####
                            self._log_.warning("In pool {} exceeding value {}  to be encoded. Set to {}.".format(self.V.index(p), v, max_int-1))
                            v = max_int - 1                               
                        #encpool += pack(ctype, v)  ### OLD ###
                        encpool.extend(pack(ctype, v)) ##### NEW ###
            self._updateProgress_(len(encpool))  
            self._Atoms_[atom].append(encpool)   
        self._log_.info("Encoding of {} bit pools finished.".format(bit))
 

    def _extractScalings_(self, bit = 16): #extract scaling values from atoms and writes them to according lists
        self._log_.info("Start to unpack and extract all saclings of {} bit pools.".format(bit))
        if bit == 32:
            atomstring = self._Atoms_['23CS']
            Scalings = self.Scal32
        else: #assuming the standard 16bit Pool case
            atomstring = self._Atoms_['LACS']
            Scalings = self.Scalings
        for s in atomstring: #goes through all Scalings read; string s has to be unpacked
            Scalings.append([]) #new scaling entry for next pool   
            for i in range(int(len(s) / 8) ):  #for each scaling tuple - 4 bytes multiplier and 4 bytes offset
                m, o = unpack('<ff', s[ i*8 : i*8 + 8] )  #retrieve multiplier and offset
                Scalings[-1].append([m, o])

    def _packAllScalings_(self): #packs the all Scalings incl. Scal32 values to binary atom strings to be later written to file 
        self._log_.info("Start to pack all scalings for pools.")
        self._Atoms_['LACS'] = []
        self._Atoms_['23CS'] = []
        for s in self.Scalings:
            encscal = b''
            for i in s:
                encscal += pack('<ff', i[0], i[1])
            self._Atoms_['LACS'].append(encscal)
        for s in self.Scal32:
            encscal = b''
            for i in s:
                encscal += pack('<ff', i[0], i[1])
            self._Atoms_['23CS'].append(encscal)                    

                
    def _scaleV_(self, bit = 16, reverse = False): #applies scaling to the vertices stored in V and V32
        if reverse:
            self._log_.info("Start to de-scale all {} bit pools.".format(bit))
        else:
            self._log_.info("Start to scale all {} bit pools.".format(bit))
        if bit == 32:
            V = self.V32
            Scalings = self.Scal32
            max_int = 4294967296 - 1 
        else: #assuming the standard 16bit Pool case
            V = self.V
            Scalings = self.Scalings
            max_int = 65536 - 1
            
        if len(V) != len(Scalings):
            self._log_.error("Amount of Scale atoms does not equal amount of Pools!!")
            return 1
        for p in range(len(V)): #for all Pools
            if V[p] == []: ###There can exist empty pools that have to be skipped for scaling!!!
                self._log_.info("Empty pool number {} not scaled!".format(p))
                break
            if len(V[p][0]) != len(Scalings[p]): #take first vertex as example to determine number of coordinate planes in current pool
                self._log_.error("Amount of scale values for pool {} does not equal the number of coordinate planes!!!".format(p))
                return 2
            for n in range(len(Scalings[p])): #for all scale tuples for that pool = all coordinate planes in pool
                if self._DEBUG_: self._log_.debug("Will now scale pool {} plane {} with multiplier: {} and offset: {}".format(p, n ,Scalings[p][n][0], Scalings[p][n][1]))                              
                if float(Scalings[p][n][0]) == 0.0:
                    if self._DEBUG_: self._log_.debug("   Plane will not be scaled because scale is 0!")
                    break
                for v in range(len(V[p])): #for all vertices in current plane
                    if reverse: #de-scale vertices
                        V[p][v][n] = round((V[p][v][n] - Scalings[p][n][1]) * max_int / Scalings[p][n][0])   #de-scale vertex v in pool p for plane n by subtracting offset and dividing by multiplyer
                    else:  #scale vertices
                        V[p][v][n] = (V[p][v][n] * Scalings[p][n][0] / max_int) + Scalings[p][n][1]  #scale vertex v in pool p for plane n with multiplyer and offset
               
                
    def _extractRaster_(self):  #extracts alll rasters from atoms and stores them in list
        self._log_.info("Extracting {} raster layers...".format(len(self._Atoms_['IMED'])))
        if len(self._Atoms_['IMED']) != len(self._Atoms_['DMED']):
            self._log_.error("Number of raster info atoms not equal to number of raster data atoms!!!")
            return 1           
        for rn in range(len(self._Atoms_['IMED'])):
            R = XPLNEraster()
            R.ver, R.bpp, R.flags, R.width, R.height, R.scale, R.offset = unpack('<BBHLLff', self._Atoms_['IMED'][rn])
            #if self._DEBUG_: self._log_.debug("Info of new raster layer: {} {} {} {} {} {} {}".format(R.ver, R.bpp, R.flags, R.width, R.height, R.scale, R.offset))
            self._log_.info("Info of new raster layer: {} {} {} {} {} {} {}".format(R.ver, R.bpp, R.flags, R.width, R.height, R.scale, R.offset))
            if R.flags & 1:  #signed integers to be read
                if R.bpp == 1:
                    ctype = "<b"
                elif R.bpp == 2:  ##### this is the only case tested so far !!!!!!!
                    ctype = "<h"
                elif R.bpp == 4:
                    ctype = "<i"
                else:
                    self._log_.error("Not allowed bytes per pixel in Raster Definition!!!")
                    return 2
            elif R.flags & 2: #unsigned integers to be read
                if R.bpp == 1:
                    ctype = "<B"
                elif R.bpp == 2:
                    ctype = "<H"
                elif R.bpp == 4:
                    ctype = "<I"
                else:
                    self._log_.error("Not allowed bytes per pixel in Raster Definition!!!")
                    return 3
            elif not (R.flags & 1) and not (R.flags & 2): #neither first nor second bit set means that 4 byte float has to be read
                if R.bpp == 4:
                    ctype ="<f"
                else:
                    self._log_.error("Not allowed bytes per pixel in Raster Definition!!!")
                    return 4

            for x in range(0, R.bpp * R.width, R.bpp): #going x-wise from east to west just the bytes per pixes
                line = []
                for y in range(0, R.bpp * R.height * R.width, R.bpp * R.width): #going y-wise from south to north, always jumping over the width of each x-line
                    v, = unpack(ctype, self._Atoms_['DMED'][rn][y + x : y + x + R.bpp]) #unpack R.bpp bytes at position x+y of raster data atom number rn
                    v = v * R.scale + R.offset # APPLYING SCALE + OFFSET 
                    line.append(v) #the pixel appended is to a line from south to north (y-line)
                R.data.append(line) #south to north lines are appended to each other
                self._updateProgress_(R.bpp * R.width) #update progress with number of bytes per raster line
            self.Raster.append(R) #so raster list of list is returned to be indexed by [x][y]
        self._log_.info("Finished extracting Rasters.")
   
   
    def _packRaster_(self):  #packs all rasters from lists into atoms
        self._log_.info("Packing {} raster layers...".format(len(self.Raster)))
        self._Atoms_['DMED'] = []
        self._Atoms_['IMED'] = []
        for rn in range(len(self.Raster)):
            R = self.Raster[rn]
            encrasterinfo  = pack('<BBHLLff', R.ver, R.bpp, R.flags, R.width, R.height, R.scale, R.offset)
            self._Atoms_['IMED'].append(encrasterinfo)
            #if self._DEBUG_: self._log_.debug("Info of packed raster layer: {} {} {} {} {} {} {}".format(R.ver, R.bpp, R.flags, R.width, R.height, R.scale, R.offset))
            self._log_.info("Info of packed raster layer: {} {} {} {} {} {} {}".format(R.ver, R.bpp, R.flags, R.width, R.height, R.scale, R.offset))
            if R.flags & 1:  #signed integers to be read
                if R.bpp == 1:
                    ctype = "<b"
                elif R.bpp == 2:  ##### this is the only case tested so far !!!!!!!
                    ctype = "<h"
                elif R.bpp == 4:
                    ctype = "<i"
                else:
                    self._log_.error("Not allowed bytes per pixel in Raster Definition!!!")
                    return 2
            elif R.flags & 2: #unsigned integers to be read
                if R.bpp == 1:
                    ctype = "<B"
                elif R.bpp == 2:
                    ctype = "<H"
                elif R.bpp == 4:
                    ctype = "<I"
                else:
                    self._log_.error("Not allowed bytes per pixel in Raster Definition!!!")
                    return 3
            elif not (R.flags & 1) and not (R.flags & 2): #neither first nor second bit set means that 4 byte float has to be read
                if R.bpp == 4:
                    ctype ="<f"
                else:
                    self._log_.error("Not allowed bytes per pixel in Raster Definition!!!")
                    return 4
                
            encdata = bytearray()

            for y in range(R.height): #going x-wise from east to west just the bytes per pixes ################# YYYYYYY
                line = b'' #current encoded bytes just for one line; this is quick enough wiht +=, then extend lines to encdata
                for x in range(R.width): #going y-wise from south to north, always jumping over the width of each x-line ################## XXXXXX
                    #v = R.data[x][y] / R.scale - R.offset # APPLYING SCALE + OFFSET to raster elevation at position x, y
                    v = (R.data[x][y] - R.offset) / R.scale # APPLYING SCALE + OFFSET to raster elevation at position x, y  ## corrected 26.04.2020
                    if R.flags & 1 or R.flags & 2: #integers to be read
                        v = int(v)
                        if ctype == '<H': ##  check here out of bound values  ###### NEW 26.04.2020 ######
                            if v < 0:
                                self._log_.error("Raster elevation at position {} {} is negative: {} ({})---> set to 0".format(x, y, v, ctype))
                                v = 0
                            if v > 65535:
                                self._log_.error("Raster elevation at position {} {} is above 65535: {} ({}) ---> set to 65535".format(x, y, v, ctype))
                                v = 65535
                        if ctype == '<h': ##  check here out of bound values  ###### NEW 26.04.2020 ######
                            if v < -32768:
                                self._log_.error("Raster elevation at position {} {} is below -32768: {} ({})---> set to -32768".format(x, y, v, ctype))
                                v = -32768
                            if v > 32767:
                                self._log_.error("Raster elevation at position {} {} is above 32767: {} ({}) ---> set to 32767".format(x, y, v, ctype))
                                v = 32767
                    ##### TBD: check if v is not negative for signed integer and if size for packing is according....
                    line += pack(ctype, v) #pack bytes for position x, y of raster
                encdata.extend(line)
                self._updateProgress_(R.bpp * R.width) #update progress with number of bytes per raster line
                #self._log_.info("Raster line {} encoded".format(x))
            #self._log_.info("Last Raster line encoded: {}".format(line))
            self._Atoms_['DMED'].append(encdata) #raster data for raster number rn added to atom
        self._log_.info("Finished packing Rasters.")   
   
   
    def _unpackCMDS_(self):
        i = 0 #position in CMDS String
        self._log_.info("Start unpacking of Commands.")
        current100kBjunk = 1 #counts processed bytes in 100kB junks
        while i < len(self._Atoms_['SDMC']):
            id, = unpack('<B', self._Atoms_['SDMC'][i : i+1])
            self.CMDS.append([id])
            i += 1
            if id in self._CMDStructure_:
                l = self._CMDStructLen_[id][0] #length of bytes to read
                if l > 0:
                    y = unpack('<' + self._CMDStructure_[id][0], self._Atoms_['SDMC'][i : i + l])
                    self.CMDS[-1].extend(y)
                    i += l
                if len(self._CMDStructLen_[id]) == 3: #read command with variable length
                    l = self._CMDStructLen_[id][1] #length of repeating value n to read
                    n, = unpack('<' + self._CMDStructure_[id][1], self._Atoms_['SDMC'][i : i + l]) #number n of repetitions
                    if id == 15:
                        n += 1 #id = 15 seems a special case that there is one index more than windings  ########??????????
                    i += l
                    l = self._CMDStructLen_[id][2] #length of repeated bytes
                    for j in range(n): 
                       y = unpack('<' + self._CMDStructure_[id][2], self._Atoms_['SDMC'][i : i + l])
                       self.CMDS[-1].extend(y)
                       i += l
            else:
                if id == 14: #special double packed case, which is explicetly treated separate and has special format returning lists inside commands !!!
                             ###### not tested yet !!!!!!!! ########
                    parameter, windings = unpack('<HB', self._Atoms_['SDMC'][i : i + 3])
                    i += 3
                    self.CMDS[-1].extend(parameter)
                    for w in range(windings):
                        indices, = unpack('<B', self._Atoms_['SDMC'][i : i + 1])
                        i += 1
                        windinglist = []
                        for m in range(indices):
                            y, = unpack('<H', self._Atoms_['SDMC'][i : i + 2])
                            i += 2
                            windinglist.extend(y)
                        self.CMDS[-1].append(windinglist)
                else: #command id not tretated here until now
                    self._log_.warning("Unknown command ID {} ignored!".format(id))
                    self.CMDS[-1] #delete already written id
            if self._DEBUG_: self._log_.debug("CMD id {}: {} (string pos next cmd: {})".format(self.CMDS[-1][0], self.CMDS[-1][1:], i))
            if i > current100kBjunk * 100000:
                self._updateProgress_(50000) #count only half of the length, other half by extractCMDS
                current100kBjunk += 1
        self._log_.info("{} commands haven been unpacked.".format(len(self.CMDS)))


    def _extractCMDS_(self): # extract CMDS and stores it as Mesh-Patches, Polygons, ...
        self._log_.info("Start to extract CMDS")
        for i in range(len(self.DefPolygons)):
            self.Polygons.append([]) #span list of empty lists for all defined poygon types
        for i in range(len(self.DefObjects)): 
            self.Objects.append([]) #span list of empty lists for all defined poygon types

        patchPoolIndex = None #poolIndex currently used in current patch; if different from current in CMDS then change command is written to cmds of patch

        flag_physical = None #1 if physical, 2 if overlay
        nearLOD = None  
        farLOD = None
        poolIndex = 0
        defIndex = 0
        subroadtype = 0
        junctionoffset = 0
        counter = 0
        amount_of_two_percent_CMDS = int(len(self.CMDS)/50)  ### NEW ###
        if amount_of_two_percent_CMDS == 0:                  ### NEW ###
            amount_of_two_percent_CMDS = 1 #have 1 as minimal value in order to avoid devision by zero below   ### NEW ###
        for c in self.CMDS:
            if c[0] == 1: # new pool selection
                poolIndex = c[1]
            elif c[0] == 2: # new junction offset
                junctionoffset = c[1]
            elif 3 <= c[0] <= 5: # new definition index
                defIndex = c[1]
            elif c[0] == 6: # new subtype for road
                subroadtype = c[1]
            elif 7 <= c[0] <= 8: #Object Command
                self.Objects[defIndex].append([poolIndex]) #new Polygond added for defIndex type and it starts with poolIndex from which its vertices are
                self.Objects[defIndex][-1].extend(c) #followed by the complete command to build it
            elif 9 <= c[0] <= 11: #Network Commands ### NEW: each Network command put in sublists, addtional [] inclueded !!!! 
                if self.Networks == []: #first network command, so start with first entry
                    self.Networks.append([[subroadtype, junctionoffset, poolIndex]])
                elif self.Networks[-1][0][0] != subroadtype or self.Networks[-1][0][1] != junctionoffset or self.Networks[-1][0][2] != poolIndex: #chang of relevant base settings
                    self.Networks.append([[subroadtype, junctionoffset, poolIndex]]) #sp new entry with new base-settings
                self.Networks[-1].extend([c]) #append complete command to build this network part on current base settings
            elif 12 <= c[0] <= 15: #Polygon Commands
                self.Polygons[defIndex].append([poolIndex]) #new Polygond added for defIndex type and it starts with poolIndex from which its vertices are
                self.Polygons[defIndex][-1].extend(c) #followed by the complete command to build it
            elif 16 <= c[0] <= 18:  # Add new Terrain Patch
                patchPoolIndex = None #poolIndex for new patch needs to be set as first command
                if c[0] == 17: # New Patch with new physical flag
                    flag_physical = c[1]
                elif c[0] == 18: # New Patch with new flag and LOD
                    flag_physical = c[1]
                    nearLOD = c[2]
                    farLOD = c[3]    
                p = XPLNEpatch(flag_physical, nearLOD, farLOD, poolIndex, defIndex)
                self.Patches.append(p)
            elif c[0] >= 23 and c[0] <= 31: # the command is about a patch, so store it to current patch
                if patchPoolIndex != poolIndex: #change of pool index within patch is possible
                    self.Patches[-1].cmds.append( [1, poolIndex] ) #change pool with patch via according command
                    patchPoolIndex = poolIndex #now within patch also current pool will be used
                if self.Patches[-1].defIndex != defIndex:
                    self._log_.error("Definition Index changed within patch. Aborted command extraction!")
                    return 1
                self.Patches[-1].cmds.append(c) 
            counter += 1
            if not counter % amount_of_two_percent_CMDS: #after every 2% processed of commands update progress  --> RAISES ERROR when less than 50 CMDS
                self._updateProgress_(round(len(self._Atoms_['SDMC']) / 100)) #count only half of the length, other half by unpackCMDS
        self._log_.info("{} patches extracted from commands.".format(len(self.Patches)))
        self._log_.info("{} different Polygon types including there definitions extracted from commands.".format(len(self.Polygons)))
        self._log_.info("{} different Objects with placements coordinates extracted from commands.".format(len(self.Objects)))
        self._log_.info("{} different Network subtypes extracted from commands (could include double count).".format(len(self.Networks)))

    def _packCMDS_(self): #packs all CMDS of Object, Polygons, Networks and Patches in binary string to be later written to file #####NEW FUCTION### NEW ####
        ################################# TBD: Check function for polygons and object placements !!!!!! #############################################################
        self._log_.info("Start to pack CMDS")   #### NEW 4 : put definition of variables befor encCMD function, as values like poolIndex will be changed inside ##############
        #SET state variables
        flag_physical = None
        nearLOD = None  
        farLOD = None
        poolIndex = None
        defIndex = None
        subroadtype = None
        junctionoffset = None  #### set to 0 if directly set below as in X-Plane standard dsf files
        enccmds = bytearray() #these will be the encoded CMDS to be returned  
        ### local function for single CMD encoding ###
        def encCMD(c): #encodes single CMD in array c and returns its binary
            ecmd = b'' 
            id = c[0] #id of CMD stored as first value in list
            if id == 3 and c[1] > 255: #avoid errors if definition is too big for command id 3
                id = 4
            if id == 4 and c[1] > 65535: #avoid errors if definition is too big for command id 4
                id = 5
            ecmd += pack('<B', id) #encode CMD id
            i = 1 #index in value list to be packed
            if id in self._CMDStructure_: 
                for valtype in self._CMDStructure_[id][0]: #pack fixed length values of CMD
                    ecmd += pack('<' + valtype, c[i])
                    i += 1
                if len(self._CMDStructLen_[id]) == 3: #pack command with variable length 
                    vlength = int( (len(c) - i) / len(self._CMDStructure_[id][2]) ) #fixed values inclding CMD id are counting not for the variable length, so minus i #### TBD: Test that this value does not exceed 255!!!!!! ####
                    if vlength > 255: #make sure that length is not longer than could be encoded in one byte
                        self._log_.error("Length of CMD with id {} and length {} does exceed 255 and will not be included!!!".format(id, vlength))
                        return b''
                    if id == 15:
                        vlength -= 1 #id = 15 seems a special case that there is one index more than windings 
                    ecmd += pack('<B', vlength) #count packed
                    while i < len(c): #now pack the variable length value list
                        for valtype in self._CMDStructure_[id][2]: #pack fixed length individual value
                            if valtype=='H' and (c[i]<0 or c[i]>65535):
                                self._log_.error("Trying to pack value {} at position {} in command id {} as unsignded short. Skipped. DSF will not work!!!".format(c[i], i, id))
                            else:
                                ecmd += pack('<' + valtype, c[i])
                            i += 1
            else:
                ######### TBD: include special code for CMD 14 here!!! ########## TBD ########### TBD ########### TBD ########### TBD ############### TBD ###########
                self._log_.error("CMD id {} is not supported (CMD 14 not implemented yet)! Will be skipped!!".format(id))
                return b''
            return ecmd
        ### end of inner function to pack single CMDS ###   
        for d in self.DefObjects: #for each object definition write according CMDS
            enccmds.extend(encCMD([3, d])) #definition set according to current definition id; function will handle if id > 255
            for c in self.Objects[d]:
                if c[0] != poolIndex: #Pool-Index is written before CMD; adapt index if it changes
                    enccmds.extend(encCMD([1, c[0]]))
                    poolIndex = c[0]
                enccmds.extend(encCMD(c[1:])) #now according command to place objects is encoded  #### TO BE TESTED if it works as part of array???????
        for d in self.DefPolygons: #for each polygon definition write according CMDS
            enccmds.extend(encCMD([3, d])) #definition set according to current definition id; function will handle if id > 255
            for c in self.Polygons[d]:
                if c[0] != poolIndex: #Pool-Index is written before CMD; adapt index if it changes
                    enccmds.extend(encCMD( [1, c[0]] ))
                    poolIndex = c[0]
                enccmds.extend(encCMD(c[1:])) #now according command to place objects is encoded  #### TO BE TESTED if it works as part of array???????        
        for d in self.Networks:
            if d[0][1] != junctionoffset: ## Order in org X-Plane files is with CMD id 2 at first
                enccmds.extend(encCMD([2, d[0][1]]))
                junctionoffset = d[0][1]
            if defIndex != 0:
                enccmds.extend(encCMD([3, 0])) #Currently there is only one Road-Defintion --> DefIndex set to 0
                defIndex = 0
            if d[0][2] != poolIndex:
                enccmds.extend(encCMD([1, d[0][2]]))
                poolIndex = d[0][2]
            if d[0][0] != subroadtype:  ## Order in org X-Plane files is with 6 at last
                enccmds.extend(encCMD([6, d[0][0]]))
                subroadtype = d[0][0]
            for c in d[1:]:
                enccmds.extend(encCMD(c))
        for d in self.Patches:
            if defIndex != d.defIndex:
                enccmds.extend(encCMD([3, d.defIndex])) #definition set according to current definition id; function will handle if id > 255
                defIndex = d.defIndex
            if poolIndex != d.cmds[0][1]: #Pool-Index is defined by first command and required to be defined directly before new Patch is defined!    
                enccmds.extend(encCMD([1, d.cmds[0][1]])) #include command for changing poolIndex
                poolIndex = d.cmds[0][1] #update state variable
            if nearLOD == d.near and farLOD == d.far:
                if flag_physical == d.flag:
                    enccmds.extend(encCMD([16]))
                else:
                    enccmds.extend(encCMD([17, d.flag]))
                    flag_physical = d.flag
            else:
                enccmds.extend(encCMD([18, d.flag, d.near, d.far]))
                farLOD = d.far
                nearLOD = d.near
                flag_physical = d.flag
            for c in d.cmds[1:]:   ##skip first command as this is pool defintion written above
                enccmds.extend(encCMD(c))
                if c[0] == 1: #change of poolIndex can happen within patch commands    
                    poolIndex = c[1] #therefore also state variable has to be adapted        
        self._Atoms_['SDMC'] = enccmds #Commands Atom now set to the now packed CMDS
        self._log_.info("Ended to pack CMDS")
 ########### END of NEW function _packCMDS_() #################               
                

    def _unpackAtoms_(self): #starts all functions to unpack and extract data froms strings in Atoms
        self._log_.info("Extracting properties and definitions.")
        if 'PORP' in self._Atoms_:
            self._extractProps_()
        else:
            self._log_.error("This dsf file has no properties defined!")
        if 'NFED' in self._Atoms_:    
            self._extractDefs_()
        else:
            self._log_.warning("This dsf file has no definitions.") 
        if 'IMED' in self._Atoms_:
            self._extractRaster_()
        else:
            self._log_.info("This dsf file has no raster layers.")
        if 'LOOP' in self._Atoms_:
            self._extractPools_(16)
            self._extractScalings_(16)
            self._scaleV_(16, False) #False that scaling is not reversed
            self._updateProgress_(len(self._Atoms_['LACS']))
        else:
            self._log_.warning("This dsf file has no coordinate pools (16-bit) defined!") 
        if '23OP' in self._Atoms_:
            self._extractPools_(32)
            self._extractScalings_(32)
            self._scaleV_(32, False) #False that scaling is not reversed
            self._updateProgress_(len(self._Atoms_['23CS']))
        else:
            self._log_.info("This dsf file has no 32-bit pools.")
        if 'SDMC' in self._Atoms_:
            self._unpackCMDS_()
            self._extractCMDS_()
        else:
            self._log_.warning("This dsf file has no commands defined.")
        return 0
        

    def _packAtoms_(self): #starts all functions to write all variables to strings (for later been written to file)
        ###### TBD: only pack atoms if changed --> saves time !! ############
        self._log_.info("Preparing data to be written to file.")
        self._log_.info("This version does not yet support nested polygons (Command ID 14)!")
        self._encodeProps_()
        self._encodeDefs_() 
        self._scaleV_(16, True) #de-scale again      
        self._scaleV_(32, True)
        self._encodePools_(16)
        self._encodePools_(32)
        self._packAllScalings_()
        self._packCMDS_()
        self._packRaster_()
        return 0
                                              
  
    def getVertexElevation(self, x, y, z = -32768): #gets Elevation at point (x,y) from raster grid Elevation or from Vertex itself if assigned to vertex
        if int(z) != -32768: #in case z vertex is different from -32768 than this is the right height and not taken from raster
            return z
        if "sim/west" not in self.Properties:
            self._log_.error("Cannot get elevation as properties like sim/west not defined!!!")
            return None
        if not (int(self.Properties["sim/west"]) <= x <= int(self.Properties["sim/east"])):
            self._log_.error("Cannot get elevation as x coordinate is not within boundaries!!!")
            return None
        if not (int(self.Properties["sim/south"]) <= y <= int(self.Properties["sim/north"])):
            self._log_.error("Cannot get elevation as y coordinate is not within boundaries!!!")
            return None
        if len(self.DefRasters) == 0: #No raster defined, use elevation from trias  #### NEW 7 ####
            self._log_.error("getVertexElevation: dsf includes no raster, elevation returned is None")
            return None
        else: # use raster to get elevation; THIS VERSION IS ASSUMING THAT ELEVATION RASTER IS THE FIRST RASTER-LAYER (index 0), if it is not called "elevation" a warning is raised ###
            if self.DefRasters[0] != "elevation":
                self._log_.warning("Warning: The first raster layer is not called elevation, but used to determine elevation!")
            x = abs(x - int(self.Properties["sim/west"])) * (self.Raster[0].width - 1) # -1 from widht required, because pixels cover also boundaries of dsf lon/lat grid
            y = abs(y - int(self.Properties["sim/south"])) * (self.Raster[0].height - 1) # -1 from height required, because pixels cover also boundaries of dsf lon/lat grid
            if self.Raster[0].flags & 4: #when bit 4 is set, then the data is stored post-centric, meaning the center of the pixel lies on the dsf-boundaries, rounding should apply
                x = round(x, 0)
                y = round(y, 0)
            x = int(x) #for point-centric, the outer edges of the pixels lie on the boundary of dsf, and just cutting to int should be right
            y = int(y)
            return self.Raster[0].data[x][y]   


    def getPolys(self, type): #returns all polygons of one type (numbered as in DefPolys) in a list and for each poly parameter following all vertices as reference [poolId, index]
        l = [] #list of polygons to be returned
        for p in self.Polygons[type]:
            l.append([p[2]]) #start a new poly which starts with its parameter
            if p[1] == 13: #POLYGON RANGE
                for i in range(p[3], p[4]):
                    l[-1].append([p[0], i])
        ####### TO INCLUDE ALSO OTHER POLYGON COMMAND IDs between 12 and 15 !!!!!!!!!!!!!!!!!!!!!!!!!!
        return l

    def BoundingRectangle(self, vertices): #returns 4-tuple of (latS, latN, lonW, lonE) building the smallest rectangle to include all vertices in list as pairs of [lon, lat]
        minx = 181  #use maximal out of bound values to be reset by real coordinates from patch
        maxx = -181
        miny = 91
        maxy = -91
        for v in vertices: #all vertexes of each triangle in patch
            if v[0] < minx:
                minx = v[0]
            if v[0] > maxx:
                maxx = v[0]
            if v[1] < miny:
                miny = v[1]
            if v[1] > maxy:
                maxy = v[1]
        return miny, maxy, minx, maxx


    def TriaVertices(self, t): #returns 3 vertices of triangle as list of [lon, lat] pairs  ############# TBD: CHECK WHERE NEEDED !!! ################
        return [  [self.V[t[0][0]][t[0][1]][0], self.V[t[0][0]][t[0][1]][1]], [self.V [t[1][0]] [t[1][1]][0], self.V[t[1][0]][t[1][1]][1]],  [self.V[t[2][0]][t[2][1]][0], self.V[t[2][0]][t[2][1]][1]] ]


    def getChains(self): #yields Chain chunks of dsf.Network
        for netel in self.Networks:
            poolid = netel[0][2]
            offset = netel[0][1] 
            for cmd in netel[1:]:
                chains = [] #list of vertex lists
                inside_chunk = False
                if cmd[0] == 10:
                    for i in range(cmd[1], cmd[2]):
                        if self.V32[poolid][i+offset][3] != 0:
                            if not inside_chunk:
                                chains.append([]) #new list for new chunk coming
                                inside_chunk = True #now we are inside the chunk
                            else:
                                inside_chunk = False #with this index we are leaving junk
                        chains[-1].append([poolid, i + offset])
                else:
                    if cmd[0] == 9:
                        offset2 = offset
                    elif cmd[0] == 11: #this command uses 32 bit coordinate indices without offset
                        offset2 = 0
                    else:
                        self._log_.error("Wrong network command id {} found!!".format(cmd[0]))
                        return
                    for i in range(1, len(cmd)): #first is command id  OPEN: if length is already in cmd[1] ?? ####### NOT TESTED YET
                        if self.V32[poolid][cmd[i]+offset2][3] != 0:
                            if not inside_chunk:
                                chains.append([]) #new list for new chunk coming
                                inside_chunk = True #now we are inside the chunk
                            else:
                                inside_chunk = False #with this index we are leaving junk
                        chains[-1].append([poolid, cmd[i] + offset2])                        
                for c in chains: #yield chains off current command
                    yield(c)
        
                    
    def read(self, file):  
        self.__init__("_keep_logger_","_keep_statusfunction_") #make sure all values are initialized again in case additional read
        if not path.isfile(file):
            self._log_.error("File does not exist!".format(file))
            return 1
        flength = stat(file).st_size #length of dsf-file   
        self._progress_ = [0, 0, flength] #initilize progress start for reading
        with open(file, "rb") as f:    ##Open Tile as binary fily for reading
            self._log_.info("Opend file {} with {} bytes.".format(file, flength))
            start = f.read(12)
            if start.startswith(b'7z\xBC\xAF\x27\x1C'):
                if PY7ZLIBINSTALLED:
                    f.seek(0)
                    archive = py7zlib.Archive7z(f)
                    filedata = archive.getmember(archive.getnames()[0]).read()
                    self._log_.info("File is 7Zip archive. Extracted and read file {} from archive with decompressed length {}.".format(archive.getnames()[0], len(filedata)))
                    f.close()
                    f = BytesIO(filedata)
                    self._progress_ = [0, 0, len(filedata)] #set progress maximum to decompressed length
                    flength = len(filedata) #also update to decompressed length
                    start = f.read(12)
                else:
                    self._log_.error("File is 7Zip encoded! py7zlib not installed to decode.")
                    return 2
            identifier, version = unpack('<8sI',start)
            if identifier.decode("utf-8") != "XPLNEDSF" or version != 1:
                self._log_.error("File is no X-Plane dsf-file Version 1 !!!")  
                return 3            
            while f.tell() < flength - 16: #read chunks until reaching last 16 bytes hash value
                bytes = f.read(8)
                atomID, atomLength = unpack('<4sI',bytes)        
                atomID = atomID.decode("utf-8")
                if atomID in self._AtomStructure_.keys():
                    if self._DEBUG_: self._log_.debug("Reading top-level atom {} with length of {} bytes.".format(atomID, atomLength))
                else:
                    if self._DEBUG_: self._log_.debug("Reading atom {} with length of {} bytes.".format(atomID, atomLength))
                if atomID in self._AtomOfAtoms_:  
                    self._Atoms_[atomID] = [] #just keep notice in dictonary that atom of atoms was read
                elif atomID in self._AtomList_:
                    bytes = f.read(atomLength-8)   ##Length includes 8 bytes header
                    if atomID in self._Atoms_: #subatom already exists in dictionary
                        self._Atoms_[atomID].append(bytes) #append string to existing list
                    else:
                        if atomID in self._MultiAtoms_:
                            self._Atoms_[atomID] = [bytes] #create new list entry, as for multiple atoms more can follow to be appended
                        else:
                            self._Atoms_[atomID] = bytes #for single atoms there is just this string
                else:
                    self._log_.warning("Jumping over unknown Atom ID (reversed): {} with length {}!!".format(atomID, atomLength))
                    bytes = f.read(atomLength-8)
                    #return 4
            self.FileHash = f.read(16)
            if self._DEBUG_: self._log_.debug("Reached FOOTER with Hash-Value: {}".format(self.FileHash))
        self._log_.info("Finished pure file reading.")
        self._unpackAtoms_()
        return 0 #file successfull read

    
    def write(self, file): #writes data to dsf file with according file-name
        self._progress_[0] = 0
        self._progress_[1] = 0 #keep original file length as goal to reach in progress[2]
        self._packAtoms_() #first write values of Atom strings that below will written to file   
        m = md5() #m will at the end contain the new md5 checksum of all data in file
        with open(file, "w+b") as f:    ##Open Tile as binary fily for writing and allow overwriting of existing file
            self._log_.info("Write now DSF in file: {}".format(file)  )
            s = pack('<8sI', 'XPLNEDSF'.encode("utf-8"),1)  #file header
            m.update(s)
            f.write(s)
            for k in self._Atoms_.keys():
                if k in self._AtomOfAtoms_:
                    if self._DEBUG_: self._log_.debug("Writing atom of atoms {} with length {} bytes.".format(k, self._TopAtomLength_(k)))
                    s = pack('<4sI', k.encode("utf-8"), self._TopAtomLength_(k)) # for AtomsOfAtoms just store header (id + length including sub-atoms)
                    m.update(s)
                    f.write(s)
                elif k in self._MultiAtoms_:
                    for a in self._Atoms_[k]:
                        if self._DEBUG_: self._log_.debug("Writing multi atom {} with length {} bytes.".format(k, len(a) + 8))
                        s = pack('<4sI', k.encode("utf-8"), len(a) + 8) + a # add 8 for atom header length (id+length)
                        m.update(s)
                        f.write(s)
                        self._updateProgress_(len(s))
                else: #just single instance atom with plane data
                        if k in self._AtomStructure_.keys():
                            if self._DEBUG_: self._log_.debug("Writing top-level atom {} with length {} bytes.".format(k, len(self._Atoms_[k]) + 8))
                        else:
                            if self._DEBUG_: self._log_.debug("Writing single atom {} with length {} bytes.".format(k, len(self._Atoms_[k]) + 8))
                        s = pack('<4sI', k.encode("utf-8"), len(self._Atoms_[k]) + 8) + self._Atoms_[k] # add 8 for atom header length (id+length)
                        m.update(s)
                        f.write(s) 
                        self._updateProgress_(len(s))
            if self._DEBUG_: self._log_.debug("New md5 value appended to file is: {}".format(m.digest()))
            f.write(m.digest())
        self._log_.info("Finshed writing dsf-file.")
        return 0


"""
#### FOLLOWING FUNCTION PROBABLY NOT NEEDED, TO BE REMOVED IN NEXT RELEASE ######
def isDSFoverlay(file):
  
    #This function checks if the dsf file includes the sim/overlay flag in
    #Properties and returns True if this is a case and False otherwise.
    #In case of errors, string with error description is returned.

    if not path.isfile(file):
        return "ERROR in isDSFoverlay: File {} does not exist!".format(file)
    flength = stat(file).st_size #length of dsf-file   
    with open(file, "rb") as f:    ##Open Tile as binary fily for reading
        start = f.read(12)
        if start.startswith(b'7z\xBC\xAF\x27\x1C'):
            if PY7ZLIBINSTALLED:
                f.seek(0)
                archive = py7zlib.Archive7z(f)
                filedata = archive.getmember(archive.getnames()[0]).read()
                f.close()
                f = BytesIO(filedata)
                flength = len(filedata) #also update to decompressed length
                start = f.read(12)
            else:
                return "ERROR in isDSFoverlay: File {} is 7Zip encoded! py7zlib not installed to decode.".format(file)
        identifier, version = unpack('<8sI',start)
        if identifier.decode("utf-8") != "XPLNEDSF" or version != 1:
            return "ERROR in isDSFoverlay: File {} is no X-Plane dsf-file Version 1!".format(file)  
        while f.tell() < flength - 16: #read chunks until reaching last 16 bytes hash value
            bytes = f.read(8)
            atomID, atomLength = unpack('<4sI',bytes)
            atomID = atomID.decode("utf-8")
            bytes = f.read(atomLength-8)   ##Length includes 8 bytes header

            if atomID == "DAEH":
                if bytes.find(b'sim/overlay\x001') > 0:
                    return True
                else:
                    return False
    return "ERROR in isDSFoverlay: File {} does not have an HEADER atom; no vaild dsf file!".format(file)
"""
                    
def getDSFproperties(file):
    """
    This function returns the properties of a dsf file as dict.
    """
    if not path.isfile(file):
        return "ERROR in getDSFproperties: File {} does not exist!".format(file)
    flength = stat(file).st_size #length of dsf-file   
    with open(file, "rb") as f:    ##Open Tile as binary fily for reading
        start = f.read(12)
        if start.startswith(b'7z\xBC\xAF\x27\x1C'):
            if PY7ZLIBINSTALLED:
                f.seek(0)
                archive = py7zlib.Archive7z(f)
                filedata = archive.getmember(archive.getnames()[0]).read()
                f.close()
                f = BytesIO(filedata)
                flength = len(filedata) #also update to decompressed length
                start = f.read(12)
            else:
                return "ERROR in getDSFproperties: File {} is 7Zip encoded! py7zlib not installed to decode.".format(file)
        identifier, version = unpack('<8sI',start)
        if identifier.decode("utf-8") != "XPLNEDSF" or version != 1:
            return "ERROR in getDSFproperties: File {} is no X-Plane dsf-file Version 1!".format(file)
        inHeader = False # Flag when inside Header atom of atoms
        props_dict = dict() #dictionary with properties to be returned
        while f.tell() < flength - 16: #read chunks until reaching last 16 bytes hash value
            bytes = f.read(8)
            atomID, atomLength = unpack('<4sI',bytes)
            atomID = atomID.decode("utf-8")
            if atomID == "DAEH":
                inHeader = True
            elif inHeader and atomID == "PORP":
                bytes = f.read(atomLength-8)
                x=bytes.split(b'\x00')
                for i in range(0,len(x)-1,2):
                    props_dict[x[i].decode("utf-8")]=x[i+1].decode("utf-8")
                return props_dict
                start = 0 #position when going through bytes
                while bytes.find(b'\x00',start) >= 0:
                    next = bytes.find(b'\x00',start)
                    end = bytes.find(b'\x00',next+1)
                    props_dict[bytes[start:next].decode("utf-8")] = bytes[next+1:end].decode("utf-8")       ###### l.append(atom[i:j].decode("utf-8"))
                    start = end+1
                return props_dict    
            else:
                bytes = f.read(atomLength-8)   ##Continue reading, Length includes 8 bytes header
    return "ERROR in getDSFproperties: File {} does not have an HEADER/PROPERTIES atom; no vaild dsf file!".format(file)
