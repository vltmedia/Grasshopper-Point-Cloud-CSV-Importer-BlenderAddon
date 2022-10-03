# Blender Add-on Template
# Contributor(s): Justin Jaro (Justin@VLTMedia.com)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

bl_info = {
        "name": "Grasshopper Point Cloud CSV Importer",
        "description": "Import a CSV file from Grasshopper with a Point Cloud",
        "author": "Justin Jaro",
        "version": (1, 0),
        "blender": (2, 80, 0),
        "location": "Import > Grasshopper Point Cloud CSV",
        "warning": "", # used for warning icon and text in add-ons panel
        "wiki_url": "http://vltmedia.com",
        "tracker_url": "http://vltmedia.com",
        "support": "COMMUNITY",
        "category": "IO"
        }

"""
# Contributor(s): Justin Jaro (Justin@VLTMedia.com)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

Import a Grasshopper Point Cloud CSV file formatted as:
TIMESTAMP,ORIGIN_X,ORIGIN_Y,ORIGIN_Z,XAXIS_X,XAXIS_Y,XAXIS_Z,YAXIS_X,YAXIS_Y,YAXIS_Z,STATE

ORIGIN_X,ORIGIN_Y,ORIGIN_Z = Vecator3(x,y,z) Object Position

Can import as a point cloud with attributes for GeoNodes processing, and as an animated Cube per point.


"""
import numpy as np
import bpy
import bmesh
from mathutils import Vector,Matrix,Quaternion
from math import degrees, radians, acos, fmod, sin,cos

def read_some_data(context, filepath,  flip, scale, importType, name, rotateAxis, time_rate,post_rotateValue,smooth_batchSize):
    GHTrackerParser_ = GHTrackerParser(name)
    GHTrackerParser_.LoadFile(filepath, scale, importType, flip, rotateAxis, time_rate,post_rotateValue,smooth_batchSize)
    # f = open(filepath, 'r', encoding='utf-8')
    # data = f.read()
    # f.close()

    # # would normally load the data here
    # print(data)

    return {'FINISHED'}


# ImportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty, FloatProperty
from bpy.types import Operator


class GHPointCSVImporter(Operator, ImportHelper):
    """This appears in the tooltip of the operator and in the generated docs"""
    bl_idname = "ghpointcsvimporter.ipmort_data"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Import Grasshopper Point Cloud CSV"

    # ImportHelper mixin class uses this
    filename_ext = ".csv"

    filter_glob: StringProperty(
        default="*.csv",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    
    import_name: StringProperty(
        name="Imported Name",
        default="GH_Imported_Object",
        description="Name of the new object created, point cloud or cube",
        
    )

    import_type: EnumProperty(
        name="Import Type",
        description="Choose between two import types",
        items=(
            ('OPT_A', "Animation", "Import and apply animation to a cube for later processing"),
            ('OPT_B', "Point Cloud", "Import as a Point Cloud"),
        ),
        default='OPT_A',
    )
    
    flip_90: BoolProperty(
        name="Post Rotate Keys",
        description="Rotate the imported keyframe data per frame",
        default=True,
    )
    
    postrotate_Axis: EnumProperty(
        name="Post Rotate Axis",
        description="Axis to post rotate the imported keyframe data",
        items=(
            ('OPT_X', "X", "Rotate the imported keyframe data on the X axis"),
            ('OPT_Y', "Y", "Rotate the imported keyframe data on the Y axis"),
            ('OPT_Z', "Z", "Rotate the imported keyframe data on the Z axis"),
        ),
        default='OPT_Y',
    )
    post_rotateValue: FloatProperty(
        name="Post Rotate Angle (Degrees)",
        description="The angle to rotate the imported keyframe data per frame",
        default=45,
    )
    
    smooth_batchSize: FloatProperty(
        name="Smooth Frames Size",
        description="The number of frames to average for smoothing",
        options={'HIDDEN'},
        default=1,
    )

    time_rate: FloatProperty(
        name="Time Scale",
        description="Time/Speed Scale for the imported keyframe data",
        default=1,
    )

    # List of operator properties, the attributes will be assigned
    # to the class instance from the operator settings before calling.

    scale_factor: bpy.props.FloatProperty(name="Scale", default=0.01, description="Scale factor")

    def execute(self, context):
        return read_some_data(context, self.filepath, self.flip_90, self.scale_factor, self.import_type, self.import_name, self.postrotate_Axis , self.time_rate  , self.post_rotateValue, self.smooth_batchSize )

# Only needed if you want to add into a dynamic menu.
def menu_func_import(self, context):
    self.layout.operator(GHPointCSVImporter.bl_idname, text="Grasshopper Point Cloud CSV")


# Register and add to the "file selector" menu (required to use F3 search "Text Import Operator" for quick access).
def register():
    bpy.utils.register_class(GHPointCSVImporter)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    bpy.utils.unregister_class(GHPointCSVImporter)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)

