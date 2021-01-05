# obj_ex_import.py    Version: 0.3.6 exp
# ---------------------------------------------------------
# MUXP functions for exporting and importing X-Plane Mesh
# to/from Wavefront .obj files

from logging import getLogger
from math import sqrt
from muxp_math import x2lon, y2lat, IsClockwise, distances2coordinates


def read_obj_file(filename, logname, default_terrain, type_def, area):
    """
    Reads .obj filename and adapts muxp area trias with this new mesh
    default_terrain is the terrain that will be used for are trias if nothing else is defined
    """
    log = getLogger(logname + "." + __name__)  # logging based on pre-defined logname
    log.info("Reading .obj File: {}".format(filename))
    center = []  # coordinates for center-offset
    vertices = [[None]]  # list of vertices to be read; first dummy element to match index starting with 1
    normals = [[None]]  # list of vertex normals to be read; first dummy element to match index starting with 1
    trias = []  # list or trias read
    area_trias = []  # list of area trias returned to be inserted
    material = []  # list of used materials with [starting tria index, material_name] as values
    outer_edges = dict()  # dict with (v1_index, v2_index) as key; at the end keys are all edges of poly outside
    
    # Read mesh from .obj file
    with open(filename, encoding="utf8", errors="ignore") as f:
        # Checking if file exists was done in muxp.py before calling this function!
        current_object = ""  # keeps track for which object type information is read
        for line in f:
            if line.find("o ") == 0:
                if line.find("CENTER_Coordinates") > 0:
                    current_object = "CENTER"
                elif line.find("MESH") > 0:
                    current_object = "MESH"
            elif line.find("v ") == 0 and current_object == "CENTER":  # center vertex definition in .obj file
                v = line.split()
                v.pop(0)  # remove first element 'v' from list
                try:
                    v = [float(v[0]), float(v[1]), float(v[2])]
                except (ValueError, IndexError):
                    log.info("Line in .obj file defining v does not contain three floats but {}".format(v))
                    return []
                if type_def.find("ercator") >= 0:  # matching mercartor and Mercator
                    center.append(v[0] * 10 ** 9 + v[1] * 10 ** 6 + v[2] * 1000)
                else:  # for degress
                    center.append(v[0] * 1000 + v[1] + v[2] / 10000)
                vertices.append(v)  # append also if not needed for mesh, but relevant for indexing in faces
            elif line.find("v ") == 0 and current_object == "MESH":  # mesh vertex definition in .obj file
                v = line.split()
                v.pop(0)  # remove first element 'v' from list
                try:
                    v = [float(v[0]), float(v[1]), float(v[2])]
                except (ValueError, IndexError):
                    log.info("Line in .obj file defining v does not contain three floats but {}".format(v))
                    return []
                vertices.append(v)
            elif line.find("vn ") == 0:  # vertex normal definition in .obj file
                vn = line.split()
                vn.pop(0)  # remove 'vn' from list
                try:
                    vn = [float(vn[0]), float(vn[1]), float(vn[2])]
                except (ValueError, IndexError):
                    log.error("Line in .obj file defining vn does not contain three floats but {}".format(vn))
                    return []
                normals.append(vn)
            elif line.find("f ") == 0 and current_object == "MESH":  # face definition in .obj file, only for mesh
                # IMPORTANT: THIS VERSION ASSUMES FACES AS V//VN and trias only!
                f = line.split()
                f.pop(0)  # remove first element 'f' from list
                if len(f) != 3:
                    log.error("Line in .obj file defining f defines no triangle but {}".format(f))
                    return []
                t = []  # new tria to be defined
                fv = [None, None, None]  # reference to vertices of current face (tria)
                fvn = [None, None, None]  # reference to vertex normals of current face (tria)
                for i in range(3):
                    f[i] = f[i].split('/')
                    if len(f[i]) != 3:
                        log.error(
                            "Line in .obj file defining f defines vertex not having 3 values but {}".format(f))
                        return []
                    try:
                        fv[i] = int(f[i][0])
                        fvn[i] = int(f[i][2])
                    except ValueError:
                        log.error("Line in .obj file defining f does not have correct integers but {}".format(f))
                        return []
                for i in range(3):
                    # t.append(vertices[fv[i]])  ### NEW: append vertex coordinates later, when coordinates have been calculated
                    t.append(fv[i])  # for the moment just store index to vertex number
                    if fv[i] < fv[(i + 1) % 3]:
                        edge_sorted = (fv[i], fv[(i + 1) % 3])
                    else:
                        edge_sorted = (fv[(i + 1) % 3], fv[i])
                    if edge_sorted in outer_edges:
                        outer_edges.pop(edge_sorted)  # if the same edge appears twice it is inside
                    else:
                        outer_edges[edge_sorted] = True  # edge read the first time
                for i in range(3):
                    vnx, vny, vnz = normals[fvn[i]][0], normals[fvn[i]][1], normals[fvn[i]][2]
                    ln = sqrt(vnx * vnx + vny * vny + vnz * vnz)  # length of vertex normal
                    #t[i] = t[i] + [round(vnx / ln, 4), round(vny / ln, 4)]
                    t.append([round(vnx / ln, 4), round(vny / ln, 4)])
                trias.append(t)
            elif line.find("usemtl ") == 0 and current_object == "MESH":  # change of material / terrain type
                mat = line.split()
                material.append([len(trias), mat[1]])
                
    # Basic checks if read data is okay
    if len(center) >= 3:
        if type_def.find("ercator") >= 0:  # matching mercator and Mercator
            log.info("Mesh .obj file read with center-offset (Mercator): {}".format(center))
        else:
            log.info("Mesh .obj file read with center-offset (degrees): {}".format(center))
        if len(center) > 3:
            log.warning("CENTER object had more than 3 vertices, the additional ones are ignored!")
    elif len(center) == 0:
        log.warning("Read .obj file has no object CENTER for coordinate offset. Using [0, 0, 0] as center!")
        center = [0, 0, 0]
    else:
        log.error("Read .obj file has no object CENTER has less than 3 coordinates/vertices. Mesh not inserted!")
        return []
    if len(vertices) < 6:
        log.error("Read .obj file has no triangle defined or object MESH missing. Mesh not inserted!")
        return []
    
    # Convert coordinates of vertices back to full degrees without CENTER

    if type_def.find("ercator") >= 0:  # matching mercator and Mercator
        for i in range(len(vertices)):  # as vertices needed below also add offset and convert back from Mercator
            if len(vertices[i]) >= 3:
                vertices[i] = [x2lon(vertices[i][0] + center[0]), y2lat(vertices[i][1] + center[1]),
                               vertices[i][2] + center[2]]
    elif type_def.find("degrees") >= 0:
        for i in range(len(vertices)):  # as vertices needed below also add offset and convert back from Mercator
            log.info("Converting obj-vertex {}".format(vertices[i]))  # JUST TESTING, TO BE REMOVED
            if len(vertices[i]) >= 3:
                vertices[i] = [vertices[i][0] + center[0], vertices[i][1] + center[1], vertices[i][2] + center[2]]
            log.info("   to: {}".format(vertices[i]))  # JUST TESTING, TO BE REMOVED
    elif type_def.find("meters") >= 0:  # default encoding is meters difference from center
        for i in range(len(vertices)):  # as vertices needed below also add offset and convert back from Mercator
            log.info("Converting obj-vertex {}".format(vertices[i]))  # JUST TESTING, TO BE REMOVED
            if len(vertices[i]) >= 3:
                vertices[i] = distances2coordinates(center, vertices[i])
            log.info("   to: {}".format(vertices[i]))  # JUST TESTING, TO BE REMOVED

    # Define now MUXP area trias including their correct coordinates and terrain
    patch_id_terrain = area.getPatchID(default_terrain)  # WARNING: This new patch has still no poolDefintion in first Command!
    patch_id = patch_id_terrain  # use default terrain for patches if not changed below
    log.info("Following trias have been read from file:")
    material_index = 0
    material.append([len(trias), "END OF MATERIAL LIST"])  # have closing element as below always looking for next
    for tria_num, tria in enumerate(trias):
        if material[material_index][0] == tria_num:  # we have new material starting at that tria
            ########## TBD: Also allow other terrain types to be im/exported ########################
            if material[material_index][1] == "terrain_Water":
                patch_id = area.getPatchID("terrain_Water")
                log.info(
                    "Starting with tria number {} to use material/terrain: {}".format(tria_num, "terrain_Water"))
            else:
                patch_id = patch_id_terrain
                log.info("Starting with tria number {} to use material/terrain: {}".format(tria_num, default_terrain))
            material_index += 1
        # log.info("Tria in old e.g. Mercator offset: {}".format(tria))  ##### TESTING ONLY #######
        new_v = [None, None, None]
        for e in range(3):
            # For the vertex also center-offset is added and converted back from Mercator to degrees
            # new_v[e] = [x2lon(tria[e][0] + center[0]), y2lat(tria[e][1] + center[1]), tria[e][2] + center[2],
            #           tria[e][3], tria[e][4]]
            new_v[e] = [vertices[tria[e]][0], vertices[tria[e]][1], vertices[tria[e]][2], tria[e+3][0], tria[e+3][1]]  # NEW: use index to vertices where coordinates have now been calculated above
            # log.info("   vertex {}: {}".format(e, new_v[e]))
            # This version only creates simple vertices without s/t coordinates
        area_trias.append([new_v[0], new_v[1], new_v[2], [None, None], [None, None], [None, None], patch_id])
        # As tria is completely new, there is no pool/patchID where tria is inside, so None
        # ==> If None makes problems use [None, None] or [-1, -1]
        area_trias[-1] = area.ensureClockwiseTria(area_trias[-1])
        log.info(area_trias[-1])

    # Identify outline (outer_edges) of read mesh triangles
    log.info("Following outer edges identified: {}".format(outer_edges))
    v = next(iter(outer_edges))
    oe_poly = [v[0]]  # list with indices to vertices that build the poly along outer edges
    next_v = v[1]  # index to next vertex that needs to be found on outline polygon
    while len(outer_edges) > 1:  # last edge ist clear, as this is just way back to first vertex
        outer_edges.pop(v)
        log.info("Outer Poly: {} searching next: {}".format(oe_poly, next_v))
        next_v_found = False
        for v in outer_edges:
            if next_v in v:
                oe_poly.append(next_v)
                if next_v == v[0]:
                    next_v = v[1]
                else:
                    next_v = v[0]
                next_v_found = True
                break
        if not next_v_found:
            log.warning("Mesh to be inserted is not continuous. Following part missing in insertion {}!".format(outer_edges))
            if next_v == oe_poly[0]:
                log.warning("However even mesh is not continuous, found closed poly for outer edges and continue with insertion.")
                break
            else:
                log.error("Found no closed polygon for outer edges. Can't insert this mesh from file!")
                return[]
    log.info("Outer Edges as Poly: {}".format(oe_poly))
    for i in range(len(oe_poly)):
        oe_poly[i] = vertices[oe_poly[i]]
    oe_poly = oe_poly[oe_poly.index(min(oe_poly)):] + oe_poly[:oe_poly.index(min(oe_poly))]
    #  oe_poly start now with the most south-west corner
    oe_poly.append(oe_poly[0])  # make it a closed poly
    if IsClockwise(oe_poly):
        oe_poly.reverse()  # inner poly for triangulation should be anti-clockwise
    log.info("Outer Edges as Poly: {}".format(oe_poly))

    return area_trias, oe_poly


