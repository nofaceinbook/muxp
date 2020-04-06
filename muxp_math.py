# -*- coding: utf-8 -*-
#******************************************************************************
#
# muxp_math.py   Version: 0.1.3 exp
#        
# ---------------------------------------------------------
# Mathematical functions for Python Tool: Mesh Updater X-Plane (muxp)
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

from math import sin, cos, atan2, sqrt, radians #for different calculations

def _linsolve_(a1, b1, c1, a2, b2, c2):  
    divisor = (a1 * b2) - (a2 * b1)
    if divisor == 0:  ## WARNING: for colineear setting special returns special value no error!!!!!
        return -99999, -99999  ### points are colinear, might intersect or not BUT here with negative values calling intersection function returns None
    return round(((c1 * b2) - (c2 * b1)) / divisor, 8), round(((a1 * c2) - (a2 * c1)) / divisor, 8)  # ROUNDING TO ALWAYS GET SAME CONCLUSION

def intersection(p1, p2, p3, p4):  # checks if segment from p1 to p2 intersects segement from p3 to p4   ### NEW - taken from bflat ###
    s0, t0 = _linsolve_(p2[0] - p1[0], p3[0] - p4[0], p3[0] - p1[0], p2[1] - p1[1], p3[1] - p4[1], p3[1] - p1[1])
    if s0 >= 0 and s0 <= 1 and t0 >= 0 and t0 <= 1:
        return (round((p1[0] + s0 * (p2[0] - p1[0])), 8), round(p1[1] + s0 * (p2[1] - p1[1]), 8))  ### returns the cutting point as tuple; ROUNDING TO ALWAYS GET SAME POINT 
    else:                    
        return (None)

def distance(p1, p2): #calculates distance between p1 and p2 in meteres where p is pair of longitude, latitude values          
    R = 6371009 #mean radius earth in m
    lon1 = radians(p1[0]) # WARNING: changed order as it is in bflat now !!!!!!!!
    lat1 = radians(p1[1])
    lon2 = radians(p2[0])
    lat2 = radians(p2[1]) 
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))   
    return R * c

def edgeDistance(p, a, b): #calculates distance of point p to edge e from a to b
    vector_ab = (b[0] - a[0], b[1] - a[1])
    ortho_ab = (b[1] - a[1], a[0] - b[0])
    vector_ap = (p[0] - a[0], p[1] - a[1])
    ab_part, ortho_part = _linsolve_(vector_ab[0], ortho_ab[0], vector_ap[0],vector_ab[1], ortho_ab[1], vector_ap[1])
    dist = distance(p, [p[0] + ortho_part * ortho_ab[0], p[1] + ortho_part * ortho_ab[1]] )
    return ab_part, ortho_part, dist 

def PointLocationInTria(p, t): #delivers location of point p in Tria t by vectors spanned by t from last vertex in tria
    denom = ((t[1][1] - t[2][1])*(t[0][0] - t[2][0]) + (t[2][0] - t[1][0])*(t[0][1] - t[2][1]))
    if denom == 0: ### to be checked when this is the case!!!!
        return -0.01, -0.01 ###NEW NEW NEW, should actually never be the case, but for isPointInTria it delviers NO!
    nom_a = ((t[1][1] - t[2][1])*(p[0] - t[2][0]) + (t[2][0] - t[1][0])*(p[1] - t[2][1]))
    nom_b = ((t[2][1] - t[0][1])*(p[0] - t[2][0]) + (t[0][0] - t[2][0])*(p[1] - t[2][1]))
    a = nom_a / denom
    b = nom_b / denom
    return a, b #returns multiplier for vector (t2 - t0) and for vector (t2 - t1) starting from point t2

def isPointInTria(p, t): #delivers True if p lies in t, else False
    a, b = PointLocationInTria(p, t)
    c = 1 - a - b
    return (0 <= a <= 1 and 0 <= b <= 1 and 0 <= c <= 1)