import os

def point_cloud(ob_name, coords, vx, vy, pointsRotation,  pointsRotation4, edges=[], faces=[]):
    """Create point cloud object based on given coordinates and name.

    Keyword arguments:
    ob_name -- new object name
    coords -- float triplets eg: [(-1.0, 1.0, 0.0), (-1.0, -1.0, 0.0)]
    """

    # Create new mesh and a new object
    me = bpy.data.meshes.new(ob_name + "Mesh")
    ob = bpy.data.objects.new(ob_name, me)

    # Make a mesh from a list of vertices/edges/faces
    me.from_pydata(coords, edges, faces)

    # Display name and update the mesh
    ob.show_name = True
    me.update()
    bm = bmesh.new()
    bm.from_mesh(me)

    vxatt = bm.verts.layers.float_vector.new("vx")
    vyatt = bm.verts.layers.float_vector.new("vy")
    rotatt = bm.verts.layers.float_vector.new("rot")
    rotcolatt = bm.verts.layers.float_color.new("rot4")
    for index , meshver in enumerate(bm.verts):
        meshver[vxatt] = vx[index]
        meshver[vyatt] = vy[index]
        meshver[rotatt] = pointsRotation[index]
        meshver[rotcolatt] = pointsRotation4[index]
    if me.is_editmode:
        bmesh.update_edit_mesh(me)
    else:
        bm.to_mesh(me)
        me.update()

    bm.free()
    del bm
    # ob.data.attributes.new(name='vx', type='FLOAT_VECTOR', domain='POINT')
    # ob.data.attributes.new(name='vy', type='FLOAT_VECTOR', domain='POINT')
    # ob.data.attributes['vx'].data.foreach_set('vector', vx)
    # ob.data.attributes['vy'].data.foreach_set('vector', vy)
    return ob

