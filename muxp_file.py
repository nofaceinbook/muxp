# muxp_file.py    Version: 0.2.0 exp
#        
# ---------------------------------------------------------
# Python Class for handling muxp-files.
# Used by Mesh Updater X-Plane (muxp)
#
# For more details refert to GitHub: https://github.com/nofaceinbook/betterflat
#
# WARNING: This code is still under development and may still have some errors.
#
# Copyright (C) 2020 by schmax (Max Schmidt)
#
# This code is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR 
# A PARTICULAR PURPOSE.  See the GNU General Public License for more details.  
#
# A copy of the GNU General Public License is available at:
#   <http://www.gnu.org/licenses/>. 
#
#******************************************************************************

#New in 0.2.0: Corrected that NEW Sceneries will be identified by findDSFfiles
#New in 0.2.0: update_elevation_in_poly command
#New in 0.2.0: findDSFmeshFiles function now searches for all scenery packs independent from tile (set None)

from logging import getLogger
from os import path, replace, walk, stat
from xplnedsf2 import getDSFproperties  ## isDSFoverlay not needed any more
from muxp_math import doBoundingRectanglesIntersect

def readMuxpFile(filename, logname):
    log = getLogger(logname + "." + __name__) #logging based on pre-defined logname
    log.info("Reading muxp File: {}".format(filename))
    d = {} #dictionary returnig the read content
    #no_split_keys = ["xpfolder", "muxpfolder", "id", "description", "author"]
    d["commands"] = [] #in this dictionary entry are commands listed
    if not path.isfile(filename):
        return None, "Error: File not existent!"
    with open(filename, encoding="utf8", errors="ignore") as f:
        for line in f:
            line_indent = len(line) - len(line.lstrip()) #line indent for checking if new command or inside ### WARNING: Tabs count just 1 !!!
            line = line.lstrip() #remove new leading spaces, tabs etc
            if line.find('\n') >= 0:
                line = line[:line.find('\n')] #remove line feed
            if line.find('#') >= 0:
                line = line[:line.find('#')] #remove everything after # which is comment
            if line.find(':') >= 0:
                key = line[:line.find(':')]
                key = key.lstrip()
                value = line[line.find(':')+2:]
                value = value.lstrip()
                #if key not in no_split_keys:
                #    value = value.split() #each value is list of values that where sperated by blanks
                #    if len(value) == 1: #in case of single values
                #        value = value[0] #just use value and not set
                if line_indent == 0: #we are on toplevel
                    if len(value) == 0: #if no value given, this is a mesh command
                        log.info("Entering new command: {}".format(key))
                        new_command_dict = {}
                        new_command_dict["command"] = key
                        d["commands"].append(new_command_dict)
                    else:
                        log.info("Read key: {} assigned to: {} and indent: {}".format(key, value, line_indent))  
                        d[key] = value
                else: #we are inside a command
                    if len(value) == 0: #if no value given, this is a data list for last element of command
                        log.info("Entering new datalist: {}".format(key))
                        new_datalist = []
                        d["commands"][-1][key] = new_datalist
                    else:
                        log.info("Read key inside command: {} assigned to: {} and indent: {}".format(key, value, line_indent))  
                        d["commands"][-1][key] = value
            if line.find('-') == 0: #we have now data list element which should belong to data set in command ---> error checks should be done as weel
                #list_elements = line[2:].split()
                #if len(list_elements) == 1:
                #    list_elements = list_elements[0]
                #new_datalist.append(list_elements)
                #log.info("Data-element: {}".format(list_elements))
                new_datalist.append(line[2:])
                log.info("Data-element: {}".format(new_datalist[-1]))
    return d, None

