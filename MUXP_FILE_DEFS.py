SUPPORTED_MUXP_FILE_VERSION = 0.1

MUST_BASE_VALUES = ["muxp_version", "id", "version", "area", "tile", "commands"]  # These values must be all present in muxp files

OPTIONAL_BASE_VALUES = ["description", "author", "source_dsf"]  # only strings are allowed optional

MUXP_COMMANDS = (
    "cut_polygon",
    "cut_ramp",
    "cut_flat_terrain_in_mesh",
    "cut_spline_segment",
    "update_network_levels",
    "limit_edges",
    "update_raster_elevation",
    "update_raster4spline_segment",
    "update_elevation_in_poly",
    "extract_mesh_to_file",
    "insert_mesh_from_file",
    "exit_without_update",
    "unflatten_default_apt",
)

MUXP_PARAMS = (
    'name',
    'elevation',
    'terrain',
    "include_raster_square_criteria",
    "edge_limit",
    "width",
    "profile_interval",
)

MUST_COMMAND_PARAMETERS = {"cut_polygon": ["coordinates"],
                           "cut_ramp": ["coordinates", "3d_coordinates"],
                           "cut_flat_terrain_in_mesh": ["coordinates", "terrain", "elevation"],
                           "cut_spline_segment": ["3d_coordinates", "terrain", "width", "profile_interval"],
                           "update_network_levels": ["coordinates", "road_coords_drapped"],
                           "limit_edges": ["coordinates", "edge_limit"],
                           "update_raster_elevation": ["coordinates", "elevation"],
                           "update_raster4spline_segment": ["3d_coordinates", "width"],
                           "update_elevation_in_poly": ["coordinates"],  # optionally either set flat by elevation or ramp by 3 3d_cooridinates
                           "extract_mesh_to_file": ["coordinates"],
                           "insert_mesh_from_file": ["coordinates", "terrain"],
                           "exit_without_update": [],
                           "unflatten_default_apt": ["name"]}

PARAMETER_TYPES = {"command": ["string"],  # this is just command-type
                   "_command_info": ["string"],  # added below, includes full command including added info after '.' like cut_polygon.inner
                   "name": ["string"],
                   "terrain": ["string"],
                   "elevation": ["float"],
                   "include_raster_square_criteria": ["string"],
                   "edge_limit": ["int"],
                   "profile_interval": ["float"],
                   "width": ["float"]}

OPTIONAL_PARAMETER_SETTING = {"elevation": None,
                              "name": "",
                              "include_raster_square_criteria": "corner_inside"}  # IF Parmeter is not given for command, the value in this dict is assigned

LIST_TYPES = {"coordinates": ["float", "float"],  # currently just float and int supported, everything else is string
              "3d_coordinates": ["float", "float", "float"],
              "road_coords_drapped": ["float", "float", "int"]}

COORD_SWAPPING = ["coordinates",
                  "road_coords_drapped"]  # If parameter/list is included here coordinates from lon/lat will be swapped to x,y
########## IMPORTANT: 3d_coordinates currently not swpapped !!!!!!!!!!! ############################################
