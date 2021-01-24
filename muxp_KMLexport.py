# -*- coding: utf-8 -*-
#******************************************************************************
#
# muxp_KMLexport.py   for muxp
#        
muxpKMLexport2_VERSION = "0.4.0"
# ---------------------------------------------------------
# Python module for exporting mesh area to be flattened to KML-file.
# This module is called by muxp.py (Tool for flattening X-Plane Mesh)
#
# For more details refer to GitHub: https://github.com/nofaceinbook/muxp

# Copyright (C) 2021 by schmax (Max Schmidt)
#
# This code is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR 
# A PARTICULAR PURPOSE.  See the GNU General Public License for more details.  
#
# A copy of the GNU General Public License is available at:
#   <http://www.gnu.org/licenses/>. 
#
#******************************************************************************

# NEW Version 0.0.4: Support to convert kml to muxp file

from os import fspath, path
from muxp_math import *
from muxp_file import readMuxpFile, validate_muxp
from xmltodict import parse

def kmlExport2(dsf, boundaries, extract, filename):
    
    #### Sort exported trias according to their patches, and get all vertices
    patchTrias = {} #dictionary that stores for each patch the list of trias that are in the area in this patch
    all_vertices = []
    for t in extract:
        all_vertices.extend(t[0:3]) #get coordinates of tria vertices
        if t[6] in patchTrias:
            patchTrias[t[6]].append(t)
        else:
            patchTrias[t[6]] = [ t ]
    
    #### Get the bounding rectangle over all boundaries and all tria vertices to be exported for area which is relevant for raster export
    for bounds in boundaries:
        all_vertices.extend(bounds)
    latS, latN, lonW, lonE = BoundingRectangle(all_vertices)
    # Make sure that bounds stay inside 1x1 grid
    if int(lonE) > int(dsf.Properties["sim/east"]):
        lonE = int(dsf.Properties["sim/east"]) - 0.0000001
    if int(lonW) < int(dsf.Properties["sim/west"]):
        lonW = int(dsf.Properties["sim/west"]) + 0.0000001
    if int(latN) > int(dsf.Properties["sim/north"]):
        latN = int(dsf.Properties["sim/north"]) - 0.0000001
    if int(latS) < int(dsf.Properties["sim/south"]):
        latS = int(dsf.Properties["sim/south"]) + 0.0000001

    #### Get index for raster pixel SW (yS, xW) for area to be exported
    if len(dsf.Raster):  # check if dsf file has Raster definition, and skip this part if not
        xW = abs(lonW - int(dsf.Properties["sim/west"])) * (dsf.Raster[0].width - 1) # -1 from widht required, because pixels cover also boundaries of dsf lon/lat grid
        yS = abs(latS - int(dsf.Properties["sim/south"])) * (dsf.Raster[0].height - 1) # -1 from height required, because pixels cover also boundaries of dsf lon/lat grid
        if dsf.Raster[0].flags & 4: #when bit 4 is set, then the data is stored post-centric, meaning the center of the pixel lies on the dsf-boundaries, rounding should apply
            xW = round(xW, 0)
            yS = round(yS, 0)
        xW = int(xW) #for point-centric, the outer edges of the pixels lie on the boundary of dsf, and just cutting to int should be right
        yS = int(yS)

        #### Get index for raster pixel NE (yN, xE) for area to be exported
        xE = abs(lonE - int(dsf.Properties["sim/west"])) * (dsf.Raster[0].width - 1) # -1 from widht required, because pixels cover also boundaries of dsf lon/lat grid
        yN = abs(latN - int(dsf.Properties["sim/south"])) * (dsf.Raster[0].height - 1) # -1 from height required, because pixels cover also boundaries of dsf lon/lat grid
        Rcentricity = "point-centric"
        if dsf.Raster[0].flags & 4: #when bit 4 is set, then the data is stored post-centric, meaning the center of the pixel lies on the dsf-boundaries, rounding should apply
            xE = round(xE, 0)
            yN = round(yN, 0)
            Rcentricity = "post-centric"
        xE = int(xE) #for point-centric, the outer edges of the pixels lie on the boundary of dsf, and just cutting to int should be right
        yN = int(yN)

        #### Define relevant info for raster to be used later ####
        Rwidth = dsf.Raster[0].width
        xstep = 1 / (Rwidth - 1)  ##### perhaps only -1 when post-centric ---> also above !!! ########################################
        xbase = int(dsf.Properties["sim/west"])
        Rheight = dsf.Raster[0].height
        ystep = 1 / (Rheight -1)  ##### perhaps only -1 when post-centric ---> also above !!! ########################################
        ybase = int(dsf.Properties["sim/south"])



    
    filename = fspath(filename) #encode complete filepath as required by os
    with open(filename + ".kml", "w") as f:
        f.write("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
        f.write("<kml xmlns=\"http://www.opengis.net/kml/2.2\" >\n")
        f.write("<Document>\n")
   
        ############## Style definitions for Polygons in kml ###############
        f.write("<Style id=\"Water\"><LineStyle><width>1</width></LineStyle><PolyStyle><color>40ff0000</color></PolyStyle></Style>\n")
        f.write("<Style id=\"grass\"><LineStyle><width>1</width></LineStyle><PolyStyle><color>407fffaa</color></PolyStyle></Style>\n")
        f.write("<Style id=\"FLAT\"><LineStyle><color>ffff00aa</color><width>3</width></LineStyle><PolyStyle><color>40f7ffff</color></PolyStyle></Style>\n")
        f.write("<Style id=\"ELSE\"><LineStyle><width>1</width></LineStyle><PolyStyle><color>4000aaaa</color></PolyStyle></Style>\n")
        f.write("<Style id=\"Area\"><LineStyle><color>ff0000ff</color><width>4</width></LineStyle><PolyStyle><fill>0</fill></PolyStyle></Style>\n")
        
        ############## Style definitions for Raster Pixels ################
        if len(dsf.Raster):  # check if dsf file has Raster definition, and skip this part if not
            f.write("<Style id=\"Raster0\"><LineStyle><color>ff000000</color><width>1</width></LineStyle><PolyStyle><color>80998066</color></PolyStyle></Style>\n")
            f.write("<Style id=\"Raster1\"><LineStyle><color>ff000000</color><width>1</width></LineStyle><PolyStyle><color>80edefbe</color></PolyStyle></Style>\n")
            f.write("<Style id=\"Raster2\"><LineStyle><color>ff000000</color><width>1</width></LineStyle><PolyStyle><color>80efff00</color></PolyStyle></Style>\n")
            f.write("<Style id=\"Raster3\"><LineStyle><color>ff000000</color><width>1</width></LineStyle><PolyStyle><color>808fffff</color></PolyStyle></Style>\n")
            f.write("<Style id=\"Raster4\"><LineStyle><color>ff000000</color><width>1</width></LineStyle><PolyStyle><color>8000beff</color></PolyStyle></Style>\n")
            f.write("<Style id=\"Raster5\"><LineStyle><color>ff000000</color><width>1</width></LineStyle><PolyStyle><color>806596ff</color></PolyStyle></Style>\n")
            f.write("<Style id=\"Raster6\"><LineStyle><color>ff000000</color><width>1</width></LineStyle><PolyStyle><color>806060ff</color></PolyStyle></Style>\n")
            f.write("<Style id=\"Raster7\"><LineStyle><color>ff000000</color><width>1</width></LineStyle><PolyStyle><color>802c1ad3</color></PolyStyle></Style>\n")
            f.write("<Style id=\"Raster8\"><LineStyle><color>ff000000</color><width>1</width></LineStyle><PolyStyle><color>8020206b</color></PolyStyle></Style>\n")
            f.write("<Style id=\"Raster9\"><LineStyle><color>ff000000</color><width>1</width></LineStyle><PolyStyle><color>80131340</color></PolyStyle></Style>\n")
            minelev = 10000
            maxelev = -500
            for x in range(xW, xE+1):
                for y in range (yS, yN+1):
                    if dsf.Raster[0].data[x][y] < minelev:
                        minelev = dsf.Raster[0].data[x][y]
                    if dsf.Raster[0].data[x][y] > maxelev:
                        maxelev = dsf.Raster[0].data[x][y]
            elevsteps = (maxelev - minelev) / 10  + 0.01 #add small value that the maxvalue is in last elevstep included
        
        ########### Show boundaries as Areas ################
        for boundary in boundaries:     
            f.write("    <Placemark><name>Selected Area</name><styleUrl>#Area</styleUrl><Polygon><outerBoundaryIs><LinearRing><coordinates>\n")
            for p in boundary:
                f.write("        {},{},0\n".format(p[0], p[1]))
            f.write("    </coordinates></LinearRing></outerBoundaryIs></Polygon></Placemark>\n")        

        ######### Export Raster #################
        if len(dsf.Raster):  # check if dsf file has Raster definition, and skip this part if not
            f.write("<Folder><name>Raster {}x{} ({})from {}m to {}m </name>\n".format(Rwidth, Rheight, Rcentricity, minelev, maxelev))
            elevfolders = [[], [], [], [], [], [], [], [], [], []]
            if Rcentricity == "post-centric": #if post-centricity we have to move dem pixel half width/hight to left/down in order to get pixel center on border of dsf tile
                cx = 0.5 * xstep
                cy = 0.5 * ystep
            else:
                cx = 0
                cy = 0
            for x in range(xW, xE+1):
                for y in range (yS, yN+1):
                    folder = int((dsf.Raster[0].data[x][y] - minelev)/elevsteps)
                    elevfolders[folder].append("    <Placemark><name>Pixel {}:{} at {} m</name><styleUrl>#Raster{}</styleUrl><Polygon><outerBoundaryIs><LinearRing><coordinates>\n".format(x, y, dsf.Raster[0].data[x][y], folder ))
                    elevfolders[folder].append("        {},{},{}\n".format(xbase + x*xstep - cx, ybase + y*ystep - cy, dsf.Raster[0].data[x][y] ))
                    elevfolders[folder].append("        {},{},{}\n".format(xbase + x*xstep - cx, ybase + (y+1)*ystep - cy, dsf.Raster[0].data[x][y] ))
                    elevfolders[folder].append("        {},{},{}\n".format(xbase + (x+1)*xstep - cx, ybase + (y+1)*ystep - cy, dsf.Raster[0].data[x][y] ))
                    elevfolders[folder].append("        {},{},{}\n".format(xbase + (x+1)*xstep - cx, ybase + y*ystep - cy, dsf.Raster[0].data[x][y] ))
                    elevfolders[folder].append("        {},{},{}\n".format(xbase + x*xstep - cx, ybase + y*ystep - cy, dsf.Raster[0].data[x][y] ))
                    elevfolders[folder].append("    </coordinates></LinearRing></outerBoundaryIs></Polygon></Placemark>\n")
            for folder in range(10):
                f.write("<Folder><name>Raster from {}m to {}m</name>\n".format(int(minelev + folder*elevsteps), int(minelev + (folder+1)*elevsteps)))
                for line in elevfolders[folder]:
                    f.write(line)
                f.write("</Folder>\n")
            f.write("</Folder>\n")

        ########### Export Trias per Patch ##############
        for p_num in patchTrias:
            p = dsf.Patches[p_num]
            if p.flag == 1:
                flag = "PYS"
            else:
                flag = "OVL"
            terrain = dsf.DefTerrains[p.defIndex]
            if "Water" in terrain:
                style = "Water"
            elif "grass" in terrain:
                style = "grass"
            else:
                style = "ELSE"
                
            f.write("<Folder><name>Patch {} ({}): {}</name>\n".format(p_num, flag, terrain))
            tcount = 0

            for t in patchTrias[p_num]:
                upcoords = "{} - ".format(t[3:6])  ########### Following NEW /EXPERIMENTAL to get upper coordinates shown in Google Earth
                upi = 5
                while upi < len(t[0]):
                    upxa = ", {0:.6f}".format(t[0][upi])
                    upcoords += upxa
                    upi += 1
                upi = 5
                upcoords += "/"
                while upi < len(t[1]):
                    upxa = ", {0:.6f}".format(t[1][upi])
                    upcoords += upxa
                    upi += 1
                upi = 5
                upcoords += "/"
                while upi < len(t[2]):
                    upxa = ", {0:.6f}".format(t[2][upi])
                    upcoords += upxa
                    upi += 1                    
                f.write("    <Placemark><name>T{} {}</name><styleUrl>#{}</styleUrl><Polygon><outerBoundaryIs><LinearRing><coordinates>\n".format(tcount, upcoords, style))  ##upcords NEW/Experimental
                h = [] #stores heigth of vertices in triangles
                h.append(int(dsf.getVertexElevation(t[0][0], t[0][1], t[0][2])))  #3rd Value is height from Vertex to be consideredn in case differnet from -32xxx
                h.append(int(dsf.getVertexElevation(t[1][0], t[1][1], t[1][2])))
                h.append(int(dsf.getVertexElevation(t[2][0], t[2][1], t[2][2])))
                f.write("        {0},{1},{2} {3},{4},{5} {6},{7},{8} {0},{1},{2}\n".format(t[0][0], t[0][1], h[0], t[1][0], t[1][1], h[1], t[2][0], t[2][1], h[2]))
                f.write("    </coordinates></LinearRing></outerBoundaryIs></Polygon></Placemark>\n")
                tcount += 1
            f.write("</Folder>\n")

        f.write("</Document></kml>\n")


def kml2muxp(filename):
    """
    :param filename: name of kml file converted to muxp file
    Returns also same filename but removes .kml and adds .muxp if not present.
    :return: muxp_file_string, name of muxp-file created or error_string if muxp_file is None
    """
    xml = parse(open(filename).read())
    muxp = ""
    try:
        doc = xml['kml']['Document']
    except KeyError:
        return None, "Not kml Document file!"
    try:
        muxp += doc['description'] + '\n'
    except KeyError:
        return None, "Muxp header info in document description missing!"
    try:
        if doc['Placemark']['name'] != "area:":
            return None, "First Placemark is not area"
    except (KeyError, TypeError):
        return None, "No or too many Placemarks in kml main doc. Just one Placemark area needed!"
    try:
        area_lines = doc['Placemark']['Polygon']['outerBoundaryIs']['LinearRing']['coordinates']
        area_lines = area_lines.replace('\n', ' ')
        area_lines = area_lines.split()
        area_lat, area_lon = [], []
        for line in area_lines:
            coords = line.split(',')
            area_lat.append(float(coords[0]))
            area_lon.append(float(coords[1]))
        muxp += ("area: {} {} {} {}\n".format(min(area_lon), max(area_lon), min(area_lat), max(area_lat)))
    except KeyError:
        return None, "Coordinates of area missing"
    try:
        test = doc['Folder']
    except KeyError:
        return None, "Folders with commands missing!"
    try:  # Test if there is just one folder = one command
        test = doc['Folder']['name']
        doc['Folder'] = [doc['Folder']]  # convert single command to list in order to proceed
    except:
        test = "not needed"

    for folder in doc['Folder']:  # Folders with commands
        muxp += '\n'  # add new line before new command
        try:
            muxp += folder['name'] + '\n'
        except KeyError:
            continue
        try:
            desc_lines = folder['description'].split('\n')
            for line in desc_lines:
                muxp += "   {}\n".format(line.strip())
        except KeyError:
            desc = ""
        try:
            if folder['Placemark']['name'] == "coordinates:":
                coords_lines = folder['Placemark']['Polygon']['outerBoundaryIs']['LinearRing']['coordinates']
                coords_lines = coords_lines.replace('\n', ' ')
                coords_lines = coords_lines.split()
                muxp += "   coordinates:\n"
                for line in coords_lines:
                    coords = line.split(',')
                    muxp += "   - {} {}\n".format(coords[1].strip(), coords[0].strip())
        except KeyError:
            coords = ""
        try:
            if folder['Folder']['name'] == "3d_coordinates:":
                muxp += "   3d_coordinates:\n"
                try:  # single 3d coordinate
                    point = folder['Folder']['Placemark']['Point']['coordinates'].split(',')
                    elev = folder['Folder']['Placemark']['name']
                    muxp += "   - {} {} {}\n".format(point[1].strip(), point[0].strip(), elev.strip())
                except TypeError:   # multiple 3d coordinates
                    try:
                        for place in folder['Folder']['Placemark']:
                            point = place['Point']['coordinates'].split(',')
                            elev = place['name']
                            muxp += "   - {} {} {}\n".format(point[1].strip(), point[0].strip(), elev.strip())
                    except KeyError:
                        return None, "Syntax Error in multiple 3d_coordinate!"
                except KeyError:
                    return None, "Syntax Error in single 3d_coordinate!"
        except KeyError:  # No 3d_coordinates present within this command
            coords = ""

    muxp_filename = filename
    if muxp_filename.rfind(".kml") == len(muxp_filename) - 4:  # filename for muxp file ends with '.kml'
        muxp_filename = muxp_filename[:muxp_filename.rfind(".kml")]  # remove
    if muxp_filename.rfind(".muxp") != len(muxp_filename) - 5:  # filename for muxp file does not end with '.muxp'
        muxp_filename += ".muxp"  # add .muxp ending

    return muxp, muxp_filename


def muxp2kml(filename, logname):
    """
    Converts a muxp file in a kml string that is returned for further editing.
    Also the filneame with ending '.kml' is returned.
    In case of error the kml is None and instead of filename the error is returned.
    """
    muxpdefs, err = readMuxpFile(filename, logname)
    if err is not None:
        return None, err
    error, resultinfo = validate_muxp(muxpdefs, logname)
    if error < 0: # errors above 0 mean that file can still be processed
        return None, "Validation of muxp-file failed with error code {} ({})".format(error, resultinfo)

    filename = fspath(filename + ".kml") #encode complete filepath as required by os
    kml = []
    kml.append("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
    kml.append("<kml xmlns=\"http://www.opengis.net/kml/2.2\" >\n")
    kml.append("<Document>\n\n")
    head, tail = path.split(filename)
    kml.append("<name>{}</name>".format(tail))

    kml.append("<description>\n")
    for d in muxpdefs:
        if d != "area" and d != "commands":
            if d == "elevation_step" and not muxpdefs[d]:
                continue  # no need to include elevation_step if value is not defined
            kml.append("{}: {}\n".format(d, muxpdefs[d]))
    kml.append("</description>\n\n")

    kml.append("<Style id=\"Area\"><LineStyle><color>ff0000ff</color><width>4</width></LineStyle><PolyStyle><fill>0</fill></PolyStyle></Style>\n")
    kml.append("<Style id=\"Coords\"><LineStyle><color>ffff00aa</color><width>3</width></LineStyle><PolyStyle><color>40f7ffff</color></PolyStyle></Style>\n\n")
    kml.append("    <Placemark><name>area:</name><styleUrl>#Area</styleUrl><Polygon><outerBoundaryIs><LinearRing><coordinates>\n")
    kml.append("        {},{},0\n".format(muxpdefs["area"][2], muxpdefs["area"][0]))
    kml.append("        {},{},0\n".format(muxpdefs["area"][2], muxpdefs["area"][1]))
    kml.append("        {},{},0\n".format(muxpdefs["area"][3], muxpdefs["area"][1]))
    kml.append("        {},{},0\n".format(muxpdefs["area"][3], muxpdefs["area"][0]))
    kml.append("        {},{},0\n".format(muxpdefs["area"][2], muxpdefs["area"][0]))
    kml.append("    </coordinates></LinearRing></outerBoundaryIs></Polygon></Placemark>\n")

    for c in muxpdefs["commands"]:
        kml.append("\n<Folder><name>{}:</name>\n".format(c["_command_info"]))
        kml.append("<description>\n")
        for k in c:
            if k != "command" and k != "coordinates" and k != "3d_coordinates" and k != "_command_info":
                if c[k] != "" and not (k == "include_raster_square_criteria" and c[k] == "corner_inside") and not (k == "elevation" and c[k] is None):  # Don't include empty / default values
                ##### TBD: Make check for default values generic on default definitions #####
                    kml.append("{}: {}\n".format(k, c[k]))
        kml.append("</description>\n")
        if "coordinates" in c:
            kml.append("    <Placemark><name>coordinates:</name><styleUrl>#Coords</styleUrl><Polygon><outerBoundaryIs><LinearRing><coordinates>\n")
            for coords in c["coordinates"]:
                kml.append("        {},{},0\n".format(coords[0], coords[1]))
            kml.append("    </coordinates></LinearRing></outerBoundaryIs></Polygon></Placemark>\n")
        if "3d_coordinates" in c:
            kml.append("    <Folder><name>3d_coordinates:</name>\n")
            for coords in c["3d_coordinates"]:
                kml.append("        <Placemark><name>{}</name><Point><coordinates>{},{},0</coordinates></Point></Placemark>\n".format(coords[2],coords[1],coords[0]))
                #### IMPORTANT: 3d_coordinates are not yet swapped between lat / lon !!!!
            kml.append("   </Folder>\n")
        kml.append("</Folder>\n")

    kml.append("</Document></kml>\n")
    return "".join(kml), filename
