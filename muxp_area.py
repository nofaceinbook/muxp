# -*- coding: utf-8 -*-
#******************************************************************************
#
# muxp_area.py    Version: 0.1.0 exp
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

from logging import getLogger
from muxp_math import *
from copy import deepcopy
from tripy import *
    
class muxpArea:
    
    def __init__(self, dsf, logname):
        self.dsf = dsf #dsf from which area is extracted
        self.log = getLogger(logname + "." + __name__) #logging based on pre-defined logname
        self.apatches = set() #set of patches that are relevant for that area
        self.atrias = [] #area as array, of triangles where
                  # [0 - 2] list of all coordinates of tria vertices including s/t ##### ONLY REFERENCE NO DEEPCOPY / BETTER JUST DEEPCOPY of x,y corrds ?????
                  # [3 - 5] list of pool and vertex id in pool in dsf -- they stay even, if coordinates are changed or trias split; allows reference to original trias/values/scaling
                  # [6] index to patch tria was in dsf

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
                                self.atrias.append([ self.dsf.V[t[0][0]][t[0][1]], self.dsf.V[t[1][0]][t[1][1]], self.dsf.V[t[2][0]][t[2][1]] ])
                                self.atrias[-1].extend(t)  #so we have an intersection of tria box with area and append the tria
                                self.atrias[-1].append(self.dsf.Patches.index(p))
                                self.apatches.add(self.dsf.Patches.index(p))
                                tremoved.append(t)
                                self.log.debug("Tria {} with latS: {}  latN: {}  lonW: {} and lonE: {} in area.".format(t, miny, maxy, minx, maxx))
                triaCount += 1
            for t in tremoved:
                trias.remove(t)
            p.trias2cmds(trias) #updates dsf patch with trias not including removed ones
        self.log.info("  ... dsf has {} trias and {} trias from {} different patches are now in the extracted area.".format(triaCount, len(self.atrias), len(self.apatches)))
        return
    
    def getAllVerticesForCoords(self, coords):
        """
        Returns all vertices that have same lon/lat coordinates as given in list of coords (list of [x,y])
        """
        self.log.info("Searching vertices for coords: {}")
        cdict = {}  #set up dictonary with all coords o to find additional in area with same coords
        vertices = [] #list of vertices 
        for c in coords:
            cdict[(round(c[0], 7), round(c[1], 7))] = True  # coords round to range of cm
        for t in self.atrias:
            for v in t[:3]:
                self.log.info("Checking vertex: ({}, {})".format(round(v[0],7), round(v[1],7)))
                if (round(v[0], 7), round(v[1], 7)) in cdict:
                    vertices.append(v)  # add tuple of vertex at coords to make sure to get all vertices at the coords
        self.log.info("{} vertices on {} coords found.".format(len(vertices), len(coords)))
        return vertices    #returns set of all vertices which ar on coords
    
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
        ############ TBD: Check where really deepcopy is required ################
        self.log.info("Polygon {} cutting from start-segement {} at distance: {}".format(p, c_start, c_start_distance))
        border_v = [] #these vertices are building the border between the cut halfs of p from entry to exit point (including vertices of c and cutting points)
        for i in range(c_start, len(c) - 1): #check for each segement of cutting poly...
            len_p = len(p)
            cP_dict = dict() #this dict will contain all cutting points of segment in c with all segments in p as values and distances to segment start of c as keys
            for j in range (len_p): #...which segments of p it will cut
                cuttingPoint = intersection(c[i], c[i+1], p[j], p[(j+1)%len_p]) ### WHAT HAPPENS IF SEGEMENTS ARE COLINEAR???? #####
                if cuttingPoint: #segement of c did cut segment of p, so we now enter/leave p
                    self.log.info("   not confiremed cutting point {}: with c-segment:{} after distance:{}".format(cuttingPoint, i, distance(c[i], cuttingPoint)))
                    if i != c_start or distance(c[i], cuttingPoint) > c_start_distance: #cuts on start_segement before distance are not counted
                        self.log.info("   cutting point {}: with c-segment:{} after distance:{}".format(cuttingPoint, i, distance(c[i], cuttingPoint)))
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
        border_v[0] = border_v[0][0] #get rid of not needed sgement info in vertex list
        border_v[-1] = border_v[-1][0] #get rid of not needed sgement info in vertex list
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
        ## The following line assumes that c[i] to c[i+1] is still the butting line of p where cutting polygon exits p
        if ((c[i+1][0] - c[i][0]) * (p[exit_segment][1] - c[i][1]) - (c[i+1][1] - c[i][1]) * (p[exit_segment][0] - c[i][0])) < 0: #first point of exit segment of p lies on outer side in case of clockwise going through p
            outer = part1
            inner = part2
        else:
            outer = part2
            inner = part1
            self.log.info("    SWAPPED INNER AND OUTER POLYS!")
        ### Special case if entry and exit point are on the same segment of p, then the inner polygon makes no use of of vertices from p, just from border_v
        if entry_segment == exit_segment:
            inner = deepcopy(border_v)
        
        outer1, inner1, border1 = self.PolyCutPoly(outer, c, i, distance(c[i], border_v[-1]) + 0.01) ######  0.0001 was not sufficeint, why so high rounding errors ??? ####
        if border1 == []: #no further cut for outer
            outer1 = [outer] #so we stay with the current outer
        outer2, inner2, border2 = self.PolyCutPoly(inner, c, i, distance(c[i], border_v[-1]) + 0.01) ######  0.0001 was not sufficeint, why so high rounding errors ??? ####
        if border2 == []: #no further cut for inner
            inner2 = [inner] #so we stay with the current inner
        border_v.extend(border1)
        outer1.extend(outer2)
        inner1.extend(inner2)
        border_v.extend(border2)
        return outer1, inner1, border_v


    def CutPoly(self, p, elev=None):
        #### TBD: Make sure p is ordered clockwise !!!! ##############################
        outer = []
        inner = []
        border = []
        new_trias = []
        old_trias = []
        self.log.info("Cutting Polygon p into area, retrieving inner and outer sub-polygons.")
        for t in self.atrias: #go through all trias in area
            tria = [t[0][0:2], t[1][0:2], t[2][0:2]]
            
            while isPointInTria(p[0], tria): #make sure that first vertex of p is outside tria
                ############# TBD: special case that whole p is in tria!!!! ################
                self.log.info("p[0] inside tria --> shifting poly {}".format(p))
                p = p[1:]
                p.append(p[0])
                self.log.info("       to poly {}".format(p))
            o, i, b = self.PolyCutPoly(tria, p)
            outer.extend(o), inner.extend(i), border.extend(b)

            if PointInPoly(tria[0], p) and PointInPoly(tria[1], p) and PointInPoly(tria[2], p): #special case that tria lies completely in p
                if elev != None: #if elevation should be adapted do this for inner trias
                    inside_tria = deepcopy(t)
                    for tv in range(3):
                        inside_tria[tv][2] = elev
                    new_trias.append(inside_tria)
                    self.log.info("Adapted elevation in inside tria. New Tria: {}".format(inside_tria))

            for poly in i: ### In case p has own mesh, than only earclip outer trias, but insert border vertices into mesh and delete inner trias without cut  #### ERROR CHECKING ONLY ######
                if len(earclip(deepcopy(poly))) < len(poly) - 2: self.log.error("Earclip does only return {} trias for poly: {}".format(len(earclip(deepcopy(poly))), poly))  #### ERROR CHECKING ONLY ######
                for tria in earclip(deepcopy(poly)): #earclip want's polygon without last vertex as returned by PolyCutPoly; earclip should always return clockwise order
                    if len(tria) < 3: self.log.error("Earclipp has returned tria with less then 3 vertices for poly: {}".format(poly))  #### ERROR CHECKING ONLY ######
                    new_v = [None, None, None]
                    for e in range(3):
                        new_v[e] = createFullCoords(tria[e][0], tria[e][1], t)
                        if elev != None: ### actually only for inner + border_v !!!!!!!!!!!!!!!!! ### 
                            new_v[e][2] = elev
                    new_trias.append([new_v[0], new_v[1], new_v[2], t[3], t[4], t[5], t[6]])

            for poly in o: #out polys have always to be earclipped, but no elevation/terrian change 
                if len(earclip(deepcopy(poly))) < len(poly) - 2: self.log.error("Earclip does only return {} trias for poly: {}".format(len(earclip(deepcopy(poly))), poly))  #### ERROR CHECKING ONLY ######
                for tria in earclip(deepcopy(poly)): #earclip want's polygon without last vertex as returned by PolyCutPoly; earclip should always return clockwise order
                    if len(tria) < 3: self.log.error("Earclipp has returned tria with less then 3 vertices for poly: {}".format(poly))  #### ERROR CHECKING ONLY ######
                    new_v = [None, None, None]
                    for e in range(3):
                        new_v[e] = createFullCoords(tria[e][0], tria[e][1], t)
                    new_trias.append([new_v[0], new_v[1], new_v[2], t[3], t[4], t[5], t[6]])
                     
            if b != []: #we have border vertices, so there was a cut in this tria
                old_trias.append(t) #so this tria is replaced by trias of inner and outer polys
        for nt in new_trias: #add all new trias
            self.atrias.append(nt)
            #### tbd: adapt elevation for all trias (only outer if p own mesh) and create for inner trias new terrain patches if terrain given
        for ot in old_trias: #and remove old ones
            self.log.info("Following Tria is removed: {}".format(ot))
            try: #as we might cross same tria several times there might several removals for same tria
                self.atrias.remove(ot)
            except ValueError:
                self.log.info("   was already removed...")
        
        if elev != None: #Adapt elevevation of border vertices 
            for v in self.getAllVerticesForCoords(border):
                v[2] = elev
                
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
                for vti in range(len(t[vt])):
                    if t[vt][vti] != self.dsf.V[t[vt+3][0]][t[vt+3][1]][vti]:
                        self.log.info("Reference for vertex {} not correct any more. {} differs to {}!".format(self.atrias.index(t), t[vt][vti], self.dsf.V[t[vt+3][0]][t[vt+3][1]][vti]))
                        break
                    count += 1
                if len(t[vt]) != count: #the reference for this vertex to the pool is not correct any more, new vertex needs to be inserted in dsf
                    v = deepcopy(t[vt]) #v has now deepcopy of all coordinates of that vertex that is to be inserted in the dsf
                    poolID4v = None #Searching for the pool ID for vertex v
                    if elevscal < 1 and v[2] < -32765: #we want to get submeter elevations but have vertex referencing raster
                        v[2] = self.dsf.getVertexElevation(v[0], v[1], v[2]) #make sure that v[2] is real elevation and not using raster (with raster no submeter); only works because raster is there
                    for i in newPools:
                        if len(v) == len(self.dsf.Scalings[i]): #does size of scaling vector / number of planes for pool fit
                            counter = 0
                            for j in range(len(v)): #check for each plane j if v could fit between minimum and maximum reach of scale
                                if v[j] >= self.dsf.Scalings[i][j][1] and v[j] <= self.dsf.Scalings[i][j][1] + self.dsf.Scalings[i][j][0]:
                                    counter += 1
                                else:
                                    break
                            if len(v) == counter:  #all values of v are within range of scale for pool i
                                poolID4v = i #existing pool id found fulfilling all requirements                            
                                break
                    if poolID4v != None: #existing pool was found
                        matchfound = False
                        for ev in self.dsf.V[poolID4v]: #check for all existing vertices ev if they match v already
                            counter = 0
                            for i in range(len(v)): #check for all planes/coordinates whether they are nearly equal
                                if abs(ev[i] - v[i]) >= self.dsf.Scalings[poolID4v][i][0] / 65535: #if difference is lower than scale multiplier both coordinates would end up same after endcoding, so they match
                                    break
                                counter +=1
                            if len(v) == counter: #matching vertex found
                                t[vt+3] = [poolID4v, self.dsf.V[poolID4v].index(ev)]
                                self.log.info("  Vertex {} equals vertex {} in existing Pool with index {} .".format(v, ev, poolID4v))
                                matchfound = True
                                break
                            if counter >= 2:
                                self.log.warning("  Vertex {} is at same location as {} but different higher coordinate {}!!".format(v, ev, counter))
                        if not matchfound:       
                            self.dsf.V[poolID4v].append(v)
                            t[vt+3] = [poolID4v, len(self.dsf.V[poolID4v])-1] #change reference in area tria vertex to the last vertex in existing pool
                            self.log.info("  Vertex {} inserted in existing pool no. {}.".format(v, poolID4v))
                    else: #no existing pool fulfilling requirements was found, so new pool has to be created and added with v
                        if len(self.dsf.V) >= 65535: #reached maximum number of pools, no pool could be added any more
                            self.log.error("DSF File already has maximum number of point pools. Addtional pools required for change can not be added!!!")
                            return -1
                        self.dsf.V.append([v])
                        self.dsf.Scalings.append(deepcopy(self.dsf.Scalings[t[vt+3][0]])) #get scalings from the original tria vertex the new vertex is inside
                        ########## HOWEVER NEW VERTEX MIGHT BE OUTSIDE THESE SCALINGS --> check and adapt if required AFTER elevation was adapted as needed
                        if elevscal < 1: #for given submeter elevation pool-scaling has to be adapted
                            self.dsf.Scalings[-1][2][0] = 65535 * elevscal #new multiplier based on required scaling for elevation defined for new pool
                            self.dsf.Scalings[-1][2][1] = int(-500 + int((v[2]+500)/(65535 * elevscal)) * (65535 * elevscal)) #offset for elevation of v   ######## -500m is deepest vaule that can be defined with this routine ####
                        ## Check new scaling for vertex and adapt as required based on multipliers / offsets give
                        scale_checked = False
                        while not scale_checked:
                            scale_checked = True #assume test will passed, will be set False if on check does not pass
                            for j in range(len(v)): #check for each plane j if v could fit between minimum and maximum reach of scale
                                if v[j] < self.dsf.Scalings[-1][j][1]: #v at plane j is lower than scaling allows
                                    self.dsf.Scalings[-1][j][1] -= self.dsf.Scalings[-1][j][0] #subtract one scalefactor from base
                                    scale_checked = False #check if new scaling fits
                                    self.log.warning("  Vertex {} does not fit to scaling. Reduced scaling base for plane {} to {}!".format(v, j, self.dsf.Scalings[-1][j][1]))
                                if v[j] > self.dsf.Scalings[-1][j][1] + self.dsf.Scalings[-1][j][0]: #v at plane j is higher than scaling allows
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
                