def PointInPoly(p, poly):
    """
    Test wether a point p with [lat, lon] coordinates lies in polygon (list of [lat, lon] pairs and retruns True or False.
    Counts number of intersections from point outside poly to p on same y-coordinate, if it is odd the point lies in poly.
    To avoid intersection at vertex of poly on same y-coordinate, such points are shifte about 1mm above for testing intersection.
    """
    count = 0
    for i in range(len(poly) - 1):  # for all segments in poly
        epsilon0, epsilon1 = (0, 0)  # added to p's y coordinate in case p is on same y-coordinate than according vertex of segment
        if poly[i][1] < p[1] and poly[i + 1][1] < p[1]:  # if vertices of segment below y-coordinate of p, no intersection
            continue
        if poly[i][1] > p[1] and poly[i + 1][1] > p[1]:  # if vertices of segment above y-coordinate of p, no intersection
            continue
        if poly[i][1] == p[1]:
            epsilon0 = 0.00000001
        if poly[i + 1][1] == p[1]:
            epsilon1 = 0.00000001
        x = intersection([poly[i][0], poly[i][1] + epsilon0], [poly[i + 1][0], poly[i + 1][1] + epsilon1], [181, p[1]], p)
        if x:
            count += 1
    if count % 2:
        return True  # odd number of intersections, so p in poly
    else:
        return False  # even number of intersection, so p outside poly

def edgeInPoly(p, q, poly):
    """
    Checks if an edge from p to q is inside or at least intersects a polygon.
    Returns True or False accordingly.
    """
    if PointInPoly(p, poly) or PointInPoly(q, poly): #at least one point of edge is in poly
        return True
    for i in range(len(poly) - 1):  # for all segments in poly
        if intersection(poly[i], poly[i+1], p, q):
            return True
    return False
            

def BoundingRectangle(vertices, borderExtension=0.0001):
    """
    Returns 4-tuple of (latS, latN, lonW, lonE) building the smallest rectangle to include all vertices in list as pairs of [lon, lat].
    In order to be sure that the rectangle includes really all neede, the border can be extended. Default is about 10m.
    """
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
    return miny-borderExtension, maxy+borderExtension, minx-borderExtension, maxx+borderExtension


def segmentToBox (p1, p2, w):
    """
    Returns for a segement between points p1 and p2 (with [x,y] coordinates)
    boundary of a box with length of segement where line is in the middle
    and the box has width w
    """
    degree_dist_at_equator = 111120 #for longitude (or 111300?)
    lat_degree_dist_average = 111000
    degree_dist_at_lat = cos (radians(p1[0])) * degree_dist_at_equator
    if round (p1[1], 6) == round (p2[1], 6): #segement exactly east-west direction
        dx = 0   #difference for longitute in meters to reach corner from center end
        dy = w/2 #difference for latitude in meters to reach corner from center end
    elif round (p1[0], 6) == round (p2[0], 6): #segment is exactly north-south direction
        dx = w/2
        dy = 0
    else: 
        m = -1 / ((p2[0] - p1[0]) / (p2[1] - p1[1])) #gradient of perpendicular line
        dx = sqrt( ( (w/2)**2) / (1 + m**2)) 
        dy = dx * m 
    dx /= degree_dist_at_lat #convert meters in longitute coordinate difference at geographical latitude
    dy /= lat_degree_dist_average #convert meters in latitude coordinate difference 
    l = []
    if (p1[1] <= p2[1] and dy >= 0) or (p1[1] > p2[1] and dy < 0): #make sure to always insert in clockwise order
        l.append([round(p1[1] - dx, 8), round(p1[0] - dy, 8)]) #buttom corner1
        l.append([round(p1[1] + dx, 8), round(p1[0] + dy, 8)]) #buttom corner2
        l.append([round(p2[1] + dx, 8), round(p2[0] + dy, 8)]) #top corner1
        l.append([round(p2[1] - dx, 8), round(p2[0] - dy, 8)]) #top corner2
    else: #insert vertices in different order to assure clockwise orientation
        l.append([round(p1[1] + dx, 8), round(p1[0] + dy, 8)])
        l.append([round(p1[1] - dx, 8), round(p1[0] - dy, 8)])
        l.append([round(p2[1] - dx, 8), round(p2[0] - dy, 8)])
        l.append([round(p2[1] + dx, 8), round(p2[0] + dy, 8)])
    l.append(l[0]) #add first corner to form closed loop
    return l