def validate_muxp(d, logname):
    """
    Validates values in read muxp dictionary d and turns them inside d to correct format
    or returs error in case values don't match (first value is integer [negative error, positive warning], second error message)
    """
    SUPPORTED_MUXP_FILE_VERSION = 0.1

    MUST_BASE_VALUES = ["muxp_version", "id", "area", "tile", "commands"] #These values must be all present in muxp files
    
    OPTIONAL_BASE_VALUES = ["description", "author"] #only strings are allowed optional

    MUST_COMMAND_PARAMETERS = {"cut_polygon" : ["coordinates"],
                               "cut_ramp" : ["coordinates", "3d_coordinates"],
                               "cut_flat_terrain_in_mesh" : ["coordinates", "terrain", "elevation"],
                               "cut_spline_segment" : ["3d_coordinates", "terrain", "width", "profile_interval"],
                               "update_network_levels" : ["coordinates", "road_coords_drapped"],
                               "limit_edges" : ["coordinates", "edge_limit"],
                               "update_raster_elevation" : ["coordinates", "elevation"],
                               "update_raster4spline_segment" : ["3d_coordinates", "width"],
                               "update_elevation_in_poly": ["coordinates", "elevation"],
                               "extract_mesh_to_file": ["coordinates"],
                               "insert_mesh_from_file": ["coordinates", "terrain"],
                               "exit_without_update": []}
    
    PARAMETER_TYPES = {"command" : ["string"],   #this is just command-type
                       "_command_info" : ["string"],  #added below, includes full command including added info after '.' like cut_polygon.inner
                       "name" : ["string"],
                       "terrain" : ["string"],
                       "elevation" : ["float"],
                       "include_raster_square_criteria" : ["string"],
                       "edge_limit" : ["int"],
                       "profile_interval" : ["float"],
                       "width" : ["float"]}
    
    OPTIONAL_PARAMETER_SETTING = {"elevation" : None,
                                  "name" : "",
                                  "include_raster_square_criteria" : "corner_inside"} #IF Parmeter is not given for command, the value in this dict is assigned
    
    LIST_TYPES = {"coordinates" : ["float", "float"],  #currently just float and int supported, everything else is string
                  "3d_coordinates" : ["float", "float", "float"],
                  "road_coords_drapped" : ["float", "float", "int"] }
    
    COORD_SWAPPING = ["coordinates", "road_coords_drapped"] #If parameter/list is included here coordinates from lon/lat will be swapped to x,y
                     ########## IMPORTANT: 3d_coordinates currently not swpapped !!!!!!!!!!! ############################################
    
    warnings = 0
    errors = 0
    skipped_commands = set() #set of indeces that will be skipped and thus removed from d["commands"]
    
    log = getLogger(logname + "." + __name__) #logging based on pre-defined logname
    log.info("Validating muxp File")
    
    ### CHECK THAT ALL MUST BASE VALUES ARE READ
    for mbv in MUST_BASE_VALUES:
        if mbv not in d:
            err  = "Must value {} missing in muxp-file.".format(mbv)
            log.error(err)
            return -1, err
    ### REPLACE OPTIONAL VALUES BY "" IF NOT PRESENT
    for obv in OPTIONAL_BASE_VALUES:
        if obv not in d:
            d[obv] = ""
    ### CONVERT AND CHECK BASE VALUES        
    try:
        muxp_version = float(d["muxp_version"])
    except ValueError:
        err = "muxp_version is not of type float"
        log.error(err)
        return -2, err
    if muxp_version > SUPPORTED_MUXP_FILE_VERSION:
        err = "muxp file version is {} but version {} is supported".format( d["muxp_version"], SUPPORTED_MUXP_FILE_VERSION)
        log.warning(err)
        return 1, err
    ### Extract and validate tile defined
    try:
        longitude = int(d["tile"][:3])
        latitude = int(d["tile"][3:])
    except ValueError:
        err = "Tile definition must be of form +xx+yyy (xx = longitude, yyy=latitude, + could also be -)"
        log.error(err)
        return -3, err
    ### Extract and validate area defined 
    d["area"] = d["area"].split() 
    for i in range(len(d["area"])):
        try:
            d["area"][i] = float(d["area"][i])
        except ValueError:
            err = "area argument {} is not a float.".format(i+1)
            log.error(err)
            return -4, err
        if i < 2 and not longitude <  d["area"][i] < longitude + 1:
            err = "area argument {} is outside defined tile definition for longitude".format(i+1)
            log.error(err)
            return -4, err
        if i >= 2 and not latitude <  d["area"][i] < latitude + 1:
            err = "area argument {} is outside defined tile definition for latitude".format(i+1)
            log.error(err)
            return -4, err        
    if i != 3:
        err = "Error muxp file: area has {} instead of 4 arguments.".format(i+1)
        log.error(err)
        return -4, err
    if not (0 <= d["area"][1] - d["area"][0] <= 1) or not (0 <= d["area"][3] - d["area"][2] <= 1):
        err = "Area definiton not correct. Must be of form longitude_min, longitude_max, latitude_min, latidude_max and within 1x1 degree grid."
        log.error(err)
        return -4, err
    ### VALIDATE AND EXTRACT COMMANDS
    for i, c in enumerate(d["commands"]):
        log.info("Validating Command {}: {}".format(i, c))
        if c["command"].find(".") > 1: #Check if command has additional info attached with '." like cut_polygon.inner
            d["commands"][i]["_command_info"] = d["commands"][i]["command"] #keep the full command name as additional info in dictionary for command with key "_command_info"
            d["commands"][i]["command"] = d["commands"][i]["command"][:c["command"].find(".")] #cut command unil '.'
        else:
            d["commands"][i]["_command_info"] = c["command"] #set _command_info to just command name in order that info can be shown e.g. for errors
            
        if c["command"] not in MUST_COMMAND_PARAMETERS: #check if supported command 
            log.warning("Command {}: {} NOT supported and skipped.".format(i, c["command"]))
            log.info("These commands are supported: {} ".format(MUST_COMMAND_PARAMETERS))
            warnings += 1
            skipped_commands.add(i)
            continue
        for must in MUST_COMMAND_PARAMETERS[c["command"]]: #check if all must values are included
            if must not in c:
                log.error("Command {}: Must parameter {} missing, command {} skipped.".format(i, must, c["command"]))
                errors += 1
                skipped_commands.add(i)
                break
        for parameter in c:
            log.info("    Validating Paramter {}".format(parameter))
            if parameter in PARAMETER_TYPES:
                d["commands"][i][parameter] = d["commands"][i][parameter].split()
                if len(c[parameter]) < len(PARAMETER_TYPES[parameter]):
                    log.error("Command {}: For parameter {} missing value, command {} skipped.".format(i+1, parameter, c["_command_info"]))
                    errors += 1
                    skipped_commands.add(i)
                for t, val_type in enumerate(PARAMETER_TYPES[parameter]):
                    if val_type == "float": 
                        try:
                            d["commands"][i][parameter][t] = float(c[parameter][t])
                        except ValueError:
                            log.error("Command {}: For {}. element of parameter {} wrong type (float would be required), command {} skipped.".format(i+1, t+1, parameter, c["_command_info"]))
                            skipped_commands.add(i)
                    if val_type == "int": 
                        try:
                            d["commands"][i][parameter][t] = int(c[parameter][t])
                        except ValueError:
                            log.error("Command {}: For {}. element of parameter {} wrong type (int would be required), command {} skipped.".format(i+1, t+1, parameter, c["_command_info"]))
                            skipped_commands.add(i)
                if len(d["commands"][i][parameter] ) == 1: ### If parameter has just one value, get rid of array
                    d["commands"][i][parameter] = d["commands"][i][parameter][0]
                if parameter in COORD_SWAPPING:
                        d["commands"][i][parameter][0], d["commands"][i][parameter][1]  = d["commands"][i][parameter][1], d["commands"][i][parameter][0]
            elif parameter in LIST_TYPES:
                log.info("       Current parameter is a list ....")
                for j, listline in enumerate(c[parameter]):
                    d["commands"][i][parameter][j] = d["commands"][i][parameter][j].split()
                    listline = listline.split()
                    if len(listline) < len(LIST_TYPES[parameter]):
                        log.error("Command {}: For list elements in line {} of list missing value, command {} skipped.".format(i+1, j+1, c["_command_info"]))
                        errors += 1
                        skipped_commands.add(i)
                        continue #no further processing of list, as elements are missing
                    for t, val_type in enumerate(LIST_TYPES[parameter]):
                        if val_type == "float": 
                            try:
                                d["commands"][i][parameter][j][t] = float(listline[t])
                            except ValueError:
                                log.error("Command {}: For {}. element in line {} of list {} wrong type (float would be required), command {} skipped.".format(i+1, t+1, j+1, parameter, c["_command_info"]))
                                skipped_commands.add(i)
                        if val_type == "int":  
                                try:
                                    d["commands"][i][parameter][j][t] = int(listline[t])
                                except ValueError:
                                    log.info("     listline: {}".format(listline))
                                    log.error("Command {}: For {}. element in line {} of list {} wrong type (int would be required), command {} skipped.".format(i+1, t+1, j+1, parameter, c["_command_info"]))
                                    skipped_commands.add(i)
                    if len(d["commands"][i][parameter][j]) == 1: ### If line of list has just one value, simplify array
                        d["commands"][i][parameter][j] = d["commands"][i][parameter][j][0]
                    if parameter in COORD_SWAPPING:
                        d["commands"][i][parameter][j][0], d["commands"][i][parameter][j][1]  = d["commands"][i][parameter][j][1], d["commands"][i][parameter][j][0]
            else:
                log.warning("Command {}: Parameter/List {} unknown in command {}. Parameter is ignored.".format(i+1, parameter, c["_command_info"]))
                warnings += 1
                continue
        for optpara in OPTIONAL_PARAMETER_SETTING: #If these optional parameters are not given with command, they are included with their default value
            if optpara not in c:
                c[optpara] = OPTIONAL_PARAMETER_SETTING[optpara]
    skipped_commands = sorted(skipped_commands, reverse = True)
    skipped_names = "" #names of commands sikipped
    for skipped in skipped_commands:
        skipped_names = skipped_names + d["commands"][skipped]["_command_info"]  +"\n"
        d["commands"].pop(skipped)
    if errors:
        return -5, "MUXP file has {} errors and {} warnings.\nFollowing commands skipped:\n{}".format(errors, warnings, skipped_names)
    elif warnings:
        return 5, "MUXP file has {} warnings.\nFollowing commands skipped:\n{}".format(warnings, skipped_names)
    else:
        return 0, "MUXP file read without errors and warnings."
                    
    return None  #No error               
    
        
