# muxp_file.py    Version: 0.1.0 exp
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

from logging import getLogger
from os import path, replace

def readMuxpFile(filename, logname):
    log = getLogger(logname + "." + __name__) #logging based on pre-defined logname
    log.info("Reading muxp File: {}".format(filename))
    d = {} #dictionary returnig the read content
    no_split_keys = ["xpfolder", "muxpfolder", "id", "description", "author"]
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
                if key not in no_split_keys:
                    value = value.split() #each value is list of values that where sperated by blanks
                    if len(value) == 1: #in case of single values
                        value = value[0] #just use value and not set
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
                list_elements = line[2:].split()
                if len(list_elements) == 1:
                    list_elements = list_elements[0]
                new_datalist.append(list_elements)
                log.info("Data-element: {}".format(list_elements))
    return d, None

def validate_muxp(d):
    """
    Validates values in read muxp dictionary d and turns them inside d to correc format
    or returs error in case walues don't match.
    """
    ### Validate muxp file version ###
    if float(d["version"]) < 0.01: ### IMPORTANT: This is current version for muxp file
        return "Error muxp file: version is too old."
    
    ### Extract and validate area defined ###    
    #d["area"] = d["area"].split()
    for i in range(len(d["area"])):
        try:
            d["area"][i] = float(d["area"][i])
        except ValueError:
            return "Error muxp file: area argument {} is not a float.".format(i+1)
    if i != 3:
        return "Error muxp file: area has {} instead of 4 arguments.".format(i+1)
    ################ TBD: Check that 4 floats really define coordinates for an area #########################
    
    ### Extract and validate commands
    for i, c in enumerate(d["commands"]):
        if "coordinates" in c:
            for j, coord in enumerate(c["coordinates"]):
                d["commands"][i]["coordinates"][j] = [float(coord[1]), float(coord[0])] #swap from lon/lat to x,y
                ##### TBD: Check that really two floats
        if "3d_coordinates" in c:
            for j, coord in enumerate(c["3d_coordinates"]):
                d["commands"][i]["3d_coordinates"][j] = [float(coord[1]), float(coord[0]), float(coord[2])] #swap from lon/lat to x,y
        if "elevation" in c:
            d["commands"][i]["elevation"] = float(c["elevation"])
        #### TBD: Extract further commands #########
        
    #### TBD: Check that each command also includeds required attributes like coords for cut_poly... #####
    ########### ---> also include None values for non-existing values like for elevation in cut poly
    
    return None  #No error               
    
 

        
def get10grid(tile):
    """
    returns for a tile definition string like -122 or +47 the 10 rounded string -130 or +40 
    """
    if tile[0] == '-':
        s = 5
    else:
        s = 4.99
    if len(tile) == 3:
        return "{0:+03d}".format(round((int(tile)-s)/10)*10)
    else:
        return "{0:+04d}".format(round((int(tile)-s)/10)*10)
    