class GHTrackerParser:
    def __init__(self, newname):
        self.name = newname
        self.rawdata = []
        self.points = []
        self.pointsVx = []
        self.pointsVy = []
        self.targetObj = "defaultnothing-"
        
    def setTargetObject(self, name):
        self.targetObj = bpy.context.scene.objects[name]
    
    def checkTargetObject(self):
        if self.targetObj == "defaultnothing-":
            # create a new cube
            bpy.ops.mesh.primitive_cube_add()
            self.targetObj = bpy.context.selected_objects[0]
            self.targetObj.name = self.name
        
    def LoadFile(self, filepath, scale = 1, importType = 'OPT_A', flip=False, rotateAxis = 'X', time_rate=1,post_rotateValue=90,smooth_batchSize=4):
        self.rotateAxis = rotateAxis
        self.flip = flip
        self.scale = scale
        self.time_rate = time_rate
        self.post_rotateValue = post_rotateValue
        self.smooth_batchSize = smooth_batchSize
        self.importType = importType
        #filee = open("F:/Projects/CodeDump/ethicaGrasshopperParse/Recording_001.csv", "r")
        filee = open(filepath, "r")
        self.rawdata = [line.split(',') for line in filee.readlines()]
        self.rawdata.pop(0)
        filee.close()
        
        self.GeneratePointCloud()
        
    def parsePoints(self):
        self.points = self.smoothPoints([(float(line[1])* self.scale , float(line[2]) * self.scale, float(line[3]) * self.scale) for line in self.rawdata])
        self.parsePointsVx()
        self.parsePointsVy()
        self.parseRotation()

    def parsePointsVx(self):
        self.pointsVx = self.smoothPoints([[float(line[4]) , float(line[5]) , float(line[6]) ] for line in self.rawdata])

    def parsePointsVy(self):
        self.pointsVy = self.smoothPoints([[float(line[7]) , float(line[8]) , float(line[9]) ] for line in self.rawdata])

    def smoothPoints(self, pointsList ):
        newpoints = []
        if self.smooth_batchSize > 1:
            for point in range(round(len(pointsList)/self.smooth_batchSize)):
                newVect = [0,0,0]
                for vect in range(round(self.smooth_batchSize)):
                    indx = vect * point
                    arr = pointsList[indx]
                    for axis in range(3):
                        newVect[axis] += arr[axis]
                newVect = [newVect[0] / self.smooth_batchSize, newVect[1] / self.smooth_batchSize, newVect[2] / self.smooth_batchSize ]
                newpoints.append(newVect)
        else:
            newpoints = pointsList
            self.smooth_batchSize = 0
        return newpoints

    def parseRotation(self):
        self.pointsRotation = []
        self.pointsRotation4 = []
        if self.importType == 'OPT_A':
            self.checkTargetObject()
        for indx, pointx in enumerate(self.pointsVx):
            pointov = Vector((self.points[indx][0],self.points[indx][1],self.points[indx][2]))
            pointxv = Vector((self.pointsVx[indx][0],self.pointsVx[indx][1],self.pointsVx[indx][2]))
            pointyv = Vector((self.pointsVy[indx][0],self.pointsVy[indx][1],self.pointsVy[indx][2]))
            direction = pointyv - pointov
            tracker, rotator = (('X','Z'), 'Y')
            quat = direction.to_track_quat(*tracker)
            # lookat = self.lookAt(pointov, pointxv, pointyv)
            
            flipdeg = radians(0)
            if self.flip:
                flipdeg = radians(self.post_rotateValue)
            rollMatrix = Matrix.Rotation(0, 4, rotator)
            pointov = pointov.to_tuple()
            
            self.pointsRotation.append([degrees(a) for a in pointxv.rotation_difference(pointyv).to_euler()])
            # self.pointsRotation.append([degrees(a) for a in pointxv.rotation_difference(pointyv).to_euler()])
            # self.pointsRotation4.append([a for a in lookat])
            self.pointsRotation4.append([a for a in quat])
            if self.importType == 'OPT_A':
                self.targetObj.matrix_world = quat.to_matrix().to_4x4() @ rollMatrix
                self.targetObj.location = pointov
                # self.targetObj.rotation_axis_angle = lookat
                if self.rotateAxis == 'OPT_X':
                    self.targetObj.rotation_euler[0] = self.targetObj.rotation_euler[0] + flipdeg
                if self.rotateAxis == 'OPT_Y':
                    self.targetObj.rotation_euler[1] = self.targetObj.rotation_euler[1] + flipdeg
                if self.rotateAxis == 'OPT_Y':
                    self.targetObj.rotation_euler[2] = self.targetObj.rotation_euler[2] + flipdeg
                self.targetObj.keyframe_insert(data_path="location", frame=round((indx + self.smooth_batchSize) * self.time_rate))
                self.targetObj.keyframe_insert(data_path="rotation_euler", frame=round((indx + self.smooth_batchSize) * self.time_rate))
        
    def lookAt(self,  sourcePoint,   front,  up):
    
        toVector = (front - sourcePoint).normalized();

        #//compute rotation axis
        rotAxis = front.cross(toVector).normalized();
        d = np.linalg.norm(np.square(rotAxis), ord=1, axis=0)

        print("HEYY  : " , d)
        if d == 0:
            rotAxis = up;

        #//find the angle around rotation axis
        dot = front.dot(toVector);
        ang = acos( fmod( dot, 1 ) )

        #//convert axis angle to quaternion
        return self.angleAxisf(rotAxis, ang)
    def NormalizeData(self, data):
        return (data - np.min(data)) / (np.max(data) - np.min(data))
    def angleAxisf(self, axis, angle):
        print("Axis : " , axis)
        print("angle : " , angle)
        s = sin(angle / 2)
        u = axis.normalized()
        x = cos(angle / 2)
        y = u.x * s
        z = u.y * s
        w = u.z * s
        return Quaternion([x, y, z, w])
    
    
    def GeneratePointCloud(self):
        self.parsePoints()
        
        if self.importType == 'OPT_B':
            pc = point_cloud(self.name, self.points, self.pointsVx, self.pointsVy, self.pointsRotation, self.pointsRotation4)

            # Link object to the active collection
            bpy.context.collection.objects.link(pc)

        # Alternatively Link object to scene collection
        #bpy.context.scene.collection.objects.link(pc)
        

    

if __name__ == "__main__":
    register()

