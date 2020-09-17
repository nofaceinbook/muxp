# -*- coding: utf-8 -*-
#******************************************************************************
#
# muxp_math.py   Version: 0.2.4 exp
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

#Change since 0.1.3: Spline evaluation returns distance for error checking
#Change since 0.1.4: Removed () around None for return value of intersection
#                    Using new earclipping from mrbaozi directly inside this file
#Change since 0.1.5: Adapting earclipping (select shortest ears with not maximal angele of trias)
#Change since 0.1.6: Adapted earclipping agin: Miniear only takes ears with not mximial angle if such trias exist
#                    Added function doBoundingRectanglesIntersect
#Change since 0.1.7: check devision by zero in  max_tria_angle for malformed trias

from math import sin, cos, atan2, tan, atan, acos, log, exp, sqrt, radians, degrees, pi #for different calculations

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
        return None   ######### Removed () around none on 12.04.2020

def lat2y(a):
    RADIUS = 6378137.0  # in meters on the equator
    return log(tan(pi / 4 + radians(a) / 2)) * RADIUS

def lon2x(a):
    RADIUS = 6378137.0  # in meters on the equator
    return radians(a) * RADIUS

def x2lon(a):
    RADIUS = 6378137.0  # in meters on the equator
    return degrees(a/RADIUS)

def y2lat(a):
    RADIUS = 6378137.0  # in meters on the equator
    return degrees(2 * atan(exp(a/RADIUS)) - pi / 2)

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
    ab_part, ortho_part = _linsolve_(vector_ab[0], ortho_ab[0], vector_ap[0], vector_ab[1], ortho_ab[1], vector_ap[1])
    dist = distance(p, [p[0] + ortho_part * ortho_ab[0], p[1] + ortho_part * ortho_ab[1]] )
    return ab_part, ortho_part, dist

def sortPointsAlongPoly(points, poly, epsilon=0.001):
    """
    Returns given list of points in [x, y] coordinates which are lying on the edges of a polygon
    (also given as [x, y] coordinates, sorted such that they are following position on the edges.
    epsilon is the minimal error distances allowed in decision if point is on edge.
    """
    sortedPoints = []  # list of points sorted along Poly
    log_info = ""
    for p in points:
        for i in range(len(poly) - 1):
            edist, odist, dist = edgeDistance(p, poly[i], poly[i+1])
            #print("Check point {} for edge {} results in odist {} and distance {}".format(p, i, odist, edist))
            if odist < epsilon and edist >= -epsilon and edist <= 1 + epsilon:
                print("    added to list")
                sortedPoints.append([i, edist, p[0], p[1]])
                break
            if i == len(poly) - 2:  # we did not find an edge for p
                log_info += "ERROR: point {} not on edge of poly {}\n".format(p, poly)
                return None
    sortedPoints.sort()  # okay now they are sorted as required
    for i in range(len(sortedPoints)):
        log_info += "Info: Point {} on edge no {} starting at {} with part {}\n".format(sortedPoints[i][2:], sortedPoints[i][0], poly[sortedPoints[i][0]], sortedPoints[i][1])
        sortedPoints[i] = [sortedPoints[i][2], sortedPoints[i][3]]  # remove now data used for sorting
    return sortedPoints, log_info

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

def doBoundingRectanglesIntersect(r, s):
    """
    Returns True if two bounding rectangles r, s as 4-tuple of (latS, latN, lonW, lonE)
    and False otherwise.
    """
    #are corners of s inside r then we have intersection
    if r[0] <= s[0] <= r[1] and r[2] <= s[2] <= r[3]: return True
    if r[0] <= s[0] <= r[1] and r[2] <= s[3] <= r[3]: return True
    if r[0] <= s[1] <= r[1] and r[2] <= s[2] <= r[3]: return True
    if r[0] <= s[1] <= r[1] and r[2] <= s[3] <= r[3]: return True
    #so either r and s are distinct or r is completely in s
    if s[0] <= r[0] <= s[1] and s[2] <= r[2] <= s[3]:
        return True
    else:
        return False

def CenterInAtrias(atrias):
    """
    Returns center as [x, y, z] for all trias in a list of area trias.
    """
    max_coords = [-99999, -99999, -99999]
    min_coords = [99999, 99999, 99999]
    for t in atrias:
        for i in range(3):
            for j in range(3):
                if t[i][j] < min_coords[j]:
                    min_coords[j] = t[i][j]
                if t[i][j] > max_coords[j]:
                    max_coords[j] = t[i][j]
    return [(min_coords[0]+max_coords[0])/2, (min_coords[1]+max_coords[1])/2, (min_coords[2]+max_coords[2])/2]