def get10grid(tile):
    """
    returns for a tile definition string like -122+47 the 10 rounded string -130+40 
    """
    grid10 = ""
    for tile_part in [tile[:3], tile[3:]]:
        if tile_part[0] == '-':
            s = 5
        else:
            s = 4.99
        if len(tile_part) == 3:
            grid10 += "{0:+03d}".format(round((int(tile_part)-s)/10)*10)
        else:
            grid10 += "{0:+04d}".format(round((int(tile_part)-s)/10)*10)
    return grid10
        

def findDSFmeshFiles(tile, xpfolder, logname):
    """
    This function returns dictionary of all Scenery Packs that include a mesh
    for given tile or in general if tile == None.
    It searches in the X-Plane folder in Custom and Global Scenery.
    The key of the dict is the path from xpfolder to the scenery pack and
    then value is type of ACTIVE (topmost in scenery_packs.ini), PACK, DEFAULT,
    DISABLED, NEW (not in scenery_paxcks.ini yet).
    """
    log = getLogger(logname + "." + __name__)  # logging based on pre-defined logname
    inifile = xpfolder + "/Custom Scenery/scenery_packs.ini"
    packs = dict() #dictionary of scenery packs with key of pack as name and type as value

    if tile != None: #search packs for a specific tile
        grid10 = get10grid(tile)
        ########## TBD: Define all such folders as global variable to be easily changable ###############
        if path.exists(xpfolder +  "/Global Scenery/X-Plane 11 Global Scenery/Earth nav data/" + grid10 + "/" + tile + ".dsf"):  
            packs["Global Scenery/X-Plane 11 Global Scenery"] = "DEFAULT"
        for (_, dirs, _) in walk(xpfolder+"/Custom Scenery/"):
            break
        for scenery in dirs:
            dsf_file = xpfolder + "/Custom Scenery/" + scenery + "/Earth nav data/" + grid10 + "/" + tile + ".dsf"
            if path.exists(dsf_file):
                err, props = getDSFproperties(dsf_file)
                if err:
                    log.error(props)
                else:
                    if not 'sim/overlay' in props.keys():
                    #if not isDSFoverlay(dsf_file): ### OLDER FUNCTION, TO BE REMOVED
                        packs["Custom Scenery/"+scenery] = "NEW" #for the moment each found scenery is new
                    elif props["sim/overlay"] == '0': #In case such a definition would exist.....
                        packs["Custom Scenery/"+scenery] = "NEW" #for the moment each found scenery is new
    else: #search for any mesh packs
        packs["Global Scenery/X-Plane 11 Global Scenery"] = "DEFAULT"  #For all Tiles DEFAULT is allways an option
        for scenery in next(walk(xpfolder+"/Custom Scenery/"))[1]: #get all scenery pack folders in Custom Secenery
            next_pack = False
            for (root, dirs, files) in walk(xpfolder+"/Custom Scenery/"+scenery):
                for f in files:
                    if f[len(f)-4:] != ".dsf": #only consider .dsf-files
                        continue
                    if stat(path.join(root, f)).st_size > 1000000: ### WARNING: DSF Mesh with size less than 1MB will not be considered to be a mesh pack!
                        err, props = getDSFproperties(path.join(root, f))
                        if err:
                            log.error(props)
                        else:
                            if not 'sim/overlay' in props.keys():
                                packs["Custom Scenery/"+scenery] = "NEW" #for the moment each found scenery is new
                            elif props["sim/overlay"] == '0': #In case such a definition would exist.....
                                packs["Custom Scenery/"+scenery] = "NEW" #for the moment each found scenery is new
                    next_pack = True #after analysis of first .dsf file decide if mesh or not --> WARNING: Might skip small dsf or mixed dsf mesh folders
                    break
                if next_pack:
                    break    

    if not path.exists(inifile):
        return packs #Without inifile all packs are returned as New
                
    active_pack_found = False            
    with open(inifile, encoding="utf8", errors="ignore") as f:
        for line in f:
            if line.startswith("SCENERY_PACK_DISABLED"):
                scenery = line[line.find(" ")+1:-2]
                if scenery in packs.keys():
                    packs[scenery] = "DISABLED"                  
            elif line.startswith("SCENERY_PACK"):
                scenery = line[line.find(" ")+1:-2]
                if scenery in packs.keys():
                    if not active_pack_found:
                        packs[scenery] = "ACTIVE"
                        active_pack_found = True
                    else:
                        packs[scenery] = "PACK"

    sorted_packs = dict()
    for scentype in ["NEW", "ACTIVE", "PACK", "DEFAULT", "DISABLED"]:
        for scen in packs.keys():
            if packs[scen] == scentype:
                sorted_packs[scen] = scentype
                if tile == None and scentype == "ACTIVE": #In case of returning all mesh scenery packs
                    sorted_packs[scen] = "PACK" #ACTIVE makes no sense, because would depend on tile
                
    
    return sorted_packs

