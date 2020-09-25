#################################################################################################
# The following code is taken from https://bitbucket.org/marangonico/muxp_conv/src/master/
# with allowance by it's author Nicola Marangon
#
# It allows conversion from MUXP to WED and back
#################################################################################################

import yaml
from collections import OrderedDict
from xmltodict import parse, unparse
from MUXP_FILE_DEFS import MUXP_COMMANDS, MUXP_PARAMS


class MUXP(object):

    muxp_file = None
    muxp_yaml = None
    wed = None
    # wed_xml = None
    # o = None
    # world = None
    # max_id = 0


    def __init__(self, muxp_file=None):
        self.muxp_file = muxp_file

        if self.muxp_file:
            self.load()

    def load(self, muxp_file=None):
        if muxp_file:
            self.muxp_file = muxp_file

        with open(self.muxp_file) as file:
            self.muxp_yaml = yaml.load(file, Loader=yaml.FullLoader)

    @staticmethod
    def wed_check_and_add_meta(wed, parent, value, name):
        if name in value:
            wed.add_meta(object_name=f"{name}:{value[name]}", parent=parent)

    def wed_inject(self, wed_file=None):

        wed = WED(wed_file=wed_file)

        group_muxp = wed.get_object('Group', 'muxp')
        if group_muxp:
            wed.delete_object(group_muxp)

        wed.add_group_muxp()

        for k, v in self.muxp_yaml.items():

            commands = k.split('.')

            if commands[0] in ('muxp_version', 'id', 'version', 'description', 'author', 'tile', ):
                ##### TBD: HAVE THIS META-DATA GLOBALLY DEFINED ###############
                wed.add_meta(object_name=f"{k}:{v}")

            elif commands[0] == 'area':
                lats_lons = v.split()
                # v='45.392391  45.403086  6.625944  6.644899' -> ['45.392391', '45.403086', '6.625944', '6.644899']
                coords = [
                    (lats_lons[0], lats_lons[2]),
                    (lats_lons[1], lats_lons[2]),
                    (lats_lons[1], lats_lons[3]),
                    (lats_lons[0], lats_lons[3]),
                    (lats_lons[0], lats_lons[2]),
                ]
                wed.add_poly(
                    object_name='area:', coords=coords
                )

            else:

                if commands[0] in MUXP_COMMANDS:

                    g = wed.add_group(k)

                    if 'coordinates' in v:
                        ref_lat, ref_lon = v['coordinates'][0].split()
                    elif '3d_coordinates' in v:
                        ref_lat, ref_lon, elevation = v['3d_coordinates'][0].split()
                    elif 'road_coords_drapped' in v:
                        ref_lat, ref_lon, elevation = v['road_coords_drapped'][0].split()
                    else:
                        ref_lat = None

                    if ref_lat:
                        wed.set_reference_values(lat=ref_lat, lon=ref_lon)

                    for param in MUXP_PARAMS:
                        self.wed_check_and_add_meta(wed, g, v, param)

                    if 'coordinates' in v:
                        coords = []
                        for coord in v['coordinates'][0:-1]:
                            coords.append(coord.split())
                        wed.add_poly(object_name='coordinates', parent=g, coords=coords)

                    if '3d_coordinates' in v:
                        coords = []
                        for coord in v['3d_coordinates']:
                            coords.append(coord.split())
                        wed.add_string(object_name='3d_coordinates', parent=g, coords=coords)

                    if 'road_coords_drapped' in v:
                        coords = []
                        for coord in v['road_coords_drapped'][0:-1]:
                            coords.append(coord.split())
                        wed.add_poly(object_name='road_coords_drapped', parent=g, coords=coords)

        return wed.emit_xml()

    def wed_collect_area(self, wed_object):

        lat_min = 90
        lat_max = -90
        lon_min = 180
        lon_max = -180

        ring = self.wed.get_object(object_id=wed_object['children']['child']['@id'])
        for child in ring['children']['child']:
            o = self.wed.get_object(object_id=child['@id'])

            lat = float(o['point']['@latitude'])
            lon = float(o['point']['@longitude'])

            if lat > lat_max:
                lat_max = lat

            if lat < lat_min:
                lat_min = lat

            if lon > lon_max:
                lon_max = lon
            if lon < lon_min:
                lon_min = lon

        area = f"{lat_min}  {lat_max}  {lon_min}  {lon_max}"

        return area

    def wed_collect_coordinates(self, wed_object):

        coords = []

        ring = self.wed.get_object(object_id=wed_object['children']['child']['@id'])
        for child in ring['children']['child']:
            o = self.wed.get_object(object_id=child['@id'])
            lat = float(o['point']['@latitude'])
            lon = float(o['point']['@longitude'])
            # coords.append(f'{lat:18} {lon:18}')
            coords.append(f'{lat} {lon}')

        coords.append(coords[0])

        return coords

    def wed_collect_3d_coordinates(self, wed_object):

        coords = []

        if isinstance(wed_object['children']['child'], list):
            wed_coordinates = wed_object['children']['child']
        else:
            ring = self.wed.get_object(object_id=wed_object['children']['child']['@id'])
            wed_coordinates = ring['children']['child']

        for child in wed_coordinates:
            o = self.wed.get_object(object_id=child['@id'])
            lat = float(o['point']['@latitude'])
            lon = float(o['point']['@longitude'])

            object_name = o['hierarchy']['@name']
            try:
                if float(object_name) == int(float(object_name)):
                    elevation = int(float(object_name))
                else:
                    elevation = float(object_name)
            except ValueError as e:
                print(f"3d_coordinates: object name should be elevation, but is {object_name}")

            coords.append(f'{lat} {lon} {elevation}')

        if wed_object['@class'] != 'WED_StringPlacement':
            coords.append(coords[0])

        return coords

    def wed_collect_command(self, wed_object):

        cmd_yaml = {}

        if isinstance(wed_object['children']['child'], list):
            children = wed_object['children']['child']
        else:
            children = [wed_object['children']['child'], ]

        for child in children:

            o = self.wed.get_object(object_id=child['@id'])
            wed_command = o['hierarchy']['@name']

            if ':' in wed_command and o['@class'] == 'WED_ObjPlacement':
                key, value = wed_command.split(':')
                if key in ('muxp_version', 'version', 'elevation', 'width', 'profile_interval', ):
                    if float(value) == int(float(value)):
                        cmd_yaml[key] = int(float(value))
                    else:
                        cmd_yaml[key] = float(value)
                else:
                    cmd_yaml[key] = value

            elif wed_command == 'coordinates':
                cmd_yaml['coordinates'] = self.wed_collect_coordinates(o)

            elif wed_command == '3d_coordinates':
                cmd_yaml['3d_coordinates'] = self.wed_collect_3d_coordinates(o)

            pass

        return cmd_yaml

    def wed2muxp(self, wed_file=None):

        self.wed = WED(wed_file=wed_file)
        self.muxp_yaml = {}

        g = self.wed.get_object('Group', 'muxp')

        for child in g['children']['child']:
            o = self.wed.get_object(object_id=child['@id'])

            wed_command = o['hierarchy']['@name']

            if ':' in wed_command and o['@class'] == 'WED_ObjPlacement':
                key, value = wed_command.split(':')

                if key in ('muxp_version', 'version', ):
                    if float(value) == int(float(value)):
                        self.muxp_yaml[key] = int(float(value))
                    else:
                        self.muxp_yaml[key] = float(value)
                else:
                    self.muxp_yaml[key] = value

            elif ':' in wed_command and wed_command == 'area:':
                self.muxp_yaml['area'] = self.wed_collect_area(o)

            elif o['@class'] == 'WED_Group':

                # if '.' in wed_command:
                #     cmd, label = wed_command.split('.')
                # else:
                #     cmd = wed_command
                if o['hierarchy']['@hidden'] == '0':
                    self.muxp_yaml[wed_command] = self.wed_collect_command(o)

        # for command in ('muxp_version', 'id', 'version', 'description', 'author', 'tile', ):
        #     o = g.get_object()

        y = yaml.dump(
            self.muxp_yaml, default_flow_style=False, sort_keys=False).replace("\'", "")

        return y