def gauss_jordan(m, eps = 1.0/(10**10)):
    """Puts given matrix (2D array) into the Reduced Row Echelon Form.
       Returns True if successful, False if 'm' is singular.
       NOTE: make sure all the matrix items support fractions! Int matrix will NOT work!
       Written by Jarno Elonen in April 2005, released into Public Domain"""
    (h, w) = (len(m), len(m[0]))
    for y in range(0,h):
      maxrow = y
      for y2 in range(y+1, h):    # Find max pivot
        if abs(m[y2][y]) > abs(m[maxrow][y]):
          maxrow = y2
      (m[y], m[maxrow]) = (m[maxrow], m[y])
      if abs(m[y][y]) <= eps:     # Singular?
        return False
      for y2 in range(y+1, h):    # Eliminate column y
        c = m[y2][y] / m[y][y]
        for x in range(y, w):
          m[y2][x] -= m[y][x] * c
    for y in range(h-1, 0-1, -1): # Backsubstitute
      c  = m[y][y]
      for y2 in range(0,y):
        for x in range(w-1, y-1, -1):
          m[y2][x] -=  m[y][x] * m[y2][y] / c
      m[y][y] /= c
      for x in range(h, w):       # Normalize row y
        m[y][x] /= c
    return True

def lin_equation_solve(M, b):
    """
    solves M*x = b
    return vector x so that M*x = b
    :param M: a matrix in the form of a list of list
    :param b: a vector in the form of a simple list of scalars
    """
    m2 = [row[:]+[right] for row,right in zip(M,b) ]
    result = gauss_jordan(m2)
    return [row[-1] for row in m2] if result else None

def getspline(xp, yp):
    """
    for x values xp with according y values yp a natural cubic spline is defined
    note: x values should be sorted from lowest to highest value!
    note: generates only float values to be compatible with gaus_jordan function used
    returns list with deepcopy list of x-values and list of cubic spline paramters (one sgement after the other)
    """
    points = len(xp)
    segments = points - 1
    if (points != len(yp)) or (points < 3):
        return None
    A = []
    b = []
    xp_returned = [] #deepcopy of returned x-values
    for i in range(points):
        xp_returned.append(float(xp[i]))
    for i in range(4 * segments):
        A.append([])
        b.append(0.0)
        for j in range(4 * segments):
            A[i].append(0.0)
    for i in range(segments):
        #condition for left end of segment
        A[i][4*i+0] = float(xp[i]**3)
        A[i][4*i+1] = float(xp[i]**2)
        A[i][4*i+2] = float(xp[i])
        A[i][4*i+3] = 1.0
        b[i] = float(yp[i])
        #condition for right end of segment
        A[segments+i][4*i+0] = float(xp[i+1]**3)
        A[segments+i][4*i+1] = float(xp[i+1]**2)
        A[segments+i][4*i+2] = float(xp[i+1])
        A[segments+i][4*i+3] = 1.0        
        b[segments+i] = float(yp[i+1])
        if i == 0:
            continue #do outer points later, so one row missing now therefore -1 below
        #condition for first derivation of inner points, setting b value to 0 omitted
        A[2*segments+i-1][4*(i-1)+0] = float(3*xp[i]**2)
        A[2*segments+i-1][4*(i-1)+1] = float(2*xp[i])
        A[2*segments+i-1][4*(i-1)+2] = 1.0
        A[2*segments+i-1][4*(i-1)+4] = float(-3*xp[i]**2)
        A[2*segments+i-1][4*(i-1)+5] = float(-2*xp[i])
        A[2*segments+i-1][4*(i-1)+6] = -1.0
        #condition for second derivation of inner points, setting b value to 0 omitted
        A[3*segments+i-1][4*(i-1)+0] = float(6*xp[i])
        A[3*segments+i-1][4*(i-1)+1] = 2.0
        A[3*segments+i-1][4*(i-1)+4] = float(-6*xp[i])
        A[3*segments+i-1][4*(i-1)+5] = -2.0
    # Now consider derivation for endpoints, here for NATURAL SPLINE so second derivation 0 at ends, setting b to 0 omitted
    A[3*segments-1][0] = float(6*xp[0])
    A[3*segments-1][1] = 2.0
    A[4*segments-1][4*(segments-1)] = float(6*xp[segments])
    A[4*segments-1][4*(segments-1)+1] = 2.0
    #Now solve according linear equations
    x = lin_equation_solve(A, b)
    return [xp_returned, x]

