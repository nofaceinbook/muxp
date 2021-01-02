# -*- coding: utf-8 -*-
#******************************************************************************
#
# muxp_area.py    Version: 0.3.5e exp
#        
# ---------------------------------------------------------
# Python Class for adapting mesh in a given area of an XPLNEDSF
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

from xplnedsf2 import *
from logging import getLogger
from muxp_math import *
from copy import deepcopy
from math import acos
from obj_ex_import import *
from muxp_KMLexport import kmlExport2  # TESTING ONLY
    
class muxpArea:
    
    def __init__(self, dsf, logname):
        self.dsf = dsf #dsf from which area is extracted
        self.log = getLogger(logname + "." + __name__) #logging based on pre-defined logname
        self.apatches = set() #set of patches that are relevant for that area
        self.atrias = [] #area as array, of triangles where
                  # [0 - 2] list of all coordinates of tria vertices including s/t ##### ONLY REFERENCE NO DEEPCOPY / BETTER JUST DEEPCOPY of x,y corrds ?????
                  # [3 - 5] list of pool and vertex id in pool in dsf -- they stay even, if coordinates are changed or trias split; allows reference to original trias/values/scaling
                  # [6] index to patch tria was in dsf
        self.elevation_scalings = dict()  # dictionary of scalings for elevation relevant in that area; pair of (factor, base) are keys in dict and value is number of patch for which it exists
        self.elev_factor_min, self.elev_base_min = (999999, 999999)  # minimum values in existing mesh used for defining according new pools in update

    def extractMeshArea(self, latS, latN, lonW, lonE):
        """
        Extracts an area [latS, latN, lonW, lonE] from mesh in self.dsf and stores it in self.trias
        Important: This function really removes trias from dsf.
                   This function will add trias to existing ones.
        """
        self.log.info("Extracting area latS: {}, latN: {}, lonW: {}, lonE:{} from dsf.".format(latS, latN, lonW, lonE))
        triaCount = 0 #counts all trias in dsf
        for p in self.dsf.Patches:
            trias = p.triangles()
            tremoved = [] #trias that should be removed
            for t in trias:
                # get for each tria the bounding rectangle in miny, maxy, minx, maxxx
                minx = min(self.dsf.V[t[0][0]][t[0][1]][0], self.dsf.V[t[1][0]][t[1][1]][0], self.dsf.V[t[2][0]][t[2][1]][0])
                maxx = max(self.dsf.V[t[0][0]][t[0][1]][0], self.dsf.V[t[1][0]][t[1][1]][0], self.dsf.V[t[2][0]][t[2][1]][0])
                miny = min(self.dsf.V[t[0][0]][t[0][1]][1], self.dsf.V[t[1][0]][t[1][1]][1], self.dsf.V[t[2][0]][t[2][1]][1])
                maxy = max(self.dsf.V[t[0][0]][t[0][1]][1], self.dsf.V[t[1][0]][t[1][1]][1], self.dsf.V[t[2][0]][t[2][1]][1])
                #now check if bounding rectangle of tria intersects with area
                if not (minx < lonW and maxx < lonW): #x-range of box is not completeley West of area     
                    if not (minx > lonE and maxx > lonE): #x-range of box is not completele East of area
                        if not (miny < latS and maxy < latS): #y-range is not completele South of area
                            if not (miny > latN and maxy > latN): #y-range is not conmpletele North of ares
                                ### NEW 15.08.20: DEEPCOPY 2 LINES BELOW TO HAVE REALLY UNIQUE VERTICES NOT RELATING TO SAME IN DSF !!!
                                self.atrias.append([deepcopy(self.dsf.V[t[0][0]][t[0][1]]), deepcopy(self.dsf.V[t[1][0]][t[1][1]]), deepcopy(self.dsf.V[t[2][0]][t[2][1]])])
                                self.atrias[-1].extend(deepcopy(t))  #so we have an intersection of tria box with area and append the tria
                                self.atrias[-1].append(self.dsf.Patches.index(p))
                                current_patch_index = self.dsf.Patches.index(p)
                                self.apatches.add(current_patch_index)
                                ### self.log.info("Scaling: {}   just multiplier: {}".format(self.dsf.Scalings[t[0][0]], self.dsf.Scalings[t[0][0]][0]))
                                self.elevation_scalings[(self.dsf.Scalings[t[0][0]][2][0], self.dsf.Scalings[t[0][0]][2][1])] = current_patch_index
                                self.elevation_scalings[(self.dsf.Scalings[t[1][0]][2][0], self.dsf.Scalings[t[1][0]][2][1])] = current_patch_index
                                self.elevation_scalings[(self.dsf.Scalings[t[2][0]][2][0], self.dsf.Scalings[t[2][0]][2][1])] = current_patch_index
                                tremoved.append(t)
                                self.log.debug("Tria {} with latS: {}  latN: {}  lonW: {} and lonE: {} in area.".format(t, miny, maxy, minx, maxx))
                triaCount += 1
            for t in tremoved:
                trias.remove(t)
            p.trias2cmds(trias) #updates dsf patch with trias not including removed ones
        self.log.info("  ... dsf has {} trias and {} trias from {} different patches are now in the extracted area.".format(triaCount, len(self.atrias), len(self.apatches)))
        self.elev_factor_min, self.elev_base_min = (999999, 999999)  # start with high numbers for searching for min
        for e in self.elevation_scalings.keys():
            self.elev_factor_min = min(self.elev_factor_min, e[0])
            self.elev_base_min = min(self.elev_base_min, e[1])
        self.log.info(" DSF Extract has following elevation scalings (with example patch number as value): {}".format(self.elevation_scalings))
        self.log.info(" For updated dsf following minimum factor: {} and base: {} are relevant".format(self.elev_factor_min, self.elev_base_min))
        return
    
    
    def insertMeshArea(self):
        """
        Insert mesh area in dsf again from which it was extracted.
        Important: The shape of extraction must still be the same. Also no new vertices on borders are allowed.
                   Changes are only allowed inside the area.
        """
        patchTrias = {} #dictionary that stores for each patch the list of trias that are in the area in this patch
        for t in self.atrias:
            if t[6] in patchTrias:
                patchTrias[t[6]].append([t[3], t[4], t[5]])
            else:
                patchTrias[t[6]] = [ [t[3], t[4], t[5]] ]
        for p in patchTrias:
            self.log.info("For patch no. {} trias will be added: {}".format(p, patchTrias[p]))
            dsftrias = self.dsf.Patches[p].triangles()
            dsftrias.extend(patchTrias[p])
            self.dsf.Patches[p].trias2cmds(dsftrias)

    def validate_mesh(self):
        """
        Function validates if mesh of area is correct like trias are clockwise, are no lines or just points,
        no vertex on same coordinates with different elevation ....
        """
        for nt, t in enumerate(self.atrias):
            # Checking all trias are clockwise
            if not IsClockwise([t[0][:2], t[1][:2], t[2][:2]]):
                self.log.warning("Tria {} is anticlockwise and will be set to clockwise now.".format(t))
                self.atrias[nt][0], self.atrias[nt][2] = self.atrias[nt][2],  self.atrias[nt][0]
        # Checking different elevations for same coords
        ############## TBD: SHOULD THIS NOT BE DONE WHEN MATCHING THEM FOR CONVERSION TO DSF #####################
        different_elevations = 0  # assume no differences exist
        cdict = {}  # set up dictionary with all coords, value is list with max. elevation at first element and
        # indices-tuples (nt, nv) to all vertices at this coordinates as following elements
        for nt, t in enumerate(self.atrias):
            for nv, v in enumerate(t[:3]):
                if (round(v[0], 7), round(v[1], 7)) in cdict:
                    current_max_elevation = cdict[(round(v[0], 7), round(v[1], 7))][0]
                    if v[2] < current_max_elevation:
                        self.atrias[nt][nv][2] = current_max_elevation
                        different_elevations += 1
                    elif v[2] > current_max_elevation:  # current elevation is highest
                        cdict[(round(v[0], 7), round(v[1], 7))][0] = v[2]
                        for index_tuple in cdict[(round(v[0], 7), round(v[1], 7))][1:]:  # adapt all previous vertices
                            self.atrias[index_tuple[0]][index_tuple[1]][2] = v[2]
                        different_elevations += 1
                    cdict[(round(v[0], 7), round(v[1], 7))].append((nt, nv))
                else:
                    cdict[(round(v[0], 7), round(v[1], 7))] = [v[2], (nt, nv)]  # set elevation and index for these coordinates
        if different_elevations:
            self.log.warning("{} DIFFERING ELEVATIONS at vertices found; updated to max. elevation found at each coordinates".format(different_elevations))
            #### tbd to set always on the same value in area, e.g. always highest found  ####

        ##### to be continued ##############
        ###### OPEN: Check not atrias but really trias in dsf are correct? But then this has to be final step after creating dsfVertices and insertion in dsf ##########

    def getAllVerticesForCoords(self, coords):
        """
        Returns all vertices that have same lon/lat coordinates as given in list of coords (list of [x,y])
        """
        self.log.info("Searching vertices for coords: {}".format(coords))
        cdict = {}  #set up dictonary with all coords o to find additional in area with same coords
        vertices = [] #list of vertices 
        for c in coords:
            cdict[(round(c[0], 7), round(c[1], 7))] = True  # coords round to range of cm
        for t in self.atrias:
            for v in t[:3]:
                self.log.debug("Checking vertex: ({}, {})".format(round(v[0],7), round(v[1],7)))
                if (round(v[0], 7), round(v[1], 7)) in cdict:
                    vertices.append(v)  # add tuple of vertex at coords to make sure to get all vertices at the coords
        self.log.info("{} vertices on {} coords found.".format(len(vertices), len(coords)))
        return vertices    #returns set of all vertices which ar on coords

    def mesh_elevation(self, p, epsilon=0.0001):
        """
        Returns elevation of a point = (x, y) in meters calculated based on it's position within the mesh.
        epsilon is the allowed tolerance in percent to count p inside tria, default is 0.01 percent
        """
        for t in self.atrias:
            a, b = PointLocationInTria(p, [t[0][:2], t[1][:2], t[2][:2]])
            c = 1 - a - b
            if -epsilon <= a <= 1 + epsilon and -epsilon <= b <= 1 + epsilon and -epsilon <= c <= 1 + epsilon:  # means p is inside t
                if t[0][2] < -32767 or t[1][2] < -32767 or t[2][2] < -32767:  # we have raster elevation at a vertex
                    elev = []
                    for i in range(3):
                        elev.append(self.dsf.getVertexElevation(t[i][0], t[i][1]))
                    return elev[2] + a * (elev[0] - elev[2]) + b * (elev[1] - elev[2])
                else:  # no raster elevation
                    return t[2][2] + a * (t[0][2] - t[2][2]) + b * (t[1][2] - t[2][2])
        self.log.error("No mesh triangle found where point {} is inside in order to retrieve elevation!".format(p))
        return None

    def replace_vertex_in_poly(self, oldv, newv, poly):
        """
        Replaces in list of vertices in poly all vertices (x,y) that match oldv with newv.
        In case newv was already in the list, this occurrence is left out. Updated poly is returned.
        """
        replaced = False
        new_poly = []
        for v in poly:
            if v[0] == oldv[0] and v[1] == oldv[1] and not replaced:
                new_poly.append(newv)
                replaced = True
            elif v[0] != newv[0] or v[1] != newv[1]:
                new_poly.append(v)
        return new_poly


    def PolyCutPoly(self, p, c, c_start=0, c_start_distance=0):
        """
        This function cuts polygon p with cutting poly c.
        p must is interpreted as a closed polygon (but last point not identic to first in list)
        where c could also be some segments (if c is closed last point must be same as first point in list).
        All polys must be ordered clockwise. Important: First point of c (=c[0]) must be outside of p.
        Polys may be concave but must not cut themselves / have doubled lines for themselves
        Function returns of poly p the polys left (= outside c, in case c is closed), right (=inside c) and border vertices between outside and inside.
        Important: As p, the returned polys are to be intrpreted as closed, however the last vertex is not the same as the first
        c_start and c_start_distance needed for recursive calls in case we are checking for further cuts,
        then checking starts at c with index c_start and cuts only count when after distance on that segement (cuts before are already considered)
        """
        ############ TBD: Handle accuracy in case cut is close to vertices and cutting points are close to segements, especially co-linar segments ###############
        ################### ---> FIRST ASPECTS NOW COVERED AND IDEAS FOR OTHERS, REFER TO COMMENTS BELOW (7.20.2020)
        ############ TBD: Check where really deepcopy is required ################
        self.log.info("Polygon {} cutting with {} from start-segement {} at distance {}".format(p, c, c_start, c_start_distance))
        border_v = [] #these vertices are building the border between the cut halfs of p from entry to exit point (including vertices of c and cutting points)
        for i in range(c_start, len(c) - 1): #check for each segement of cutting poly...
            len_p = len(p)
            cP_dict = dict() #this dict will contain all cutting points of segment in c with all segments in p as values and distances to segment start of c as keys
            for j in range (len_p): #...which segments of p it will cut
                cuttingPoint = intersectionCL(c[i], c[i+1], p[j], p[(j+1)%len_p]) ### WHAT HAPPENS IF SEGEMENTS ARE COLINEAR???? #####
                if cuttingPoint == "Collinear":
                    self.log.warning("Collinear Lines in PolyCutPoly with cut segment: {} and poly segement: {} of poly: {}".format(i, j, p))
                    ####### INFO 1: FLAT TRIAS WHERE TWO VERTICES ARE IDENTICAL ALSO COUNT AS COLLINEAR
                    ####### INFO 2: COLLINEAR COULD ALSO HAPPEN FAR AWAY WITHOUT EXACT OVERLAPPING PARTS
                    ### TBD: DEPENDING ON WHAT KIND OF COLLINEAR CASE WE HAVE THIS FUNCTION MIGHT NEED TO RETURN
                    ###        at least info on border_vertices (but only returning them causes error in calling function as this expects then a cut has happened
                    cuttingPoint = None
                if cuttingPoint: #segement of c did cut segment of p, so we now enter/leave p
                    self.log.info("   not confirmed cutting point {}: with c-segment:{} after distance:{}".format(cuttingPoint, i, distance(c[i], cuttingPoint)))
                    if i != c_start or distance(c[i], cuttingPoint) > c_start_distance: #cuts on start_segement before distance are not counted
                        self.log.info("   cutting point {}: with c-segment:{} after distance:{}".format(cuttingPoint, i, distance(c[i], cuttingPoint)))
                        if round(distance(c[i], cuttingPoint), 3) in cP_dict: #### NEW 5.10.20 special case
                            self.log.warning("Tangent cutting point at {} detected or cutting very very sharp tria!".format(cuttingPoint))
                            cP_dict[round(distance(c[i], cuttingPoint), 3)+000.1] = [cuttingPoint, j]
                            ######### TBD: cP_dict might not have right order by this simple statement above
                            ########### needs to be checked which segment comes first
                            ############ IN CASE OF SHARP TRIAS THIS COULD LEAD TO FLAT TRIAS, WHERE TWO VERTICES ARE IDENTICAL
                            ############    -> They should be removed
                        else: #### NEW 5.10.20 special case, was done every time before new if came
                            cP_dict[round(distance(c[i], cuttingPoint), 3)] = [cuttingPoint, j] #j is entry segement of p, needed to find end of outside/inside poly  #assumption is that for such polys there is no doubled cuttingPoint
            if len(cP_dict) == 0: #this segement of p was not cut by c, go to next one
                if border_v != []:
                    border_v.append(c[i+1]) #if we are already inside p, we add the current end of segemnet to border
                continue
            if len(cP_dict) > 0: #cutting Points we are entering/leaving p
                for k in sorted(cP_dict.keys()):
                    border_v.append(cP_dict[k])
                    if len(border_v) >= 2: #now we have entry to p as first point and exit as last point in list
                        break #additional cutting points will be checked later, in this function call we just consider one entry and exit in p
            if len(border_v) == 1: #we just entered p but segment of c does not also leave p
                border_v.append(c[i+1]) #so end point of c is inside p and thus a border vertex 
                continue #we need to search further for exit
            else:
                break #now we have entry to p as first point and exit as last point in border_v list and can stopp searching cuts
        if len(border_v) < 2: #no cut found for c into p        #### len(border_v1) == 1 should not happen, or error ??!! ############
                return [], [], [] #only return empty lists in case of no cut
        self.log.info("   Cutting line ended: {}".format(border_v))
        entry_segment = border_v[0][1]
        exit_segment = border_v[-1][1]
        if int(exit_segment) != exit_segment:  # NEW 4.10.20 preventing error, that no exit segment was found and thus reference is to a coorindate as float ############ TBD ####
            self.log.warning("No exit found in PolyCutPoly. Thus this poly is not cut!")
            return [], [], []  # For the moment just assume that this error case is no cut !!!! ############# TBD #####
            ###### Think of returning at least border_v; BUT first vertex still has exit segment to be removed first !! #####
            ######     and only returning border causes error in calling function CutPoly which assumes there was a cut if border vertices are returned
            ####### RETURN ABOVE IS TOO EARLY, THERE MIGHT BE ANOTHER CUTTING POINT LATER ???? !! ?? ###########
            ######### This case here could be handled together with 8 lines above if len(border_v) < 2
        border_v[0] = border_v[0][0] #get rid of not needed sgement info in vertex list
        border_v[-1] = border_v[-1][0] #get rid of not needed sgement info in vertex list
        if entry_segment == exit_segment: #Special case if entry and exit on same segment, then one part is just formed by border vertices ####### NEW 18.04.2020 ##########
            if not IsClockwise(border_v): #so we have to be sure that also this part is ordered clockwise; if c is concave then an outer part (anti-clockwis) can cut into p
                self.log.warning("   Entry = Exit segment and border vertices are not clockwise --> it is reversed!!!")
                outer = deepcopy(border_v)
                outer.reverse() #as they are not clockwise
                inner = deepcopy(border_v) #border_v are first part around inner
                for s in range(len_p): #and follow then all around p back to first border_v
                    inner.append(p[(entry_segment+1+s)%len_p])
            else: #so the inner part is cutting into p on the same segment
                self.log.warning("   Entry = Exit segment but border vertices clockwise")
                inner = deepcopy(border_v) #inner are thus just border_v which are already clockwise
                outer = deepcopy(border_v)
                outer.reverse() #these border_v are now not including inner part, but outer, so they have to be reversed
                for s in range(len_p): #and follow then all around p back to first border_v
                    outer.append(p[(entry_segment+1+s)%len_p])
        else: #no special case; entry and exit to p are on different segments
            part1 = deepcopy(border_v)
            part1.append(p[exit_segment])#the first vertex of exit-segment is the first in the loop back (outer) to entry
            s = (exit_segment-1)%len_p
            while s !=  entry_segment: #go backwards through p till entry point for cut found
                part1.append(p[s])
                s = (s-1)%len_p
            part2 = deepcopy(border_v)
            part2.append(p[(exit_segment + 1)%len_p]) #second vertex of exit-segment is the first in loop forward (inner) back to entry
            s = (exit_segment+2)%len_p
            while s !=  (entry_segment+1)%len_p: #go forward through p till entry point for cut found
                part2.append(p[s])
                s = (s+1)%len_p
            #### AS part 1 was constructed backwards we must no reverse it in order to have it in clockwise order again
            part1.reverse()
            ### Now check which part is outer and inner:
            ## The following line assumes that c[i] to c[i+1] is still the cutting line of p where cutting polygon exits p
            if ((c[i+1][0] - c[i][0]) * (p[exit_segment][1] - c[i][1]) - (c[i+1][1] - c[i][1]) * (p[exit_segment][0] - c[i][0])) > 0: #first point of exit segment of p lies on outer side in case of clockwise going through p
                outer = part1
                inner = part2
            else:
                outer = part2
                inner = part1
                self.log.info("    SWAPPED INNER AND OUTER POLYS!")

        ############ FOLLOWING NEW 5.10.2020 ##########################################
        # This code shall handle edge cases where c cuts p close to points of p
        # So either just being tangent (cutting of just one edge) or parallel of edge of p
        # However this will not handle the exact collinear match when searching intersections above --> tbd above
        # Also not handled yet is the case that vertex of c is close to edge/vertex of p (without cut)
        #   -> TBD: Latest could be done before cut to check cutting line for all vertices in cutting line close to
        #     points in mesh, and use those for cutting, and if vertices close to edges, split edges
        ############################################
        # Following line defines the point of current cutting line that will be used to search for further cuts
        #    it is included here, as this part could set the value to 0, and also further improvements possible, read blelow
        exit_distance = distance(c[i], border_v[-1]) + 0.01 ######  0.0001 was not sufficeint, why so high rounding errors ??? ####
        # Search closest points of p to entry and exit point of cut, which are closer than ACCURACY or None else
        close_entry_point = None  # in normal case entry and exit points are not too close to vertices of p
        close_exit_point = None
        """
        for point in p:  # but check now for all vertices of p if there closer points
            if distance(point, border_v[0]) < 1:  # border_v[0] is entry point   #### TBD: VALUE 2 IS ACCURACY TO BE DEFINED GENERALLY ###########
                if not close_entry_point or distance(point, border_v[0]) < distance(close_entry_point, border_v[0]):
                    close_entry_point = deepcopy(point)  # deepcopy required ??
            if distance(point, border_v[-1]) < 1:  # border_v[-1] is exit point   #### TBD: VALUE 2 IS ACCURACY TO BE DEFINED GENERALLY ###########
                if not close_exit_point or distance(point, border_v[-1]) < distance(close_exit_point, border_v[-1]):
                    close_exit_point = deepcopy(point)  # deepcopy required ??
        """
        # When searching closest point this must be selected from vertices on the edge cut and not any point of p
        ############ TBD: The first value compared to is ACCURACY --> SHOULD BE DEFINED FLEXIBLE WITH COMMANDS #######
        # In case cutting polygon has closer edges/vertics than accuracy this could lead to errors in the mesh
        ACCURACY = 0.3
        if distance(border_v[0], p[entry_segment]) < ACCURACY and distance(border_v[0], p[entry_segment]) < distance(border_v[0], p[(entry_segment+1)%len(p)]):
            close_entry_point = deepcopy(p[entry_segment])
        elif distance(border_v[0], p[(entry_segment+1)%len(p)]) < ACCURACY and distance(border_v[0], p[(entry_segment+1)%len(p)]) < distance(border_v[0], p[entry_segment]):
            close_entry_point = deepcopy(p[(entry_segment+1)%len(p)])
        if distance(border_v[-1], p[exit_segment]) < ACCURACY and distance(border_v[-1], p[exit_segment]) < distance(border_v[-1], p[(exit_segment+1)%len(p)]):
            close_exit_point = deepcopy(p[exit_segment])
        elif distance(border_v[-1], p[(exit_segment+1)%len(p)]) < ACCURACY and distance(border_v[-1], p[(exit_segment+1)%len(p)]) < distance(border_v[-1], p[exit_segment]):
            close_exit_point = deepcopy(p[(exit_segment+1)%len(p)])
        if close_entry_point and close_exit_point and entry_segment == exit_segment and distance(close_entry_point, close_exit_point) < ACCURACY:
            self.log.info("PolyCutPoly cuts same edge closer to vertices than accuracy. CUt is not performed and cutting vertices like {} inside that poly vanish.".format(c[i]))
            inner = []
            outer = deepcopy(p)

        # Now replace in outer and inner polys of p (after cut) the close vertices if they exist
        for old, new in [(border_v[0], close_entry_point), (border_v[-1], close_exit_point)]:
            if not new: continue  # if there is no closer point, then nothing to do
            self.log.info("Close Cut: Replacing {} with {} in outer-poly: {} and inner-poly: {}".format(old, new, outer, inner))  #### TESTING ONLY #####
            outer = self.replace_vertex_in_poly(old, new, outer)  # replace entry point by point of p
            inner = self.replace_vertex_in_poly(old, new, inner)
            # self.log.info("    polygon after replacement: {}".format(inner))  #### TESTING ONLY #####
            ## FOLLOWING OPTION COULD SIMPLIFY complete function: always start with next cutting segment
            exit_distance = 0  # VERY NEW: ACTUALLY IT SHOULD NOT BE A PROBLEM TO START WITH NEXT SEGMENT, AS ONLY CONVEX SHAPES ARE CUT BY A LINE STAY CONVEX (exception when cutting same edge twice a concave cutting line shape could stay, but completely inside the convex poly, so no further cuts expected)
            if i < len(c) - 1: i += 1
            # however issue, remains by vertex i+1 that lies after replacement inside inner/outer, therefore is next line
            if PointInPoly(c[i], outer) or PointInPoly(c[i], inner):
                if i < len(c)-1: i += 1
                self.log.info("Cutting Point {} vanished in Poly with replaced vertices, go to next in cutting line ...".format(c[i-1]))
                #### TBD: include vanished point in border_v !!!!!!!!!!!!!!!!!!! #########################
        # Now also replace entry and exit points itself in the border_vertices
        if close_entry_point: border_v[0] = close_entry_point
        if close_exit_point: border_v[-1] = close_exit_point
        # Special case for polys that have very small size like ACCURACY, they could completely collapse
        ############## NOT SURE IF THIS CASE REALLY CAN HAPPEN ???? #####################
        if len(outer) < 3 and len(inner) < 3:  # inner and outer are not 2d, so nothing would stay
            inner = deepcopy(p)  # in that case just count this small poly as belonging to the inner  #### TBD: Option to decide if inner or outer ####
            self.log.warning("Poly {} is too small to be cut with regard to ACCURACY, so it stays as inner Polygon.".format(p))
        #### ALTERNATIVE FOR SIMPLIFICATION METHOD TO START WITH NEXT SEGEMENT COULD BE TO RETRIEVE UPDATED EXIT POINT
        ####    BY USING PolyCutPoly with replaced edges
        ################################################################################

        if len(outer) >= 3:   #### NEW 5.10. as non_cut poly has either empty inner or outer
            outer1, inner1, border1 = self.PolyCutPoly(outer, c, i, exit_distance) ######  NEW 5.10., see old definition above
            if border1 == []:  # no further cut for outer
                outer1 = [outer]  #s o we stay with the current outer
        else:
            outer1, inner1, border1 = [], [], []
        if len(inner) >= 3:  #### NEW 5.10. as non_cut poly has either empty inner or outer
            outer2, inner2, border2 = self.PolyCutPoly(inner, c, i, exit_distance) ######  NEW 5.10., see old definition above
            if border2 == []:  # no further cut for inner
                inner2 = [inner]  #s o we stay with the current inner
        else:
            outer2, inner2, border2 = [], [], []
        border_v.extend(border1)
        outer1.extend(outer2)
        inner1.extend(inner2)
        border_v.extend(border2)
        self.log.info("  PolyCutPoly RESULTS:\n    p = {}\n    outer = {}\n    inner = {}\n    border = {}\n".format(p, outer1, inner1, border_v))
        return outer1, inner1, border_v


    def CutPoly(self, p, elev=None, keepInnerTrias=True):
        #################### P MUST be closed (first = last vertex in list) ### TBD: Idea was also to be able cutting al line ####################
        outer = []
        inner = []
        border = []
        new_trias = []
        old_trias = []
        p_inside_one_tria = False
        self.log.info("Cutting Polygon p into area, retrieving inner and outer sub-polygons.")
        if not IsClockwise(p):
            self.log.warning("Polygon is not clockwise --> it is reversed!!!")
            p.reverse()
        for t in self.atrias: #go through all trias in area
            tria = [t[0][0:2], t[1][0:2], t[2][0:2]]
            o, i, b = [], [], [] #need to be reset, in case p was lying completely inside a privous tria  
            shifts = 0 #counting how many shifts for next vertex in p have been performed ot find vertex outside tria as starting point
            while isPointInTria(p[0], tria): #make sure that first vertex of p is outside tria
                if shifts >= len(p): #special case that whole p is in tria, all vertices of p are inside
                    self.log.info("Polygon p lies completely in tria {}".format(tria))
                    for start_p in range(len(p)-1): #### ASSUMING CLOSED P ###########
                        for segment in range(len(p)-1): ### ASSUMING CLOSED P #########
                            cp = intersection(tria[0], p[start_p], p[segment], p[segment+1])  ###### IMPORTANT TBD: tria[0] might be different for trias lying one over the other in different patches !!!!! ####
                                ###### ==> TBD: instead of starting with tria[0] always start with most S/SW corner !!! #######################
                            self.log.info("For start {} with segment {} cutting point: {}".format(start_p, segment, cp))
                            if cp:
                                if round(cp[0],7) == round(p[start_p][0],7) and round(cp[1],7) == round(p[start_p][1],7):
                                    cp = None #if cutting point is just the point we want to sart inside p this is okay, does not count for cutting point
                                else:
                                    break #there is a cutting point, so we need to check anohter start in p
                        if not cp: # No cutting point, meaning we found a line from tria[0] to p[p_start] that is not cutting any other segment of p and can thus be used as a line to create an outer polygon inside tria around p
                            o = tria #for the outer polygon to be triangulated go first along tria 
                            o.append(tria[0]) #back to tria[0]
                            for p_v in range(start_p,-1,-1): #go back to first point of of p
                                o.append(p[p_v])
                            for p_v in range(len(p)-2, start_p-1,-1): #go from last back to start in p ##### ASSUMING CLOSED P, as last is not added again as equal to p[0] ############
                                o.append(p[p_v]) ### as o is not closed we do not need to add again tria[0]
                            self.log.info("Outer Polygon around p inside tria is: {}".format(o))
                            p_inside_one_tria = True
                            o = [o] #o is list of outer polygons, here just o itself
                            i = [deepcopy(p)] #inner polygon is p  #### deepcopy required???
                            b = deepcopy(p) #as p is inside tria, all vertices of p are boundary from inner polygon p to polygon around p  ###deepcopy required???
                            ## old_trias.append(t) #tria t is replaced by triangulation of o ### Not needed any more as we have border vertices below
                            outer.extend(o), inner.extend(i), border.extend(b)
                            break #start_p was found
                    if o == []:
                        self.log.error("Outer Polygon around p in tria not found. Area not triangulated!")
                        return [], [], []
                    break #we do not need to shift further as we did already go around and handled p inside tria
                
                shifts += 1
                if not p_inside_one_tria: #if p is inside one tria, don't really shift vertices of p, to always have same triangulation of the tria containing p
                    p = p[1:] ############# TBD: SHIFTING DOES ASSUME CLOSED P, as verst vertex is ommitted and stays only if it is also last in the list !!! #########
                    p.append(p[0])
                    self.log.info("p[0] inside tria --> shifting poly {}".format(p))
                    self.log.info("       to poly {}".format(p))

            if not p_inside_one_tria: #if p is inside one tria, no PolyCutPoly required
                o, i, b = self.PolyCutPoly(tria, p)
                outer.extend(o), inner.extend(i), border.extend(b)
            if PointInPoly(tria[0], p) and PointInPoly(tria[1], p) and PointInPoly(tria[2], p): #special case that tria lies completely in p
                if keepInnerTrias: #new 11.04.2020 if tria is completely within in t and inner trias should be removed, we need to define this here
                    if elev != None: #if elevation should be adapted do this for inner trias
                        #inside_tria = deepcopy(t) ### 11.04.2020 WHY copy inside tria? Just adapt elevation !!! ##########
                        for tv in range(3):
                            #inside_tria[tv][2] = elev ### 11.04.2020 WHY copy inside tria? Just adapt elevation !!! ##########
                            t[tv][2] = elev
                        #new_trias.append(inside_tria) ### 11.04.2020 WHY copy inside tria? Just adapt elevation !!! ##########
                        self.log.info("Adapted elevation in inside tria. New Tria: {}".format(t)) #was format(inside_tria) ### 11.04.2020 WHY copy inside tria? Just adapt elevation !!! ##########
                else: #tria is completely within p and inner trias shall be removed
                    old_trias.append(t) #so remove it
                    
            if keepInnerTrias: # In case inside p will get new mesh later, we leave inner trias away
                for poly in i: # otherwise we will now triangulate inner polygosn with earclip    #### ERROR CHECKING ONLY ######
                    if len(earclipTrias(deepcopy(poly))) < len(poly) - 2: self.log.error("Earclip does only return {} trias for poly: {}".format(len(earclipTrias(deepcopy(poly))), poly))  #### ERROR CHECKING ONLY ######
                    for tria in earclipTrias(deepcopy(poly)): #earclip want's polygon without last vertex as returned by PolyCutPoly; earclip should always return clockwise order
                        if len(tria) < 3: self.log.error("Earclipp has returned tria with less then 3 vertices for poly: {}".format(poly))  #### ERROR CHECKING ONLY ######
                        new_v = [None, None, None]
                        for e in range(3):
                            new_v[e] = createFullCoords(tria[e][0], tria[e][1], t)
                            ############# TBD: Elevation change probably not required here, because it will always be set via border vertices later ?!? ==> NO!! See inner trias above! #########################
                            if elev != None: ### actually only for inner + border_v !!!!!!!!!!!!!!!!! ###
                                new_v[e][2] = elev
                        new_trias.append([new_v[0], new_v[1], new_v[2], t[3], t[4], t[5], t[6]])

            for poly in o: #outer polys have always to be earclipped, but no elevation/terrian change
                self.log.info("Earclipping outer poly: {}".format(poly)) ############### ERROR CHECKING, TO BE REMOVED ##############
                clipped_trias = earclipTrias(deepcopy(poly))
                self.log.info("Clipped Trias: {}".format(clipped_trias))
                if len(clipped_trias) != len(poly) - 2: self.log.error("Earclip does return {} trias for {} vertices for poly: {}".format(len(clipped_trias), len(poly), poly))  #### ERROR CHECKING ONLY ######
                for tria in clipped_trias: #earclip want's polygon without last vertex as returned by PolyCutPoly; earclip should always return clockwise order
                    if len(tria) < 3: self.log.error("Earclipp has returned tria with less then 3 vertices for poly: {}".format(poly))  #### ERROR CHECKING ONLY ######
                    if max_tria_angle(tria) > 175: self.log.warning("Earclip returend silver tria with max angle {}. Tria: {}".format(max_tria_angle(tria), tria))
                    new_v = [None, None, None]
                    for e in range(3):
                        new_v[e] = createFullCoords(tria[e][0], tria[e][1], t)
                    new_trias.append([new_v[0], new_v[1], new_v[2], t[3], t[4], t[5], t[6]])
                    self.log.info("+++ TRIA IN OUTER POLY APPENDED: {}".format(new_trias[-1])) ######## LOG JUST FOR TESTING, TO BE REMOVED ###########
                     
            if b != []: #we have border vertices, so there was a cut in this tria
                old_trias.append(t) #so this tria is replaced by trias of inner and outer polys ###### OPEN: BETTER REMOVE TRIAS IN DIFFERENT PARTS ABOVE DEPENDING ON CONTEXT ???? #########
        for nt in new_trias: #add all new trias
            self.atrias.append(nt)
            #### tbd: adapt elevation for all trias (only outer if p own mesh) and create for inner trias new terrain patches if terrain given
        for ot in old_trias: #and remove old ones
            self.log.info("Following Tria is removed: {}".format(ot))
            try: #as we might cross same tria several times there might several removals for same tria
                self.atrias.remove(ot)
            except ValueError:
                self.log.info("   was already removed...")
        
        ########### TBD: Better set elevation outside, to also distinguish there for profile elevation ... #######################
        if elev != None: #Adapt elevevation of border vertices
            for v in self.getAllVerticesForCoords(border):
                v[2] = elev
                
        #eliminate double border vertices   ##### OPEN: use set in complete function instead of list for border vertices? ################
        borderSet = set()  #set with all coords of border vertices in order to eliminate dolubles 
        for v in border:
            borderSet.add((round(v[0], 7), round(v[1], 7)))  # coords round to range of cm
        border = [] #now only take border vertices one time in list
        for v in borderSet:
            border.append(v)
                
        return outer, inner, border
                
                            
    
    def cutEdges(self, v, w, accuracy = 10):
        """
        Cuts all edges of trias that intersect with segment from vertex v to w in self.atrias.
        If existing vertices/edges are closer than accuracy in m, they will be used.
        Function returns all points on the cutting line (except endpoints, if they do not cut).
        Note: If edge is completely within a tria then nothing is cut.
              In that case the segment has to be inserted, then by just inserting the vertices of the edge.
        """
        self.log.info("Cutting area with edge from: {} to: {}.".format(v, w))
        cPs = [] #functions returns a list of vertices that are lying on intersection line v to w (either created or used within accuracy)
        new_trias = [] #trias to be added when cutting in patch
        old_trias = [] #old trias to be removed when cutting in patch
        for t in self.atrias: #go through all trias in area
            iv = [] #list of intersection vertices between line vw and edges of triangle t, could be between 0 and 3
            for edge in range(3): # go through edges of tria by index numbers
                cuttingPoint = intersection(v, w, t[edge][0:2], t[(edge+1)%3][0:2]) # modulo 3 returns to first vertex to close tria
                if cuttingPoint:
                    existing_vertex_close = False
                    for i in [edge, (edge+1)%3]: #check if v is too close to vertex of tria ONLY FOR ADJECENT vertices on edge  
                        if distance(t[i][0:2], cuttingPoint) < accuracy:
                            self.log.debug("   Cutting Point {} not inserted as too close to vertex of the triangle it is in.".format(cuttingPoint))
                            cPs.append(t[i][0:2]) ### Attention: adds all coordinates of t that are within accuracy, not just one
                            existing_vertex_close = True
                    if not existing_vertex_close:
                            cuttingPoint = (cuttingPoint[0], cuttingPoint[1], edge) #store number of edge cut as third element
                            iv.append(cuttingPoint)
                            cPs.append((cuttingPoint[0], cuttingPoint[1]))
            if len(iv) == 2:
                if iv[1][0] > iv[0][0] or (iv[1][0] == iv[0][0] and iv[1][1] > iv[0][1]):
                    iv[0], iv[1] = iv[1], iv[0] #make sure to always start with most western (or most southern if both have same west coordinate) cutting Point in order to always get same mesh for overlays
                self.log.debug("   Two intersections found at {}.".format(iv))
                
                edge = iv[0][2] ## start with edge with west/southern cutting point having index v_Index-1 (was inserted first)
                if iv[1][2] == (iv[0][2] + 1) % 3: #second cutting point lies on next edge
                    new_v0 = createFullCoords(iv[0][0], iv[0][1], t)
                    new_v1 = createFullCoords(iv[1][0], iv[1][1], t)
                    new_trias.append([ new_v0, t[(edge+1)%3], new_v1, t[3], t[4], t[5], t[6]]) 
                    new_trias.append([ new_v0, new_v1, t[(edge+2)%3], t[3], t[4], t[5], t[6]])
                    new_trias.append([ new_v0, t[(edge+2)%3], t[edge], t[3], t[4], t[5], t[6]])
                else: #second cutting point must lie on previous edge
                    new_v0 = createFullCoords(iv[0][0], iv[0][1], t)
                    new_v1 = createFullCoords(iv[1][0], iv[1][1], t)
                    new_trias.append([ new_v0, t[(edge+1)%3], t[(edge+2)%3], t[3], t[4], t[5], t[6]])
                    new_trias.append([ new_v0, t[(edge+2)%3], new_v1, t[3], t[4], t[5], t[6]])
                    new_trias.append([ new_v0,  new_v1, t[edge], t[3], t[4], t[5], t[6]])
                old_trias.append(t)                   
            elif len(iv) == 1:
                edge = iv[0][2]
                self.log.debug("   One intersection found at {}.".format(iv))
                new_v0 = createFullCoords(iv[0][0], iv[0][1], t)
                new_trias.append([ t[edge], new_v0, t[(edge+2)%3], t[3], t[4], t[5], t[6]])
                new_trias.append([ new_v0, t[(edge+1)%3], t[(edge+2)%3], t[3], t[4], t[5], t[6]])
                old_trias.append(t)
        for nt in new_trias:
            self.atrias.append(nt) #update area trias by appending new trias
        for ot in old_trias:
            self.atrias.remove(ot) #update area trias by by removing trias that are replaced by new ones
        self.log.info("  ... this cut returned {} cutting points.".format(len(cPs)))
        return cPs
    
    def triasInPoly(self, poly):
        """
        Returns list of indieces to trias that are that are intersecting or ale completely within poly.
        """
        self.log.info("Searching all trias in area in/intersecting poly: {}".format(poly))
        s = set()
        for t_index in range(len(self.atrias)):
            t = self.atrias[t_index]
            for i in range(3):  # 3 sides of triangle
                for j in range(len(poly) - 1):  # sides of poly
                    if intersection(t[i], t[(i+1)%3], poly[j], poly[j + 1]):  # current triangle intersects with an poly line
                        s.add(t_index) 
            if PointInPoly(t[0],poly):  # Check also that not complete Tria lies in poly by checking for first vertex of Tria
                s.add(t_index)  
            if isPointInTria(poly[0], t):  # Check also that not complete poly lies in current tria by checking for first vertex of poly
                s.add(t_index) 
        self.log.info("   ... {} trias of area found that belong to mesh triangles intersecting or within boundary.".format(len(s)))
        return s

    def ensureClockwiseTria(self, tria):
        """
        Checks if vertices of tria (in form of self.atria) is clockwise.
        If not order is changed to be clockwise
        """
        if not IsClockwise([tria[0][:2], tria[1][:2], tria[2][:2]]):
            self.log.info("Changing following tria to clockwise order: {}".format(tria))
            tria = [tria[2], tria[1], tria[0], tria[5], tria[4], tria[3], tria[6]]
        return tria

    def edges(self, poly=None):
        """
        Returns dictonary of all edges in area, where the key are endpoints (p, q) round to 7 digits
        and the values are lists with indeces to the trias in self.atrias and number of edge in tria.
        If poly is given only edges from trias in/intersecting poly are returned.
        """
        edges = {}
        if poly == None:
            tria_indeces = range(len(self.atrias))
        else:
            tria_indeces = self.triasInPoly(poly)
        for tx in tria_indeces:
            p = [] #list of points in tria
            for i in range(3): #get points of tria in p
                p.append( ( round(self.atrias[tx][i][0],7), round(self.atrias[tx][i][1],7)) )
            for i in range(3): #go through edges
                if (p[i][0], p[i][1], p[(i+1)%3][0], p[(i+1)%3][1]) in edges:
                    edges[ (p[i][0], p[i][1], p[(i+1)%3][0], p[(i+1)%3][1]) ].append([tx, i])
                elif (p[(i+1)%3][0], p[(i+1)%3][1], p[i][0], p[i][1]) in edges: #check if edge is with other vertex order in dictionary
                    edges[ (p[(i+1)%3][0], p[(i+1)%3][1], p[i][0], p[i][1]) ].append([tx, i])
                else: #edge not yet in dictionary
                     edges[(p[i][0], p[i][1], p[(i+1)%3][0], p[(i+1)%3][1])]=[[tx, i]]
        return edges

    
    def limitEdges(self, poly, limit):
        ############### PROBLEM: If tria on one side of the edge uses raster and the one of the other side is using pre-defined elevation
        ######################### then they will in X-Plane not be on the same level ---> Make sure that new vertex on split edge
        ######################### has same elevation in both trias ----> Solve when creating dsf vertices with different elelvation....
        """
        Limits the length of the edges poly to limit in meter.
        """
        self.log.info("Limit length of edges in poly {} to {}m.".format(poly, limit))
        edges = self.edges(poly)
        big_trias = {} #dictionary containg trias with long edges (key is index to tria in self.atrias and value is list of edge indices for edges too long)
        for pq, edge_refs in edges.items(): #key in dictionary ar coordinates of vertex p and q of edge, value is list with reference to tria where this edge is
            d = distance([pq[0], pq[1]], [pq[2], pq[3]])
            #if d > limit and (PointInPoly([pq[0], pq[1]], poly) or PointInPoly([pq[2], pq[3]], poly)): #select long edges only if at least one vertex is inside poly
            if d > limit and edgeInPoly([pq[0], pq[1]], [pq[2], pq[3]], poly): #select only edges longer than limit and inside or at least intersecting poly
                for e in edge_refs:
                    if e[0] in big_trias:
                        big_trias[e[0]].append(e[1])
                    else:
                        big_trias[e[0]] = [ e[1] ]
        old_trias = [] #list of trias with long edges to be removed
        new_trias = [] #list of trias with shorter edges to be created
        for tx, le in big_trias.items():
            t = self.atrias[tx]
            if len(le) == 1: #In tria t with index tx one edge with index le is too long
                cP = [0.5 * ( t[(le[0]+1)%3][0] + t[le[0]][0] ), 0.5 * ( t[(le[0]+1)%3][1] + t[le[0]][1] ) ]
                new_v = createFullCoords(cP[0], cP[1], t)
                new_trias.append([ t[le[0]], new_v, t[(le[0]+2)%3], t[3], t[4], t[5], t[6]])
                new_trias.append([ new_v, t[(le[0]+1)%3], t[(le[0]+2)%3], t[3], t[4], t[5], t[6]])
                old_trias.append(t)
            elif len(le) == 2: #In tria t two edges are too long, meaning it is important which was detected first to have same structure for all trias
                cP0 = [ 0.5 * ( t[(le[0]+1)%3][0] + t[le[0]][0] ), 0.5 * ( t[(le[0]+1)%3][1] + t[le[0]][1] ) ]
                cP1 = [ 0.5 * ( t[(le[1]+1)%3][0] + t[le[1]][0] ), 0.5 * ( t[(le[1]+1)%3][1] + t[le[1]][1] ) ]
                new_v0 = createFullCoords(cP0[0], cP0[1], t)
                new_v1 = createFullCoords(cP1[0], cP1[1], t)
                if (le[0]+1)%3 == le[1]: #second cutting point is on the following edge
                    new_trias.append([ t[le[0]], new_v0, t[(le[0]+2)%3], t[3], t[4], t[5], t[6]])
                    new_trias.append([ new_v0, t[(le[0]+1)%3], new_v1, t[3], t[4], t[5], t[6]])
                    new_trias.append([ new_v1, t[(le[0]+2)%3], new_v0, t[3], t[4], t[5], t[6]])
                else: #second cutting point is two edges away (=the edge before)
                    new_trias.append([ new_v0, t[(le[0]+1)%3], t[(le[0]+2)%3], t[3], t[4], t[5], t[6]])
                    new_trias.append([ new_v0, t[(le[0]+2)%3], new_v1, t[3], t[4], t[5], t[6]])
                    new_trias.append([ new_v0, new_v1, t[le[0]], t[3], t[4], t[5], t[6]])
                old_trias.append(t)
            elif len(le) == 3: #In tria t all three edges are tool long
                cP = [] #list for all three new Cutting points
                new_v =[] #list for all three new vertex coordinates
                for i in range(3): # inserted structure for 3 long vertices is always the same regardless which cP is inserted first
                    cP.append([0.5 * ( t[(i+1)%3][0] + t[i][0] ), 0.5 * ( t[(i+1)%3][1] + t[i][1] ) ])
                    new_v.append(createFullCoords(cP[-1][0], cP[-1][1], t))
                for i in range(3):
                    new_trias.append([ t[i], new_v[i], new_v[(i+2)%3], t[3], t[4], t[5], t[6]])
                new_trias.append([new_v[i], new_v[(i+1)%3], new_v[(i+2)%3], t[3], t[4], t[5], t[6]])
                old_trias.append(t)
        for nt in new_trias:
            self.atrias.append(nt) #update area trias by appending new trias
        for ot in old_trias:
            self.atrias.remove(ot) #update area trias by by removing trias that are replaced by new ones
        self.log.info("  ... limiting replaced {} trias with {} new trias having shorter edges.".format(len(old_trias), len(new_trias)))
        if len(new_trias) > 0: #New trias could still have longer edges
            self.limitEdges(poly, limit) #shorten again
        ########## This funciton might be improved to go only through edges in new_trias instead starting from scratch in recursions

    def extractMeshToObjFile(self, poly, filename, type_def, file_info="# MUXP Mesh extract"):
        """
        Extracts all pyhsical trias of area which are in poly to an Wavefront .obj File with filename.
        Existing files will be overwritten!
        """
        extract_atrias = dict()  # dictionary of lists of area trias, that have to be extracted; keys are IDs of patches they belong to
        vertices = dict()  # dictionary for unique coordinates of trias as keys and [elevation, index] as value
        normals = dict()  # dictionary for vertex normals
        v_raster_elev = dict()  # dictionary with True as value in case elevation at coordinates is from raster
        self.log.info("**** EXTRACTED VERTICES FOR OBJ FILE INCLUDING ELEVATIONS AS IS IN MEMORY *****")  ### TESTING ONLY ###

        select_from_cut = False
        if type_def.find("inside_polygon") < 0:  # using cut option is default
            polysouter, polysinner, borderv = self.CutPoly(poly)  # just cut shape in mesh
            select_from_cut = True

        for t in self.atrias:  # go through all trias in area
            if not t[6]:  # Patch not defined for that tria
                self.log.error("Patch does not exist for tria: {} --> not exported!!".format(t))
                continue
            if self.dsf.Patches[t[6]].flag == 1:  # for the moment only export physical triangles !!!!!!
                if (select_from_cut and PointInPoly(tria_center(*t[:3]), poly)) or \
                        (PointInPoly(t[0][0:2], poly) and PointInPoly(t[1][0:2], poly) and PointInPoly(t[2][0:2], poly)):
                    # in case of cut select trias with center point inside poly in case of default type select
                    # all all trias with all vertices inside poly (no cut)
                    terrain_id = self.dsf.Patches[t[6]].defIndex
                    #self.log.info("Tria with flag {} and terrain {} to be exported: {}".format(self.dsf.Patches[t[6]].flag, terrain_id, t))
                    if terrain_id not in extract_atrias.keys():
                        extract_atrias[terrain_id] = [deepcopy(t)]
                    else:
                        extract_atrias[terrain_id].append(deepcopy(t))  # deepcopy, to be able to change elevation
                    for v in range(3):
                        extract_atrias[terrain_id][-1][v][2] = self.dsf.getVertexElevation(*t[v][:3])  #### NEW: use elevation, no raster value
                        vc = (round(t[v][0], 7), round(t[v][1], 7))
                        vn = (round(t[v][3], 4), round(t[v][4], 4))
                        self.log.info("{}  elev: {}".format(vc, t[v][2]))  ### TESTING ONLY ####
                        if vc not in vertices:
                            vertices[vc] = [self.dsf.getVertexElevation(*t[v][:3]), len(vertices)]
                            # use always the elevation, but have info if raster elevation was used
                            if t[v][2] == -32768:
                                v_raster_elev[vc] = True
                        if vn not in normals:
                            normals[vn] = len(normals)

        with open(filename, "w", encoding="utf8", errors="ignore") as f:
            center_lines_offset = 0  # in case of non centric export we have not v and vn for CENTER COORDINATES
            f.write(file_info)
            if type_def.find("non_centric") < 0:
                center = CenterInAtrias(extract_atrias)
                center_lines_offset = 1  # we need 3 lines for v and line vn for center coordinates
                f.write("o CENTER_Coordinates\n")
                f.write("# coordinates relative to center: {} {} {}\n".format(center[0], center[1], center[2]))
                if type_def.find("xp_coordinates") < 0:  # Mercator projection is default
                    center[0], center[1] = round(lon2x(center[0])), round(lat2y(center[1]))  # use Mercator projection
                    center[2] = round(center[2])  # center elevation also full meter
                    f.write("# used in Mercator projection: {} {} {}\n".format(center[0], center[1], center[2]))
                for i in range(3):  # Write center coordinates down scaled, so that it is nearly not visible
                    f.write("v {} ".format((int(center[i] / 1000000)) / 1000))
                    f.write("{}".format(int((center[i] - (int(center[i] / 1000000) * 1000000)) / 1000) / 1000))
                    f.write(" {}\n".format((center[i] - (int(center[i] / 1000)) * 1000) / 1000))
                f.write("vn 0 0 1\n")
                f.write("f 1//1 2//2 3//1\n")
            else:  # non centric export
                center = [0, 0, 0]
            f.write("o MESH\n")
            if type_def.find("xp_coordinates") < 0:  # Mercator is default
                for vc in vertices:
                    f.write("v {} {} {}\n".format(round(lon2x(vc[0]) - center[0], 3),
                                                  round(lat2y(vc[1]) - center[1], 3), vertices[vc][0] - center[2]))
            else:
                for vc in vertices:
                    v_string = "v {} {} {}".format(round(vc[0] - center[0], 3),
                                                   round(vc[1] - center[1], 3), vertices[vc][0] - center[2])
                    if vc in v_raster_elev:
                        v_string += "  # elev from raster"
                    f.write("{}\n".format(v_string))
            for vn in normals:
                f.write("vn {} {} {}\n".format(vn[0], vn[1], sqrt(1 - vn[0]*vn[0] - vn[1]*vn[1])))
            previous_written_material_name = None
            for terrain_id in extract_atrias:
                terrain_name = self.dsf.DefTerrains[terrain_id]
                if terrain_name == "terrain_Water":
                    material_name = "terrain_Water"
                else:
                    material_name = "solid_default_terrain"
                if previous_written_material_name != material_name:  # only write material change to file if it changed
                    f.write("usemtl {}\n".format(material_name))
                    previous_written_material_name = material_name
                ######### TBD: export also other terrain types #####################
                ######### TBD: WRITE MTL FILE AND INCLUDE USAGE IN .OBJ FILE #######
                for t in extract_atrias[terrain_id]:
                    f.write("f")
                    for v in range(3):
                        f.write(" {}//{}".format(vertices[(round(t[v][0], 7), round(t[v][1], 7))][1] +
                                                 3 * center_lines_offset + 1,  # 3 CENTER v coordinates + start at 1
                                                 normals[(round(t[v][3], 4), round(t[v][4], 4))] +
                                                 center_lines_offset + 1))  # 1 CENTER vn coordinate + start at 1
                    f.write("\n")

    def insertMeshFromObjFile(self, filename, logname, poly, terrain, type, dsf):
        """
        Inserts mesh with only physical trias from an .obj filename and inserts it in area.
        The outer polygon of file-mesh is connected to the poly using triangulation. All this
        new trias will be set to type terrain.
        Mesh must not have different vertex definitions for same x,y coordinates and ther must be no overlapping/
        double faces.
        To have room for the mesh, the mesh is first cut by poly and all inner trias are removed.
        """
        self.log.info("Inserting now mesh from: {} into: poly: {} using terrain: {}".format(filename, poly, terrain))
        if type == "exact_match_removal_poly":  # the shape of inserting mesh must have same edges as existing mesh in dsf
            trias_to_be_removed = []
            for t in self.atrias:  # go through all trias in area
                if PointInPoly(t[0][0:2], poly) and PointInPoly(t[1][0:2], poly) and PointInPoly(t[2][0:2], poly):
                    trias_to_be_removed.append(t)
            for t in trias_to_be_removed:
                self.atrias.remove(t)  # tria is removed to be later replaced by trias from .obj
        elif type == "default":  # default is filling gap
            polysouter, polysinner, borderv = self.CutPoly(poly, None, False)  # False for not keeping inner trias\
            # None for elevation as only new terrain should get elevation
            borderv, log_info = sortPointsAlongPoly(borderv, poly)
            self.log.info("Logs from sorting Points along Poly: {}\n".format(log_info))
            borderv = borderv[borderv.index(min(borderv)):] + borderv[:borderv.index(min(borderv))]
            #  borderv start now with the most south-west corner
            borderv.append(borderv[0])  # make it a closed poly
            if not IsClockwise(borderv):
                borderv.reverse()  # outer polygon for later triangulation should be clockwise
            for v in borderv:
                self.log.info("Border Vertex after Cut: {}".format(v))

        obj_trias, obj_outline = read_obj_file(filename, logname, terrain, self)

        if type == "cut_obj_outline":  # now we have outline we can remove from current mesh via cut
            borderland = obj_outline  # exact match with cut, no borderland; just border of the outer edges of inserted mesh
            polysouter, polysinner, borderv = self.CutPoly(obj_outline, None, False)  # False for not keeping trias
            match_border_with_existing_vertices(obj_outline, obj_trias, self.atrias)

        if type == "exact_match":  # in case of exact match we remove all trias inside obj_outline
            match_border_with_existing_vertices(obj_outline, obj_trias, self.atrias)
            borderland = obj_outline  # exact match, no borderland; just border of the outer edges of inserted mesh
            trias_to_be_removed = []
            for t in self.atrias:  # go through all trias in area
                if PointInPoly(tria_center(*t[:3]), obj_outline):  # remove trias with center inside our imported mesh
                    trias_to_be_removed.append(t)
            for t in trias_to_be_removed:
                self.atrias.remove(t)  # tria is removed to be later replaced by trias from .obj

        kmlExport2(dsf, [borderland], self.atrias, filename + "_removed.kml")  ### TESTING ONLY - TB REMOVED  ALSO DSF PARAMETER FOR THIS FUNCTION !! ###

        # insert all trias from .obj file in trias of that MUXP area
        for t in obj_trias:
            self.atrias.append(t)

        if type == "cut_obj_outline":  # in case of cut we need to insert vertices of cut also in added obj_trias
            for vertex in borderv:
                self.splitCloseEdges(vertex)

        if type == "exact_match_removal_poly":  # removal of trias already done above
            borderland = obj_outline  # exact match, no borderland; just border of the outer edges of inserted mesh

        if type == "default":  # fil gap between existing dsf mesh and .obj map with trias of type default_terrain
            patch_id_terrain = self.getPatchID(terrain)
            borderland = borderv + obj_outline  # area between inner/outer poly to be triangulated, not closed for earclip
            self.log.info("Borderland to be earclipped: {}".format(borderland))
            trias = earclipTrias(borderland)
            self.log.info("Earclip returned {} trias for {} vertices.".format(len(trias), len(borderland)))
            for tria in trias:
                new_v = [None, None, None]
                for e in range(3):
                    elev_found = False  # go through all existing vertices of trias to find elevation at coords
                    for t in self.atrias:
                        for v in range(3):
                            if (round(tria[e][0], 7), round(tria[e][1], 7)) == (round(t[v][0], 7), round(t[v][1], 7)):
                                elev = t[v][2]
                                elev_found = True
                                self.log.info("Elevation of borderland vertex {} is {}".format(tria[e], elev))
                        if elev_found: break
                    if not elev_found:
                        self.log.error("No elevation found for borderland vertex: {}. Mesh not inserted!".format(tria[e]))
                        return -2
                    new_v[e] = [tria[e][0], tria[e][1], elev, 0, 0]
                    # This version only creates simple vertices without vertex normals and without s/t coordinates
                self.atrias.append([new_v[0], new_v[1], new_v[2], [None, None], [None, None], [None, None], patch_id_terrain])
                self.log.info("Borderland Tria added: {}".format(self.atrias[-1]))
                # As tria is completely new, there is no pool/patchID where tria is inside, so None
        return borderland

    def calculate_vertex_normals(self, poly):
        """
        Calculates vertex normals for all trias that lay fully in poly and assigns them to all of these vertics.
        Note: vertices around poly are still required to calculate normals of vertices inside poly.
        """

        def dot_product(v1, v2):
            return sum((a * b) for a, b in zip(v1, v2))
        def length(v):
            return sqrt(dot_product(v, v))
        def v_angle(v1, v2):  # returns co-sinus value of angle #### FOR THE MOMENT REALL RETURNS ANGLE
            length_prod = length(v1) * length(v2)
            if length_prod == 0:
                return 0  # avoid error
            cos_angle = dot_product(v1, v2) / length_prod
            if cos_angle > 1:
                return acos(1)
            if cos_angle < -1:
                return acos(-1)
            return acos(cos_angle)

        self.log.info("**** CALCULATING VERTEX NORMALS *****")  ### TESTING ONLY ###
        normal_dict = {}  # dictionary that contains for (x, y) coords a  list with the sum of face normal vectors
        nl_dict = {} ### JUST Treturn acos(dot_product(v1, v2) / length_prodESTING ####
        # of attached trias in [0:3]
        for t in self.atrias:  # go through all trias in area
            if self.dsf.Patches[t[6]].flag:  # for the moment only export physical triangles !!!!!!
                if PointInPoly(t[0][:2], poly) or PointInPoly(t[1][:2], poly) or PointInPoly(t[2][:2], poly):
                    ### TO BE OPTIMIZED: REMEMBER WHICH POINTS ARE IN POLY TO AVOID SAME CHECK BELOW ######
                    tc = [(round(t[0][0], 7), round(t[0][1], 7), round(self.dsf.getVertexElevation(*t[0][:3]), 2)),
                          (round(t[1][0], 7), round(t[1][1], 7), round(self.dsf.getVertexElevation(*t[1][:3]), 2)),
                          (round(t[2][0], 7), round(t[2][1], 7), round(self.dsf.getVertexElevation(*t[2][:3]), 2))]
                    u = distance_vector(tc[2], tc[0])  # span tria with u, v vectors starting at 3rd point in tria
                    v = distance_vector(tc[2], tc[1])
                    self.log.info("tria: {}".format(tc))
                    self.log.info("  u: {}   v: {}".format(u, v))  # TO BE REMOVED -- TESTING ONLY -- #############
                    # COULD BE MORE EFFICIENT TO CALCULATE DISTANCE AS THIS IS JUST FOR X AND Y SEPARATE !!! ##########
                    tn = [u[1]*v[2] - u[2]*v[1], u[2]*v[0] - u[0]*v[2], u[0]*v[1] - u[1]*v[0]]  # normal vector for tria t
                    tn_length = sqrt(tn[0]**2 + tn[1]**2 + tn[2]**2)
                    if tn_length:  # avoid division by zero
                        l = 1 / sqrt(tn[0]**2 + tn[1]**2 + tn[2]**2)  # set length of each face vector to 1
                    else:
                        l = 1
                        self.log.warning("Zero length normal vector for tria: {}".format(t))
                    #l = 2  # tn is already created to reflect half size of the tria itself, so okay for weighting
                    # tn[1] *= -1  # According to dsf spec the y coordinate is positive for going south, by calc above it is negative BUT actually it is positive for North
                    if tn[2] < 0:  # make sure that z-vector is always showing upside
                        l *= -1
                    tnn = [l * tn[0], l*tn[1], l*tn[2]]  # face normal on tria t normalized to length 1
                    self.log.info("  Normal vector for tria (weighted by tria size): {}".format(tnn))
                    for i in range(3):
                        vc2 = tc[i][0:2]  # just first two coordinates of tria vertices
                        if PointInPoly(vc2, poly):
                            # following line calculates angle of tria at vertex vc2 for weighting vertex normal
                            angle = v_angle([tc[(i-1)%3][0] - tc[i][0], tc[(i-1)%3][1] - tc[i][1], tc[(i-1)%3][2] - tc[i][2]], [tc[(i+1)%3][0] - tc[i][0], tc[(i+1)%3][1] - tc[i][1], tc[(i+1)%3][2] - tc[i][2]])
                            if vc2 not in normal_dict:
                                normal_dict[vc2] = [angle*tnn[0], angle*tnn[1], angle*tnn[2]]
                                nl_dict[vc2] = [tnn]
                            else:
                                normal_dict[vc2] = [normal_dict[vc2][0] + angle*tnn[0], normal_dict[vc2][1] + angle*tnn[1], normal_dict[vc2][2] + angle*tnn[2]]
                                nl_dict[vc2].append(tnn)

        for v in normal_dict:  # setting all vertex normals in dict to length 1
            vn = normal_dict[v]
            l = 1 / sqrt(vn[0] ** 2 + vn[1] ** 2 + vn[2] ** 2)
            normal_dict[v] = [l*vn[0], l*vn[1], l*vn[2]]
            self.log.info("Vertex {} gets vertex normal: {}".format(v, vn))
            self.log.info("   Based on following face normals: {}".format(nl_dict[v]))

        for t in self.atrias:  # now check all vertices incl. non physical ones if they get new normal vector
            for v in t[:3]:
                if (round(v[0], 7), round(v[1], 7)) in normal_dict:
                    self.log.info("Setting for {} normal to {}".format(v, normal_dict[(round(v[0], 7), round(v[1], 7))]))
                    v[3] = normal_dict[(round(v[0], 7), round(v[1], 7))][0]  # positive value to east
                    v[4] = normal_dict[(round(v[0], 7), round(v[1], 7))][1]  # positive value to south (in XP spec BUT positive is to North !!!)
                    # direction upwards is calculated by XP; possible as the vector is normalized
    
    def createDSFVertices(self, elevscal=1):
        """
        For the area this function will find for all new vertices created in the area that
        have not yet assigned a vertex in dsf vertex pool an according vertex in the pool.
        It allows also submeter elevations when elevscal (value in meter) is below 1.
        When elevscal=1 either the raster reference -32768.0 is used or existing elevations per vertex (which might also allow submeter)
        Important: All trias require reference to trias they are inside in the orginal dsf. This is required to get the correct scalings for the area.
        Important 2: This function sets direct elevation for vertices in case elevscal is below 1.
        OPTION FOR FUTURE: use area limits for scaling lat/lon values.
        """
        ############## TBD: Also adapt the vertex normals (perhaps only in case dsf has no raster) ################
        newPools = [] # create new pools for the new vertices, these are the according indices  ##### TBD: check for existing pools first that might be used ########
        for t in self.atrias:
            for vt in range(3): #all vertices of tria t 
                count = 0 #counting how many coordinates are still the same as the referenced vertex in dsf
                if t[vt+3][0] != None and t[vt+3][1] != None: #in case of completely new tria we have no previous vertices and new ones need to be created in any case
                    for vti in range(len(t[vt])):
                        if round(t[vt][vti], 7) != round(self.dsf.V[t[vt+3][0]][t[vt+3][1]][vti], 7):  #### NEW 17.12. compare rounded to 1 cm #####
                            self.log.info("Reference for vertex {} not correct any more. {} differs to {}!".format(self.atrias.index(t), t[vt][vti], self.dsf.V[t[vt+3][0]][t[vt+3][1]][vti]))
                            break
                        count += 1
                if len(t[vt]) != count: #the reference for this vertex to the pool is not correct any more, new vertex needs to be inserted in dsf
                    v = deepcopy(t[vt]) #v has now deepcopy of all coordinates of that vertex that is to be inserted in the dsf
                    poolID4v = None #Searching for the pool ID for vertex v
                    #################### NEW 05.04.2020 commented two lines below; submeter elevation is only used for vertices assigned elevation; all ohters could stay with raster elevation ##############
                    #if elevscal < 1 and v[2] < -32765: #we want to get submeter elevations but have vertex referencing raster
                    #    v[2] = self.dsf.getVertexElevation(v[0], v[1], v[2]) #make sure that v[2] is real elevation and not using raster (with raster no submeter); only works because raster is there
                    for i in newPools:
                        if len(v) == len(self.dsf.Scalings[i]): #does size of scaling vector / number of planes for pool fit
                            counter = 0
                            for j in range(len(v)): #check for each plane j if v could fit between minimum and maximum reach of scale
                                if v[j] >= self.dsf.Scalings[i][j][1] and v[j] <= self.dsf.Scalings[i][j][1] + self.dsf.Scalings[i][j][0]:
                                    counter += 1
                                elif abs(v[j] - self.dsf.Scalings[i][j][1]) < 1e-7:   #### NEW 17.12. compare rounded to 1 cm #####
                                    self.log.warning("Current vertex {} moved slightly out of pool bounds. Set plane {} to minimum {}".format(v, j, self.dsf.Scalings[i][j][1]))
                                    v[j] = self.dsf.Scalings[i][j][1]
                                    t[vt][j] = self.dsf.Scalings[i][j][1]
                                    counter += 1
                                elif abs(v[j] - self.dsf.Scalings[i][j][1] - self.dsf.Scalings[i][j][0]) < 1e-7:   #### NEW 17.12. compare rounded to 1 cm #####
                                    self.log.warning("Current vertex {} moved slightly out of pool bounds. Set plane {} to maximum {}".format(v, j, self.dsf.Scalings[i][j][1] + self.dsf.Scalings[i][j][0]))
                                    v[j] = self.dsf.Scalings[i][j][1] + self.dsf.Scalings[i][j][0]
                                    t[vt][j] = self.dsf.Scalings[i][j][1] + self.dsf.Scalings[i][j][0]
                                    counter += 1
                                else:
                                    break
                            if len(v) == counter:  #all values of v are within range of scale for pool i
                                poolID4v = i #existing pool id found fulfilling all requirements                            
                                break
                    if poolID4v != None: #existing pool was found
                        matchfound = False
                        for ev_index, ev in enumerate(self.dsf.V[poolID4v]): #check for all existing vertices ev if they match v already ########### NEW 31.3.2020 enumerate #######
                            counter = 0
                            for i in range(len(v)): #check for all planes/coordinates whether they are nearly equal
                                if abs(ev[i] - v[i]) >= self.dsf.Scalings[poolID4v][i][0] / 65535: #if difference is lower than scale multiplier both coordinates would end up same after endcoding, so they match
                                    break
                                counter +=1
                            if counter == 2: ###################### NEW 31.03.2020 in order to handle issue for limit edges on raster and set elev. trias ###########
                                self.log.warning("  Vertex {} is at same location as {} but different elevations!!".format(v, ev))
                                ### We want on each coordinate same elevation, so let's adapt the lower elevated one to the higher (to avoid staying with unpredictable raster value for default -32768)
                                if ev[2] < v[2]:
                                    self.dsf.V[poolID4v][ev_index][2] = v[2] #adapt lower existing vertex elevation with elevation of higher new vertex
                                else:
                                    v[2] = ev[2] #adapt lower new vertex with elevation of existing higher one
                                self.log.info("      Now new vertex has elevation {}m".format(self.dsf.V[poolID4v][ev_index][2]))
                                ### We also need to continue check if same vertex can be used or new vertex has to be created because of different higher coordinates
                                for i in range(3,len(v)): #check for all planes/coordinates whether they are nearly equal
                                    if abs(ev[i] - v[i]) >= self.dsf.Scalings[poolID4v][i][0] / 65535: #if difference is lower than scale multiplier both coordinates would end up same after endcoding, so they match
                                        break
                                    counter +=1
                            if counter == len(v): #matching vertex found          #### NEW 31.03.2020: was before first if case ####
                                t[vt+3] = [poolID4v, ev_index]  #### NEW 31.03.2020  was before set to [poolID4v, self.dsf.V[poolID4v].index(ev)]
                                self.log.info("  Vertex {} equals vertex {} in existing Pool with index {} .".format(v, ev, poolID4v))
                                matchfound = True
                                break
                            if counter > 2: ##### NEW 31.03.2020: was >=, but == handled above #########
                                self.log.info("  Vertex {} is at same location as {} but different higher coordinate {}!!".format(v, ev, counter))
                        if not matchfound:       
                            self.dsf.V[poolID4v].append(v)
                            t[vt+3] = [poolID4v, len(self.dsf.V[poolID4v])-1] #change reference in area tria vertex to the last vertex in existing pool
                            self.log.info("  Vertex {} inserted in existing pool no. {}.".format(v, poolID4v))
                    else: #no existing pool fulfilling requirements was found, so new pool has to be created and added with v
                        if len(self.dsf.V) >= 65535: #reached maximum number of pools, no pool could be added any more
                            self.log.error("DSF File already has maximum number of point pools. Addtional pools required for change can not be added!!!")
                            return -1
                        self.dsf.V.append([v])
                        self.log.info("New Pool required to insert vertex: {}".format(v))
                        if t[vt+3][0] == None: #completele new tria in completely new patch, so no scaling available
                            scal_id = len(self.dsf.Scalings) - 1  # New 13.8.20: We need to find scaling with at minimum 5 values
                            while len(self.dsf.Scalings[scal_id]) < 5 and scal_id >= 0:
                                self.log.info("Scaling id {} has not enough coordinates, check for next ...".format(scal_id))
                                scal_id -= 1
                            self.dsf.Scalings.append([deepcopy(self.dsf.Scalings[scal_id][0]), deepcopy(self.dsf.Scalings[scal_id][1]),deepcopy(self.dsf.Scalings[scal_id][2]),deepcopy(self.dsf.Scalings[scal_id][3]),deepcopy(self.dsf.Scalings[scal_id][4])]) ############## This is a dirty soltion --- TBD ###############
                            ############################### BAD IMPLEMENTATION ABOVE #### Actually new scaling has to be defined based on area and typical s/t coordinates for that tile ##########################
                        else:
                            self.dsf.Scalings.append(deepcopy(self.dsf.Scalings[t[vt+3][0]])) #get scalings from the original tria vertex the new vertex is inside
                        ########## HOWEVER NEW VERTEX MIGHT BE OUTSIDE THESE SCALINGS --> check and adapt if required AFTER elevation was adapted as needed
                        if elevscal < 1: #for given submeter elevation pool-scaling has to be adapted
                            if v[2] < -32767:  # In case of Raster elevation take default scaling to avoid rounding errors  ### NEW 27.10.20 ###
                                self.log.info("First vertex for new Pool has Raster elevation. Create this Pool now with default scaling in order to avoid rounding errors.")
                                self.dsf.Scalings[-1][2][0] = 32268  # so with this Pool we can reach from -32768 to -500m; above use regular Pool (## 65535 * elevscal caused also rounding issues##)
                                self.dsf.Scalings[-1][2][1] = -32768  # Off-Set is exact RASTER Elevation (for exact matching), no need to go deeper
                            else: ### Following two lines are else
                                self.dsf.Scalings[-1][2][0] = int(65535 * elevscal)  # new multiplier based on required scaling for elevation defined for new pool
                                if self.elev_base_min < -1000:  # there was no usabale base elevation (e.g. only raster elevation present)
                                    self.dsf.Scalings[-1][2][1] = int(-10 + int((v[2] + 10) / (65535 * elevscal)) * (65535 * elevscal))  # offset for elevation of v, starting with -10m allows also small negative values at coasts; for deeper values the check below will set a lower sacaling
                                else:
                                    self.dsf.Scalings[-1][2][1] = self.elev_base_min  # use same base as original mesh; if new vertices will be lower, pool will be adapted below when scale is checked ## NEW 18.12.20
                                self.log.info("This new pool received base elevation of {} meters and allows to go additional {} meters up".format(self.dsf.Scalings[-1][2][1], self.dsf.Scalings[-1][2][0]))
                        ## Check new scaling for vertex and adapt as required based on multipliers / offsets give
                        scale_checked = False
                        while not scale_checked:
                            scale_checked = True #assume test will passed, will be set False if on check does not pass
                            for j in range(len(v)): #check for each plane j if v could fit between minimum and maximum reach of scale
                                if v[j] < self.dsf.Scalings[-1][j][1]: #v at plane j is lower than scaling allows
                                    if abs(v[j] - self.dsf.Scalings[-1][j][1]) < 1e-7:  #### NEW 17.12. compare rounded to 1 cm #####
                                        self.log.warning("Current vertex {} moved slightly out of pool bounds. Set plane {} to minimum {}".format(v, j, self.dsf.Scalings[-1][j][1]))
                                        v[j] = self.dsf.Scalings[-1][j][1]
                                        t[vt][j] = self.dsf.Scalings[-1][j][1]
                                    else:
                                        self.log.info("  Vertex in plane {} has value {} and thus lower than allowed scaling minimum {}.".format(j, v[j], self.dsf.Scalings[-1][j][1]))
                                        self.dsf.Scalings[-1][j][1] -= self.dsf.Scalings[-1][j][0] #subtract one scalefactor from base
                                        scale_checked = False #check if new scaling fits
                                        self.log.warning("  Vertex {} does not fit to scaling. Reduced scaling base for plane {} to {}!".format(v, j, self.dsf.Scalings[-1][j][1]))
                                if v[j] > self.dsf.Scalings[-1][j][1] + self.dsf.Scalings[-1][j][0]: #v at plane j is higher than scaling allows
                                    if abs(v[j] - self.dsf.Scalings[-1][j][1] - self.dsf.Scalings[-1][j][0]) < 1e-7:  #### NEW 17.12. compare rounded to 1 cm #####
                                        self.log.warning("Current vertex {} moved slightly out of pool bounds. Set plane {} to maximum {}".format(v, j, self.dsf.Scalings[-1][j][1] + self.dsf.Scalings[.1][j][0]))
                                        v[j] = self.dsf.Scalings[-1][j][1] + self.dsf.Scalings[-1][j][0]
                                        t[vt][j] = self.dsf.Scalings[-1][j][1] + self.dsf.Scalings[-1][j][0]
                                    else:
                                        self.log.info("  Vertex in plane {} has value {} and thus higher than allowed scaling maximum {}.".format(j, v[j], self.dsf.Scalings[-1][j][1] + self.dsf.Scalings[-1][j][0]))
                                        self.dsf.Scalings[-1][j][1] += self.dsf.Scalings[-1][j][0] #add one scalefactor to base
                                        scale_checked = False #check if new scaling fits
                                        self.log.warning("  Vertex {} does not fit to scaling. Increased scaling base for plane {} to {}!".format(v, j, self.dsf.Scalings[-1][j][1]))
                        poolID4v = len(self.dsf.Scalings) - 1 #ID for the pool is the last one added
                        self.log.info("  New pool with index {} and scaling {} added to insert vertex {}.".format(poolID4v, self.dsf.Scalings[poolID4v], v))
                        newPools.append(poolID4v)
                        t[vt+3] = [len(self.dsf.V)-1, 0] #change reference in area tria vertex to the first vertex in new pool
                else:
                    self.log.info("Vertex {} unchanged. Index to pool {} reused.".format(t[vt], t[vt+3][0]))
        return 0

    def rasterSquares(self, latS, latN, lonW, lonE):
        """
        Yields for a bounding rectangle with latS, latN, lonW, lonE all squares of raster
        that are inside or intersecting bounding rectangle.
        For each square [x, y] indeces to dsf.Raster[0] (assumed that elevation raster is lowest layer)
        and [[x1,y1], [x2,y2], [x3,y3], [x4, y4]] corner coordinates of square and [cx,cy] the coordinates
        of the center of the square.
        """
        #### Get index for raster pixel SW (yS, xW) for area to be exported
        xW = abs(lonW - int(self.dsf.Properties["sim/west"])) * (self.dsf.Raster[0].width - 1) # -1 from widht required, because pixels cover also boundaries of dsf lon/lat grid
        yS = abs(latS - int(self.dsf.Properties["sim/south"])) * (self.dsf.Raster[0].height - 1) # -1 from height required, because pixels cover also boundaries of dsf lon/lat grid
        if self.dsf.Raster[0].flags & 4: #when bit 4 is set, then the data is stored post-centric, meaning the center of the pixel lies on the dsf-boundaries, rounding should apply
            xW = round(xW, 0)
            yS = round(yS, 0)
        xW = int(xW) #for point-centric, the outer edges of the pixels lie on the boundary of dsf, and just cutting to int should be right
        yS = int(yS) 
        
        #### Get index for raster pixel NE (yN, xE) for area to be exported
        xE = abs(lonE - int(self.dsf.Properties["sim/west"])) * (self.dsf.Raster[0].width - 1) # -1 from widht required, because pixels cover also boundaries of dsf lon/lat grid
        yN = abs(latN - int(self.dsf.Properties["sim/south"])) * (self.dsf.Raster[0].height - 1) # -1 from height required, because pixels cover also boundaries of dsf lon/lat grid
        Rcentricity = "point-centric"
        if self.dsf.Raster[0].flags & 4: #when bit 4 is set, then the data is stored post-centric, meaning the center of the pixel lies on the dsf-boundaries, rounding should apply
            xE = round(xE, 0)
            yN = round(yN, 0)
            Rcentricity = "post-centric"
        xE = int(xE) #for point-centric, the outer edges of the pixels lie on the boundary of dsf, and just cutting to int should be right
        yN = int(yN)
        
        #### Define relevant info for raster to be used later ####
        Rwidth = self.dsf.Raster[0].width
        xstep = 1 / (Rwidth - 1)  ##### perhaps only -1 when post-centric ---> also above !!! ########################################
        xbase = int(self.dsf.Properties["sim/west"])
        Rheight = self.dsf.Raster[0].height
        ystep = 1 / (Rheight -1)  ##### perhaps only -1 when post-centric ---> also above !!! ########################################
        ybase = int(self.dsf.Properties["sim/south"])
        if Rcentricity == "post-centric": #if post-centricity we have to move dem pixel half width/hight to left/down in order to get pixel center on border of dsf tile
            cx = 0.5 * xstep 
            cy = 0.5 * ystep
        else:
            cx = 0
            cy = 0
        for x in range(xW, xE+1):
            for y in range (yS, yN+1):
                indices = [x, y]
                corners = [ [xbase + x*xstep - cx, ybase + y*ystep - cy],
                            [xbase + x*xstep - cx, ybase + (y+1)*ystep - cy],
                            [xbase + (x+1)*xstep - cx, ybase + (y+1)*ystep - cy],
                            [xbase + (x+1)*xstep - cx, ybase + y*ystep - cy]      ]
                center = [xbase + (x+0.5)*xstep - cx, ybase + (y+0.5)*ystep - cy]
                yield indices, corners, center

                
    def getPatchID(self, terrain, flag=1, near=0.0, far=-1.0):
        """
        Returns PatchID for a patch with given terrain, flag, near/far values.
        Creates a new patch if no such patch is existent.
        ###### TBD: Really search for such a patch. This version only creates new patches!!! ###########
        """
        terrain_id = 0 #find terrain id for new patch that includes trias for runway
        self.log.info("Current Terrain Definitons in dsf: {}".format(self.dsf.DefTerrains))
        while terrain_id < len(self.dsf.DefTerrains) and self.dsf.DefTerrains[terrain_id] != terrain:
            terrain_id += 1
        if terrain_id == len(self.dsf.DefTerrains):
            self.log.info("Terrain {} for runway profile not in current list. Will be added with id {}!".format(terrain, terrain_id))
            self.dsf.DefTerrains[terrain_id] = terrain
        else:
            self.log.info("Terrain {} for runway profile found in current list with id: {}.".format(self.dsf.DefTerrains[terrain_id], terrain_id))
        newPatch = XPLNEpatch(1, 0.0, -1.0, None, terrain_id) #None is PoolIndex which is not known yet ############ TBD: PoolIndix in generator for Patch not required --> to be reomved !!! #################
        ##### IMPORTANT: the first command for the pool has still to be set as selection of poolID for first tria
        self.dsf.Patches.append(newPatch)
        return len(self.dsf.Patches)-1 #Index of the new patch is now the last just added
        
    def createPolyTerrain(self, poly, terrain, elev, method = "earclip"):
        """
        Creates trias of given terrain inside the poly.
        Poly is expected to be closed (first = last vertex)
        """
        patchID = self.getPatchID(terrain) ### WARNING: This new patch has still no poolDefintion in first Command!!!!!
        if method == "earclip":
            if len(earclipTrias(deepcopy(poly[:-1]))) < len(poly) - 3: self.log.error("Earclip does only return {} trias for poly: {}".format(len(earclipTrias(deepcopy(poly))), poly))  #### ERROR CHECKING ONLY ######
            trias = earclipTrias(deepcopy(poly[:-1])) #earclip want's polygon without last vertex as returned by PolyCutPoly; earclip always returns clockwise order
        elif method == "segment_intervals":
            trias = []
            l = len(poly)
            for i in range(1, int(l/2)): #poly is assumed to have odd number of vertices, as first is same as last vertex; int rounds to lower value
                trias.append([poly[l-i], poly[i], poly[l-i-1]])
                trias.append([poly[i], poly[i+1], poly[l-i-1]])
            self.log.info("Segment Interval Poly generated: {}".format(trias))
        else:
            self.log.error("Method {} not supported in createPolyTerrain.".format(method))
        for tria in trias: 
            if len(tria) < 3: self.log.error("creatPolyTerrain method {} has returned less then 3 vertices for poly: {}".format(method, poly))  #### ERROR CHECKING ONLY ######
            new_v = [None, None, None]
            for e in range(3):
                new_v[e] = [tria[e][0], tria[e][1], elev, 0, 0] #This version only creates simple vertices without s/t coordinates
                #new_v[e] = createFullCoords(tria[e][0], tria[e][1], t)  ## TBD: support s/t vertices via a given tria t that has maximum s/t coords at endpoint
                ############# TBD: Elevation change probably not required here, because it will always be set via border vertices later ?!? #########################
            self.atrias.append([new_v[0], new_v[1], new_v[2], [None, None], [None, None], [None, None], patchID])  #As tria is completely new, there is no pool/patchID where tria is inside, so None ==> If None makes problems use [None, None] or [-1, -1]
            
    def splitCloseEdges(self, v, mindist=0.1):
        """
        Checks for a vertex v if it lies on/next to edges of trias.
        If this is the case according edges (trias) are split at v.
        Minimal distance is in meter. When v is closer than mindist
        to edge vertex or further away from edge, the edge is not split.
        """
        self.log.info("Checking if close edge for vertex {} is found.".format(v))
        new_trias = []
        old_trias = []
        for enum_t, t in enumerate(self.atrias):
            for e in range(3):
                e_part, o_part, dist = edgeDistance(v, t[e][:2], t[(e+1)%3][:2])
                if e_part > 0 and e_part < 1: #v must be between two vertices of edge
                    if distance(v, t[e][:2]) > mindist and distance(v, t[(e+1)%3][:2]) > mindist: #v must not be too close to tria edge vertices
                        if abs(dist) < mindist:
                            self.log.info("   Close edge in tria {} on edge {} found from {} to {} with distance {} --> splitted (e-part: {})  Tria: {}.".format(enum_t, e, t[e], t[(e+1)%3], dist, e_part, t))
                            new_v = createFullCoords(v[0], v[1], t) #use v now as point of both new trias
                            new_trias.append([ t[e], new_v, t[(e+2)%3], t[3], t[4], t[5], t[6]])
                            new_trias.append([ new_v, t[(e+1)%3], t[(e+2)%3], t[3], t[4], t[5], t[6]])
                            old_trias.append(t)
        for nt in new_trias:
            self.log.info("   Tria appended: {}".format(nt))
            self.atrias.append(nt) #update area trias by appending new trias
        for ot in old_trias:
            self.log.info("   Tria removed: {}".format(ot))
            if ot[0][2] > 0 or ot[1][2] > 0 or ot[2][2] > 0: ########## ERROR CHECKING ---> TO BE REMOVED ###############
                self.log.error("          REMOVED TRIA ABOVE ALREADY HAVING ELEVATION")
            if ot in self.atrias: ###### NEW 05.04.2020 ############## WHY REQUIRED after setting relative_mindist from 0.001 to 0.00001??? NOW STILL REQUIRE ??? ############
                self.atrias.remove(ot) #update area trias by by removing trias that are replaced by new ones
        return

    def assign_spline_elevation(self, spline_points, vertices, place_holder_removal=0):
        """
        Assigns for all vertices (x, y) the elevation defined by a spline going through the spline points (x, y, elev)
        The elevation for a vertex v assigned depends where the orthogonal line of from first to last spline_point
        going through v cuts this spline line
        If a place_holder value other than 0 is given, all vertices in self.atrias having this placholder elevation
        will also be assigned the spline elevation.
        """
        xp, yp = [], []  # points for spline to be created
        for p in spline_points:
            xp.append(distance([spline_points[0][1], spline_points[0][0]], [p[1], p[0]]))  #### IMPORTANT: 3d coordinates currently not swapped !!!!!!!! ##################
            if p[2] == -99999:  # MAGIC NUMBER for retrieving elevation from dsf file instead assigning it
                yp.append(self.mesh_elevation([p[1], p[0]]))  #### IMPORTANT: 3d coordinates currently not swapped !!!
                self.log.info("Assigned magic elevation -99999 at {} to mesh-elevation: {}".format(p[:2], yp[-1]))
            else:
                yp.append(p[2])
        self.log.info("Points for spline: {}, {}".format(xp, yp))
        spline = getspline(xp, yp)
        self.log.info("Spline: {}".format(spline))
        if len(vertices):
            for vertex in self.getAllVerticesForCoords(vertices):  # set vertices of intervals to correct elevation
                elev, distSplineLine = interpolatedSegmentElevation([spline_points[0], spline_points[-1]], vertex[:2], spline)  #### IMPORTANT: 3d coords not swapped, but interpolation is okay for not swapped #####
                self.log.info("Assigning Spline Elevation for {}, {}  to  {} m at distance {}".format(vertex[1], vertex[0], elev, distSplineLine))  ########### TESTING ONLY ############
                vertex[2] = elev
        if place_holder_removal:
            for nt, t in enumerate(self.atrias):
                for v in range(3):
                    if t[v][2] == place_holder_removal:  # adapt all marked vertices with elev. from position on ramp
                        self.log.info("Getting elevation for: {}".format(t[v][:2]))  ##### TO BE REMOVED ###
                        elev, distSplineLine = interpolatedSegmentElevation([spline_points[0], spline_points[-1]], t[v][:2], spline)  #### IMPORTANT: 3d coords not swapped, but interpolation is okay for not swapped #####
                        self.log.info("Assigning Spline Elevation for {}  to  {} m at distance {}".format(t[v][:2], elev, distSplineLine))  ########### TESTING ONLY ############
                        t[v][2] = elev

    def smooth_elevation_around_poly(self, poly, elevation, dist, probe_inner_vertex=False, error_rate=0.01):
        """
         Smoothens the elevation around polygon of given elevation within distance
         In case probe_inner_vertex = True the elevation inside is probed and elevation value ignored
         error rate is the percentage which is considered to be outer edge (=base) and not be somoothed, or
         inner edge considered to get just elevation.
         """
        del poly[-1]  # first = last point not needed for following calculations
        stretched_poly = stretch_poly(poly, dist)
        # stretched poly returns vertices ordered clockwise, important below for orthogonal vector to inside

        if dist == 0:
            self.log.error("Given distance must not be zero!")
            return []

        for t in self.atrias:
            for v in t[:3]:
                for i in range(len(poly)):
                    i_next = (i + 1) % len(poly)
                    base_i, inside_i = PointLocationInTria(v, [stretched_poly[i_next], poly[i], stretched_poly[i]])
                    if 0 < base_i < 1 and 0 + error_rate < inside_i < 1:
                        base_in, inside_in = PointLocationInTria(v, [stretched_poly[i], poly[i_next], stretched_poly[i_next]])
                        if 0 <= base_in <= 1 and 0 + error_rate < inside_in < 1 - error_rate:
                            base_dist = (base_i + 1 - base_in) / 2
                            base_v = [stretched_poly[i][0] + base_dist*(stretched_poly[i_next][0] - stretched_poly[i][0]), stretched_poly[i][1] + base_dist*(stretched_poly[i_next][1] - stretched_poly[i][1])]
                            inner_v = [poly[i][0] + base_dist*(poly[i_next][0] - poly[i][0]), poly[i][1] + base_dist*(poly[i_next][1] - poly[i][1])]
                            if probe_inner_vertex:
                                #ortho_to_inside = [poly[i_next][1] - poly[i][1], -(poly[i_next][0] - poly[i][0])]
                                #f = 1 / distance(inner_v, [inner_v[0] + ortho_to_inside[0], inner_v[1] + ortho_to_inside[1]])
                                ## go 1m to the inside of poly to get really elevation of inside the poly and not outside
                                #elev_inner_v = self.mesh_elevation([inner_v[0] + f*ortho_to_inside[0], inner_v[1] + f*ortho_to_inside[1]])
                                #self.log.info("Inner Point: {}  Elevation from: {}".format(inner_v, [inner_v[0] + f*ortho_to_inside[0], inner_v[1] + f*ortho_to_inside[1]]))
                                elev_inner_v = self.mesh_elevation(inner_v)
                            else:
                                elev_inner_v = elevation
                            elev_base_v = self.mesh_elevation(base_v)
                            base_inner_ratio = min(distance(base_v, v) / distance(base_v, inner_v), 1)  # maximum ratio shall be 1
                            self.log.info("Elevation at base {} for {} in distance_ratio {} is: {} (elevation inside at {}  : {})".format(base_v, v[:2], base_inner_ratio, elev_base_v, inner_v, elev_inner_v))
                            v[2] = elev_base_v + base_inner_ratio * (elev_inner_v - elev_base_v)
                            self.log.info("Elevation smoothing at {}: Set elevation to: {}".format(v[:2], v[2]))
                        elif 1 - error_rate <= inside_i < 1 and 1 - error_rate <= inside_in < 1:
                            # we are close to edge of poly so we just take elevation at poly
                            if probe_inner_vertex:
                                inner_dist, outside = PointLocationInTria(v, [poly[i_next], stretched_poly[i], poly[i]])
                                inner_v = [poly[i][0] + inner_dist * (poly[i_next][0] - poly[i][0]),
                                           poly[i][1] + inner_dist * (poly[i_next][1] - poly[i][1])]
                                #ortho_to_inside = [poly[i_next][1] - poly[i][1], -(poly[i_next][0] - poly[i][0])]
                                #f = 1 / distance(inner_v, [inner_v[0] + ortho_to_inside[0], inner_v[1] + ortho_to_inside[1]])
                                ### go 1m to the inside of poly to get really elevation of inside the poly and not outside
                                #v[2] = self.mesh_elevation([inner_v[0] + f*ortho_to_inside[0], inner_v[1] + f*ortho_to_inside[1]])
                                #self.log.info("Point {} very close to poly! Inner Point: {}  Elevation from: {} is: {}".format(v[:2], inner_v, [inner_v[0] + f*ortho_to_inside[0], inner_v[1] + f*ortho_to_inside[1]], v[2]))
                                v[2] = self.mesh_elevation(inner_v)
                            else:
                                v[2] = elevation

        poly.append(poly[0])  # set again first and last point equal
        stretched_poly.append(stretched_poly[0])
        return stretched_poly

    def smooth_elevation_around_poly_quick(self, poly, elevation, dist):  ##### currently not in use #####
        """
        Smoothens the elevation around polygon of given elevation within distance
        Uses elevation only at edges of poly and stretched poly
        """
        del poly[-1]  # first = last point not needed for following calculations
        stretched_poly = stretch_poly(poly, dist)
        dist_elev = []  # elevation of vertices of stretched poly
        for v in stretched_poly:
            dist_elev.append(self.mesh_elevation(v))
            self.log.info("Mesh elevation at {} is: {}".format(v, dist_elev[-1]))
        for t in self.atrias:
            for v in t[:3]:
                for i in range(len(poly)):
                    i_next = (i+1) % len(poly)
                    a, b = PointLocationInTria(v, [poly[i], stretched_poly[i], stretched_poly[i_next]])
                    if 0 < a < 1 and 0 < b < 1 and 0 < 1 - a - b < 1:
                        v[2] = dist_elev[i_next] + a * (elevation - dist_elev[i_next]) + b * (dist_elev[i] - dist_elev[i_next])
                        self.log.info("Elevation smoothing at {}: Set elevation to: {}".format(v[:2], v[2]))
                    a, b = PointLocationInTria(v, [poly[i], poly[i_next], stretched_poly[i_next]])
                    if 0 < a < 1 and 0 < b < 1 and 0 < 1 - a - b < 1:
                        v[2] = dist_elev[i_next] + a * (elevation - dist_elev[i_next]) + b * (elevation - dist_elev[i_next])
                        self.log.info("Elevation smoothing at {}: Set elevation to: {}".format(v[:2], v[2]))
        poly.append(poly[0])  # set again first and last point equal
        stretched_poly.append(stretched_poly[0])
        return stretched_poly

    def smooth_cut(self, c, poly, elevation=None):
        """
        Performs smoothing around poly according to given parameters in command c
        In case elevation is given, this counts for the polygon otherwise elevation at polygon is probed.
        Returns the polygon in which smoothing was performed
        """

        if c["type"] == "smooth" or c["type"] == "double_cut":
            if "distance" in c:
                d = c["distance"]
            else:
                d = 20.0
            self.log.info("Smoothing type: {} with distance: {} for poly: {}".format(c["type"], d, poly))
            if c["type"] == "double_cut":
                stretched_poly = stretch_poly(poly, d)
                polysouter, polysinner, borderv = self.CutPoly(stretched_poly)
                for box_edge in range(4):
                    ecps = self.cutEdges(poly[box_edge], stretched_poly[box_edge])
                    # OPEN: Perform that cut only for smoothing ????
            if elevation == None or elevation == -99999:
                stretched_poly = self.smooth_elevation_around_poly(poly, None, d, True)
            else:
                stretched_poly = self.smooth_elevation_around_poly(poly, elevation, d)
            self.log.info(
                "Smoothing ended inside stretched poly: {}".format(stretched_poly))
            return stretched_poly
        else:
            self.log.error("Unknown type: {}  used in command. Ignored.".format(c["type"]))
            return []

    def set_path_elevation(self, coords, width, left, right, elev):
        """
        For a path given by coordinates including left and right points to have width of the path and
        elevation give, adapts the elevation for points that are on this path dependent on these elevation points.
        """
        for t in self.atrias:
            for v in t[:3]:
                if v[2] == 333333:  # elevation placeholder
                    for i in range(len(coords)-1):
                        ortho_point = [coords[i][0]+coords[i+1][1]-coords[i][1], coords[i][1]+coords[i][0]-coords[i+1][0]]
                        line_dist, inside = PointLocationInTria(v, [coords[i+1], ortho_point, coords[i]])
                        if abs(inside) > 1 + width/2:  # outside of current path-segment (+1 as epsilon)
                            continue
                        if line_dist <= 0:  # point lies in previous segment or at beginning
                            v[2] = elev[i]
                            break
                        if line_dist <= 1:
                            v[2] = elev[i] + line_dist*(elev[i+1] - elev[i])
                            break
                    if v[2] == 333333:  # elevation not yet changed, so we are at the end of path
                        v[2] = elev[-1]
                    self.log.info("Set path elevation for {} to {} meters".format(v[:2], v[2]))

    def get_mesh_elevation_for_magic_number(self, coords, magic_number=-99999):
        #  when MAGIC NUMBER is used for elevation then elevation is assigned from dsf file instead assigning it
        for i in range(len(coords)):  # MAGIC elevation needs to be replaced before placeholder elevation is assigned
            if coords[i][2] == magic_number:  # MAGIC NUMBER for retrieving elevation from dsf file instead assigning it
                coords[i][2] = self.mesh_elevation([coords[i][1], coords[i][0]])  #### IMPORTANT: 3d coordinates currently not swapped !!!
                self.log.info("Assigned magic elevation -99999 at {} to: {}".format(coords[i][:2], coords[i][2]))