def match_border_with_existing_vertices(border, trias, area_trias, decimals=5):
    """
    For border vertices (list of [x,y] coordinates) around trias from .obj mesh the exact coordinates and
    elevation of existing vertices in area_trias will be selected. The vertices in border and area_trias
    are adapted accordingly.
    Matching is done value of decimals after decimal points of coordinates. Default value 5 is about 1m matching.
    """
    border_dict = {}  # set up dictionary with all coords of border to find additional on those coords
    vertices = {}  # dict of existing vertices from dsf which are source for correct coordinates and elevation
    for i, c in enumerate(border):
        border_dict[(round(c[0], decimals), round(c[1], decimals))] = i  # round to range of m in case of value 5
    for t in area_trias:
        for v in t[:3]:
            if (round(v[0], decimals), round(v[1], decimals)) in border_dict:
                vertices[(round(v[0], decimals), round(v[1], decimals))] = v  # add v for these border coordinates
                border[border_dict[(round(v[0], decimals), round(v[1], decimals))]] = [v[0], v[1]]  # update border coordinates
    for t in trias:
        for v in t[:3]:
            if (round(v[0], decimals), round(v[1], decimals)) in vertices:
                dsf_v = vertices[(round(v[0], decimals), round(v[1], decimals))]
                for i in range(5):  # take coordinates from dsf vertex incl. vertex normal
                    v[i] = dsf_v[i]