def evalspline(x, spline): #evaluates spline at position x
    #assumes spline in format with two lists, first x-values giving intervals/segments, second all paramters for cubic spline one after the other
    #important: it is assumed that x-values for intervals/segments are ordered from low to high
    for i in range(len(spline[0]) - 1):#splines are one less then x-points
        if x <= spline[0][i+1]: #for all points before second point use first spline segment, for all after the last-1 use last spline segment
            break
    return spline[1][4*i+0] * x**3 + spline[1][4*i+1] * x**2 + spline[1][4*i+2] * x + spline[1][4*i+3]

def interpolatedSegmentElevation(rwy, p, rwySpline): #based on segment's spline profile, the elevation of a point orthogonal to segment is calculated  (segement used to be runway)   
    start = (rwy[0][1], rwy[0][0]) #start coordinates rwy 
    end = (rwy[1][1], rwy[1][0]) #end coordinates rwy
    startD = (start[0] - 0.1 * (end[0] - start[0]), start[1] - 0.1 * (end[1] - start[1])) #use starting point 10% of rwy length before to really get value for all points around runway
    endD = (start[0] + 1.1 * (end[0] - start[0]), start[1] + 1.1 * (end[1] - start[1]))   #use end point 10% of rwy length behind to really get value for all points around runway
    inclination_of_ortho = (end[1] - start[1], start[0] - end[0])
    orthoStartD = (p[0] - inclination_of_ortho[0], p[1] - inclination_of_ortho[1]) # Start of orthogonal line of RWY through point p with length double of RWY (to guarentee intersection on center line)
    orthoEndD = (p[0] + inclination_of_ortho[0], p[1] + inclination_of_ortho[1]) # End of orthogonal line of RWY through point p with length double of RWY (to guarentee intersection on center line)
    p_centered = intersection(startD, endD, orthoStartD, orthoEndD) #location of p on center line
    d = distance(start, p_centered)
    elev = evalspline(d, rwySpline)
    return elev


def createFullCoords(x, y, t):
    """
    returns for coordinates (x, y) in tria t (list of 3 vertex list with all coords of vertices of t) the full coordinates
    """
    ##### NEW 06.04.2020: Might be the x,y are one vertex of t. In that case directly return that vertex, then correct elevation of that vertex is not destroyed #########
    for v in t[:3]: #we only need the first three elements of t containing vertex information
        if round(v[0],7) == round(x,7) and round(v[1],7) == round(y,7):
            return v
    v = [x, y]
    l0, l1 = PointLocationInTria(v, t) # returns length for vectors from point t3 with l0*(t2-t0) and l1*(t2-t1)
    if t[0][2] == -32768.0 or t[1][2] == -32768.0 or t[2][2] == -32768.0: # at least one tria vertex is getting elevation from raster  ############## UPDATED ON 31 March 2020 ############################
        elevation = -32768.0 #so take also elevation in tria from raster (might cause PROBLEM when neighbour tria does not use raster at that position --> to be solved when creating dsf vertices
    else:
        elevation = t[2][2] + l0 * (t[0][2] - t[2][2])  + l1 * (t[1][2] - t[2][2])
    v.append(elevation)
    v.extend([0, 0]) ### leave normal vectors to 0 ##### TO BE ADAPTED IN CASE OF NO RASTER !!!!!
    for i in range(5, len(t[0])): #go through optional coordinates s/t values based on first vertex in tria
        v.append(t[2][i] + l0 * (t[0][i] - t[2][i])  + l1 * (t[1][i] - t[2][i]))
    return v
        
