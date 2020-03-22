# -*- coding: utf-8 -*-
#******************************************************************************
#
# muxp_math.py   Version: 0.0.3 exp
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


def createFullCoords(x, y, t):
    """
    returns for coordinates (x, y) in tria t (list of 3 vertex list with all coords of vertices of t) the full coordinates
    """
    v = [x, y]
    l0, l1 = PointLocationInTria(v, t) # returns length for vectors from point t3 with l0*(t2-t0) and l1*(t2-t1)
    elevation = t[2][2] + l0 * (t[0][2] - t[2][2])  + l1 * (t[1][2] - t[2][2])
    if elevation < -32765:
        v.append(-32768.0) #append correct elevation (stays -32768.0 in case of raster)
    else:
        v.append(elevation)
    v.extend([0, 0]) ### leave normal vectors to 0 ##### TO BE ADAPTED IN CASE OF NO RASTER !!!!!
    for i in range(5, len(t[0])): #go through optional coordinates s/t values based on first vertex in tria
        v.append(t[2][i] + l0 * (t[0][i] - t[2][i])  + l1 * (t[1][i] - t[2][i]))
    return v
        