def getMUXPdefs(props):
    """
    Return the muxp defintions in DSF properties as array.
    """
    muxes = []
    i = 1
    while ("muxp/update/"+str(i) in props.keys()):
        update_id, version, area = props["muxp/update/"+str(i)].split('/')
        a = area.split()
        for j in range(len(a)):
            a[j] = float(a[j])
        muxes.append([update_id, version, a])
        i += 1
    return muxes

def updateAlreadyInProps(update_id, props):
    """
    Checks whether an muxp update (given as update_id string) is in the properties
    (given as dict) of an dsf file. If it is in the update the version
    of the update in the props is returned, if not None.
    """
    i = 1
    while "muxp/update/"+str(i) in props.keys():
        if props["muxp/update/"+str(i)].find(update_id) == 0:
            update_id, version, area = props["muxp/update/"+str(i)].split('/')
            return version
        i += 1
    return None

def areaIntersectionInProps(area, props):
    """
    Checks whether an area (given as 4-tuple) is intersection with
    areas defined for updates already done as stated the properties
    (given as dict) of an dsf file. If there is an intersection, the
    update_id is returned, None if there is no intersection.
    """
    i = 1
    while "muxp/update/"+str(i) in props.keys():
        update_id, version, update_area = props["muxp/update/"+str(i)].split('/')
        a = update_area.split()
        for j in range(len(a)):
            a[j] = float(a[j])
        if doBoundingRectanglesIntersect(area, a):
            return update_id
        i += 1
    return None