def segmentToBox(p1, p2, w):
    """
    Returns for a segement between points p1 and p2 (with [y,x] coordinates)
    ---> IMPORTANT: matches the not swapped 3d coordinates
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
        m = -1 / ((lat2y(p2[0]) - lat2y(p1[0])) / (lon2x(p2[1]) - lon2x(p1[1])))  # gradient of perpendicular line
        # NEW 04.08.2020 Above gradient is calculated in Mercartor projection to have equal of angle
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
    inclination_of_ortho = (lat2y(end[1]) - lat2y(start[1]), lon2x(start[0]) - lon2x(end[0]))  # NEW 04.08.2020 done in Mercartor Projection to keep equal of angle
    orthoStartD = (p[0] - inclination_of_ortho[0], p[1] - inclination_of_ortho[1]) # Start of orthogonal line of RWY through point p with length double of RWY (to guarentee intersection on center line)
    orthoEndD = (p[0] + inclination_of_ortho[0], p[1] + inclination_of_ortho[1]) # End of orthogonal line of RWY through point p with length double of RWY (to guarentee intersection on center line)
    p_centered = intersection(startD, endD, orthoStartD, orthoEndD) #location of p on center line
    d = distance(start, p_centered)
    elev = evalspline(d, rwySpline)
    return elev, d #### d just for TESTING #########


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

def max_tria_angle(t):
    """
    Returns the maximum angle within tria t in range between 0 and 180 degrees.
    """
    def dotproduct(v1, v2):
      return sum((a*b) for a, b in zip(v1, v2))
    def length(v):
      return sqrt(dotproduct(v, v))
    def angle(v1, v2):
        l1 = length(v1)
        l2 = length(v2)
        if l1 == 0 or l2 == 0: #### NEW 02.05.2020 to check whether l1 or l2 are zero
             print("ERROR IN MAX TRIA ANGLE: Tria with identical or 0-length edges. Set max angle to 180 for such a tria!")
             return 180
        a = dotproduct(v1, v2) / (length(v1) * length(v2))
        ### TBD: SOLVE ISSUES BY ROUNDING; NO NEED TO HAVE ANGEL VERY EXACT
        if a > 1:
            print("ERROR IN MAX TRIA ANGLE: VALUE FOR ACOS {} IS ABOVE 1".format(a))
            a = 1
        if a < -1:
            print("ERROR IN MAX TRIA ANGLE: VALUE FOR ACOS {} IS BELOW -1".format(a))
            a = -1            
        return acos(a)
    def vminus(v1, v2):
        return [b-a for a, b in zip(v1, v2)]
    return max(angle(vminus(v1, v0), vminus(v2, v0)) for v0, v1, v2 in [(t[0], t[1], t[2]), (t[1], t[0], t[2]), (t[2], t[1], t[0])]) * 180 / pi



############################### EARCLIPPING FUNCTIONS ########################
#Code copied from mrbaozi (MIT license)
#https://github.com/mrbaozi/triangulation 
        
def IsConvex(a, b, c):
    # only convex if traversing anti-clockwise!
    crossp = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    if crossp >= 0:
        return True 
    return False 

def InTriangleBary(a, b, c, p):
    L = [0, 0, 0]
    eps = 0.00000001  # 17.08.2020 added one "0" to resolve conflict for one tria
    # calculate barycentric coefficients for point p
    # eps is needed as error correction since for very small distances denom->0
    L[0] = ((b[1] - c[1]) * (p[0] - c[0]) + (c[0] - b[0]) * (p[1] - c[1])) \
          /(((b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])) + eps)
    L[1] = ((c[1] - a[1]) * (p[0] - c[0]) + (a[0] - c[0]) * (p[1] - c[1])) \
          /(((b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])) + eps)
    L[2] = 1 - L[0] - L[1]
    # check if p lies in triangle (a, b, c)
    for x in L:
        if x >= 1 or x <= 0:
            return False  
    return True

def InTriangle(a, b, c, p):
    c1 = (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])
    #c1 = (x2-x1)*(yp-y1)-(y2-y1)*(xp-x1)
    c2 = (c[0] - b[0]) * (p[1] - b[1]) - (c[1] - b[1]) * (p[0] - b[0])
    #c2 = (x3-x2)*(yp-y2)-(y3-y2)*(xp-x2)
    c3 = (a[0] - c[0]) * (p[1] - c[1]) - (a[1] - c[1]) * (p[0] - c[0])
    #c3 = (x1-x3)*(yp-y3)-(y1-y3)*(xp-x3)
    if (c1 < 0 and c2 < 0 and c3 < 0) or (c1 > 0 and c2 > 0 and c3 > 0):
        return True
    return False


def IsClockwise(poly):
    # initialize sum with last element
    sum = (poly[0][0] - poly[len(poly)-1][0]) * (poly[0][1] + poly[len(poly)-1][1])
    # iterate over all other elements (0 to n-1)
    for i in range(len(poly)-1):
        sum += (poly[i+1][0] - poly[i][0]) * (poly[i+1][1] + poly[i][1])
    if sum > 0:
        return True
    return False

def GetEar(poly):
    size = len(poly)
    if size < 3:
        return []
    if size == 3:
        tri = (poly[0], poly[1], poly[2])
        del poly[:]
        return tri
    for i in range(size):
        tritest = False
        p1 = poly[(i-1) % size]
        p2 = poly[i % size]
        p3 = poly[(i+1) % size]
        #print("Testing vertex i: {} to be ear ".format(i))
        if IsConvex(p1, p2, p3):
            #print("   is convex")
            for x in poly:
                if not (x in (p1, p2, p3)) and InTriangle(p1, p2, p3, x):
                    #print("      but vertex x: {} is inside [{}, {}, {}]".format(x,p1,p2,p3))
                    tritest = True
            if tritest == False:
                #print("   is ear")
                del poly[i % size]
                return (p1, p2, p3)
    print('GetEar(): no ear found')
    return []

def GetMinEar(poly): ### NEW NEW: Try to cut first ears with minimal length to avoid long edges from one vertex
    size = len(poly)
    if size < 3:
        return []
    if size == 3:
        tri = (poly[0], poly[1], poly[2])
        del poly[:]
        return tri
    mindist = 99999999 #New
    minindex = None #New
    fallback = None #New3 Have tria in case no tria is fulfilling max angle requirement
    for i in range(size):
        tritest = False
        p1 = poly[(i-1) % size]
        p2 = poly[i % size]
        p3 = poly[(i+1) % size]
        if IsConvex(p1, p2, p3):
            for x in poly:
                if not (x in (p1, p2, p3)) and InTriangle(p1, p2, p3, x):
                    tritest = True
            if not tritest:
                if max_tria_angle([p1, p2, p3]) < 177:  # avoid trias being just a line
                    if distance(poly[(i-1) % size], poly[(i+1) % size]) < mindist:
                        mindist = distance(poly[(i-1) % size], poly[(i+1) % size])
                        minindex = i
                else:  # we have (nearly) a line tria, but a tria
                    fallback = i
                        
    if minindex == None: #New
        if fallback != None: #New3
            minindex = fallback #New3
        else: #New3
            print('GetEar(): no ear found')
            return []
    #NEW 3: below un-indented
    i = minindex #this was index with minimal ear-edge-length
    p1 = poly[(i-1) % size]
    p2 = poly[i % size]
    p3 = poly[(i+1) % size]
    del poly[i % size]
    return (p1, p2, p3)

def earclipTrias(pts):  ###original name of function was triangulate
    """
    Split a convex, simple polygon into triangles, using earclipping algorithm.
    Code literally copied from mrbaozi.
    https://github.com/mrbaozi/triangulation and turned into a module.
    
    Parameters:
        pts: a list of lists (of coordinates). E.g.
          [[ 229.23,   78.21], [ 258.49,   17.23], [ 132.09,  -22.43], [ 107.97,   23.23]]
           (note the last point isn't the first, it is assumed closed)
    Returns:
        A list of tuples. Each tuple contains three coordinates (representingone triangle)
    """
    tri = []
    plist = pts[::-1] if IsClockwise(pts) else pts[:]
    while len(plist) >= 3:
        #first_point = plist[0] ### NEW: set first point to the end in order to not get all triangles in a convex part from one vertex; HOWEVER takes much longer
        #plist = plist[1:]      ### NEW (above)     BETTER BUT NOT REALLY GOOD --> USE DELAUNEY TRIANGULATION
        #plist.append(first_point)  ### NEW (above)                              --> SIMPLY by flipping edges after earclip??
        #a = GetEar(plist)
        a = GetMinEar(plist) #### NEW NEW: try to cut minimal ear edge length first  ############# TBD: ALTERNATIVE: looks better
        if a == []:
            break
        if not IsClockwise(a): ###Not in original function; but we want only clockwise trias !!! ####
            a = a[::-1]
        tri.append(a)
    return tri