class WED(object):

    wed_file = None
    wed_xml = None
    o = None
    world = None
    group_muxp = None
    max_id = 0

    ref_lat = 0
    ref_lon = 0

    def __init__(self, wed_file=None):
        self.wed_file = wed_file
        if self.wed_file:
            self.load()

    def load(self, wed_file=None):
        if wed_file:
            self.wed_file = wed_file
        self.wed_xml = parse(open(self.wed_file).read())
        self.o = self.wed_xml['doc']['objects']['object']
        self.world = self.get_object(class_name='Group', object_name='world')

        for o in self.o:
            if int(o['@id']) > self.max_id:
                self.max_id = int(o['@id'])

    @staticmethod
    def normalize_class_name(class_name):
        if class_name[0:3] != 'WED_':
            class_name = 'WED_' + class_name
        return class_name

    def get_object(self, class_name='', object_name='', object_id=''):

        class_name = self.normalize_class_name(class_name)

        try:
            object_id = str(object_id)
        except TypeError:
            pass

        for o in self.o:
            if object_name:
                if o['@class'] == class_name and o['hierarchy']['@name'].upper() == object_name.upper():
                    return o
            elif object_id:
                if o['@id'] == object_id:
                    return o

        return None

    def get_children(self, parent):

        children_objects = []

        for o in self.o:
            if o['@parent_id'] == parent['@id']:
                children_objects.append(o)

        return children_objects

    def add_object(self, class_name='', object_name='', parent=None, point=None):

        class_name = self.normalize_class_name(class_name)

        if self.get_object(class_name, object_name):
            raise Exception(f'object (class_name={class_name}, object_name={object_name} already exists')

        if parent is None:
            parent = self.group_muxp

        self.max_id += 1
        o = {
            '@class': class_name,
            '@id': str(self.max_id),
            '@parent_id': parent['@id'],
            'children': {},
            'hierarchy': {
                '@name': object_name, '@locked': '0', '@hidden': '0'
            },
        }

        if point:
            o['point'] = point

        self.o.append(o)

        if parent:
            if 'child' not in parent['children']:
                parent['children']['child'] = []

            if isinstance(parent['children']['child'], OrderedDict):
                child = parent['children']['child']
                parent['children']['child'] = [child, ]

            parent['children']['child'].append({'@id': o['@id']})

        return o

    def delete_children(self, children_ids=[]):

        for o in self.o:
            if o['@id'] in children_ids:
                if o['children']:
                    self.delete_children(o['children']['child'])
                self.o.remove(o)

    def delete_object(self, obj):

        for o in self.o:
            if o['@id'] == obj['@parent_id']:
                o['children']['child'].remove({'@id': obj['@id']})

        children_ids = [
            obj['@id'],
        ]

        self.delete_children(children_ids)

        if o['children']:
            children = o['children']['child']
            for child in children:
                self.delete_object(child)

        self.delete_children()

    def add_simple_bezier_boundary_node(self, object_name='', parent=None, lat=0, lon=0):
        point = {
            '@latitude': f'{lat}',
            '@longitude': f'{lon}',
            '@split': '0',
            '@ctrl_latitude_lo': '0.0',
            '@ctrl_longitude_lo': '0.0',
            '@ctrl_latitude_hi': '0.0',
            '@ctrl_longitude_hi': '0.0'
        }
        return self.add_object(
            class_name="SimpleBezierBoundaryNode", object_name=object_name, parent=parent, point=point)

    def add_group(self, object_name='', parent=None):
        return self.add_object('Group', object_name=object_name, parent=parent)

    def add_group_muxp(self):
        self.group_muxp = self.add_group('muxp', self.world)

    def add_poly(self, object_name='', parent=None, coords=[]):
        if parent is None:
            parent = self.group_muxp
        polygon = self.add_object('PolygonPlacement', object_name=object_name, parent=parent)
        ring = self.add_object('Ring', 'muxp_ring', polygon)
        for coord in coords:

            if len(coord) == 2:
                self.add_simple_bezier_boundary_node(
                    object_name='muxp_node', parent=ring, lat=coord[0], lon=coord[1])
            elif len(coord) == 3:
                self.add_simple_bezier_boundary_node(
                    object_name=str(coord[2]), parent=ring, lat=coord[0], lon=coord[1])

    def add_string(self, object_name='', parent=None, coords=[]):
        if parent is None:
            parent = self.group_muxp
        string = self.add_object('StringPlacement', object_name=object_name, parent=parent)
        for coord in coords:

            if len(coord) == 2:
                self.add_simple_bezier_boundary_node(
                    object_name='muxp_node', parent=string, lat=coord[0], lon=coord[1])
            elif len(coord) == 3:
                self.add_simple_bezier_boundary_node(
                    object_name=str(coord[2]), parent=string, lat=coord[0], lon=coord[1])

    def add_meta(self, object_name='', parent=None):
        point = {
            "@latitude": str(self.ref_lat),
            "@longitude": str(self.ref_lon),
            "@heading": 0,
        }
        return self.add_object('ObjPlacement', object_name=object_name, parent=parent, point=point)

    def get_meta(self, object_name='', parent=None):
        point = {
            "@latitude": str(self.ref_lat),
            "@longitude": str(self.ref_lon),
            "@heading": 0,
        }
        return self.get_object(class_name='ObjPlacement', object_name=object_name, parent=parent, point=point)

    def set_reference_values(self, parent=None, lat=0, lon=0):
        self.ref_lat = lat
        self.ref_lon = lon

    def emit_xml(self):
        return unparse(self.wed_xml, pretty=True)

