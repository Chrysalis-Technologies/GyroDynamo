# coding: utf-8
import math, random, io
from objc_util import *
import ui

# Load SceneKit
load_framework('SceneKit')
load_framework('SpriteKit')

SCNNode = ObjCClass('SCNNode')
SCNScene = ObjCClass('SCNScene')
SCNBox = ObjCClass('SCNBox')
SCNSphere = ObjCClass('SCNSphere')
SCNCone = ObjCClass('SCNCone')
SCNCylinder = ObjCClass('SCNCylinder')
SCNMaterial = ObjCClass('SCNMaterial')
SCNLight = ObjCClass('SCNLight')
SCNCamera = ObjCClass('SCNCamera')
SCNParticleSystem = ObjCClass('SCNParticleSystem')
SCNGeometrySource = ObjCClass('SCNGeometrySource')
SCNGeometryElement = ObjCClass('SCNGeometryElement')
SCNGeometry = ObjCClass('SCNGeometry')
SCNAction = ObjCClass('SCNAction')
SCNView = ObjCClass('SCNView')
SCNTransaction = ObjCClass('SCNTransaction')

UIColor = ObjCClass('UIColor')
NSData = ObjCClass('NSData')

# Styling constants
BASE_COLOR = UIColor.colorWithWhite_alpha_(0.18,1.0)
EMISSIVE_COLOR = UIColor.colorWithRed_green_blue_alpha_(0.0,0.8,1.0,1.0)
AMBIENT_COLOR = UIColor.colorWithRed_green_blue_alpha_(0.05,0.1,0.15,1.0)
LIGHT_COLOR = UIColor.colorWithRed_green_blue_alpha_(0.4,0.9,1.0,1.0)

emission_props = []
emission_offset = 0.0

def noise_image(size=64):
    from PIL import Image
    pixels = []
    for _ in range(size*size):
        v = random.randint(80,255)
        pixels.extend((0,v,v))
    img = Image.frombytes('RGB',(size,size),bytes(pixels))
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return ui.Image.from_data(buf.getvalue())

def create_material():
    mat = SCNMaterial.material()
    mat.lightingModelName = 'physicallyBased'
    mat.diffuse().contents = BASE_COLOR
    mat.metalness().contents = 0.8
    mat.roughness().contents = 0.6
    img = noise_image()
    mat.emission().contents = img
    mat.emission().intensity = 1.0
    emission_props.append(mat.emission())
    return mat

def make_ring(radius, segments, skip_prob, seed, thickness, width, height):
    random.seed(seed)
    parent = SCNNode.node()
    mat = create_material()
    seg_angle = 2*math.pi/segments
    for i in range(segments):
        if random.random() < skip_prob:
            continue
        geo = SCNBox.boxWithWidth_height_length_chamferRadius_(width, height, thickness,0.0)
        geo.materials = [mat]
        node = SCNNode.nodeWithGeometry_(geo)
        a = i*seg_angle
        x = radius*math.cos(a)
        z = radius*math.sin(a)
        node.position = (x,0,z)
        node.eulerAngles = (0,a,0)
        parent.addChildNode_(node)
    return parent

def midpoint(v1,v2):
    m = [(v1[i]+v2[i])*0.5 for i in range(3)]
    l = math.sqrt(m[0]*m[0]+m[1]*m[1]+m[2]*m[2])
    return [m[0]/l,m[1]/l,m[2]/l]

def make_geodesic_sphere(radius, freq, thickness):
    t = (1.0 + math.sqrt(5.0)) / 2.0
    verts = [
        (-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0),
        (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t),
        (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)
    ]
    verts = [midpoint((0,0,0),v) for v in verts]
    faces = [
        (0,11,5),(0,5,1),(0,1,7),(0,7,10),(0,10,11),
        (1,5,9),(5,11,4),(11,10,2),(10,7,6),(7,1,8),
        (3,9,4),(3,4,2),(3,2,6),(3,6,8),(3,8,9),
        (4,9,5),(2,4,11),(6,2,10),(8,6,7),(9,8,1)
    ]
    for _ in range(freq):
        new_faces = []
        mid_cache = {}
        def mp(i,j):
            key = tuple(sorted((i,j)))
            if key in mid_cache:
                return mid_cache[key]
            v = midpoint(verts[i], verts[j])
            verts.append(v)
            mid_cache[key] = len(verts)-1
            return mid_cache[key]
        for a,b,c in faces:
            ab = mp(a,b); bc = mp(b,c); ca = mp(c,a)
            new_faces += [(a,ab,ca),(b,bc,ab),(c,ca,bc),(ab,bc,ca)]
        faces = new_faces
    flat_verts = []
    for v in verts:
        flat_verts += [v[0]*radius,v[1]*radius,v[2]*radius]
    import struct
    vdata = struct.pack('f'*len(flat_verts), *flat_verts)
    src = SCNGeometrySource.geometrySourceWithData_semantic_vectorCount_floatComponents_componentsPerVector_bytesPerComponent_dataOffset_dataStride_(
        NSData.dataWithBytes_length_(vdata,len(vdata)), 'vertex', len(verts), True,3,4,0,12)
    indices = [i for f in faces for i in f]
    idata = struct.pack('I'*len(indices), *indices)
    elem = SCNGeometryElement.geometryElementWithData_primitiveType_primitiveCount_bytesPerIndex_(
        NSData.dataWithBytes_length_(idata,len(idata)), 0, len(indices)//3, 4)
    geo = SCNGeometry.geometryWithSources_elements_([src],[elem])
    mat = create_material()
    geo.materials = [mat]
    node = SCNNode.nodeWithGeometry_(geo)
    return node

def make_spoke(length, thickness, tilt_y, tilt_x):
    geo = SCNBox.boxWithWidth_height_length_chamferRadius_(thickness, thickness, length,0)
    mat = create_material()
    geo.materials = [mat]
    node = SCNNode.nodeWithGeometry_(geo)
    node.eulerAngles = (tilt_x, tilt_y, 0)
    return node

def make_light_column(height, radius_top, radius_bottom, color):
    cone = SCNCone.coneWithTopRadius_bottomRadius_height_(radius_top, radius_bottom, height)
    mat = SCNMaterial.material()
    mat.diffuse().contents = color.colorWithAlphaComponent_(0.25)
    mat.lightingModelName = 'constant'
    mat.doubleSided = True
    cone.materials = [mat]
    node = SCNNode.nodeWithGeometry_(cone)
    node.position = (0,height/2.0,0)
    return node

def make_rain_emitter(bounds):
    radius,height = bounds
    ps = SCNParticleSystem.particleSystem()
    ps.birthRate = 250
    ps.particleLifeSpan = 2.5
    ps.particleLifeSpanVariation = 0.5
    ps.particleVelocity = -1.5
    ps.particleVelocityVariation = 0.3
    ps.particleSize = 0.01
    ps.particleColor = LIGHT_COLOR
    ps.particleImage = noise_image(8)
    shape = SCNCylinder.cylinderWithRadius_height_(radius,height)
    ps.emitterShape = shape
    ps.emissionDuration = 0
    ps.loops = True
    return ps

def add_ring_animation(node, axis, speed_rad_s, jitter_deg, wobble_amp_deg=0, wobble_hz=0):
    rot = SCNAction.repeatActionForever_(SCNAction.rotateBy_x_y_z_duration_(axis[0]*speed_rad_s, axis[1]*speed_rad_s, axis[2]*speed_rad_s,1.0))
    node.runAction_(rot)
    if jitter_deg>0:
        j = math.radians(jitter_deg)
        jit = SCNAction.repeatActionForever_(SCNAction.sequence_([
            SCNAction.waitForDuration_(0.5),
            SCNAction.rotateBy_x_y_z_duration_(axis[0]*j, axis[1]*j, axis[2]*j,0.3),
            SCNAction.rotateBy_x_y_z_duration_(-axis[0]*j, -axis[1]*j, -axis[2]*j,0.3)
        ]))
        node.runAction_(jit)
    if wobble_amp_deg>0 and wobble_hz>0:
        w = math.radians(wobble_amp_deg)
        dur = 1.0/ wobble_hz
        wob = SCNAction.repeatActionForever_(SCNAction.sequence_([
            SCNAction.rotateBy_x_y_z_duration_(w,0,0,dur/2),
            SCNAction.rotateBy_x_y_z_duration_(-w,0,0,dur/2)
        ]))
        node.runAction_(wob)

def build_scene():
    scene = SCNScene.scene()
    root = scene.rootNode()

    outer = make_ring(1.0,48,0.2,1,0.05,0.15,0.12)
    middle = make_ring(0.77,40,0.25,2,0.045,0.13,0.1)
    inner = make_ring(0.55,32,0.3,3,0.04,0.1,0.08)
    root.addChildNode_(outer)
    root.addChildNode_(middle)
    root.addChildNode_(inner)

    core = make_geodesic_sphere(0.22,1,0.01)
    root.addChildNode_(core)

    sp1 = make_spoke(2.2,0.05,0.3,0.2)
    sp2 = make_spoke(2.2,0.05,-0.4,-0.1)
    root.addChildNode_(sp1)
    root.addChildNode_(sp2)

    add_ring_animation(outer,(0,1,0),0.07,3)
    add_ring_animation(middle,(1,0,0),-0.09,2)
    add_ring_animation(inner,(0,0,1),0.14,1,1,0.25)
    add_ring_animation(core,(0,1,0),-0.025,0)

    light_col = make_light_column(3.0,0.1,0.5,EMISSIVE_COLOR)
    root.addChildNode_(light_col)

    ps = make_rain_emitter((0.5,3.0))
    root.addParticleSystem_(ps)

    amb = SCNNode.node()
    light = SCNLight.light()
    light.type = 'ambient'
    light.color = AMBIENT_COLOR
    amb.light = light
    root.addChildNode_(amb)

    spot_node = SCNNode.node()
    spot = SCNLight.light()
    spot.type = 'spot'
    spot.color = LIGHT_COLOR
    spot.castsShadow = True
    spot_node.light = spot
    spot_node.position = (0,3,0)
    spot_node.eulerAngles = (-math.pi/2,0,0)
    root.addChildNode_(spot_node)

    camera_node = SCNNode.node()
    camera = SCNCamera.camera()
    camera.fieldOfView = 40
    camera_node.camera = camera
    camera_node.position = (0,0,3.5)
    pivot = SCNNode.node()
    pivot.addChildNode_(camera_node)
    pivot.position = (0,0,0)
    root.addChildNode_(pivot)
    pivot.runAction_(SCNAction.repeatActionForever_(SCNAction.rotateBy_x_y_z_duration_(0,0.02,0,40)))

    scene.cameraNode = camera_node
    scene.cameraPivot = pivot
    return scene

class MainView(ui.View):
    def __init__(self):
        self.flex = 'WH'
        self.scene = build_scene()
        frame = (0,0,self.width,self.height)
        self.scn_view = SCNView.alloc().initWithFrame_options_(frame, None).autorelease()
        self.scn_view.scene = self.scene
        self.scn_view.allowsCameraControl = False
        self.scn_view.backgroundColor = UIColor.blackColor()
        self_obj = ObjCInstance(self)
        self_obj.addSubview_(self.scn_view)
        self.overlay = ui.View(frame=self.bounds)
        self.overlay.flex = 'WH'
        self.overlay.background_color = (0,0,0,0.001)
        self.add_subview(self.overlay)
        self.overlay.touch_enabled = True
        self.overlay.touch_began = self.touch_began
        self.overlay.touch_moved = self.touch_moved
        self.overlay.touch_ended = self.touch_ended
        self.yaw = 0.0
        self.pitch = 0.0
        self.dist = 3.5
        self.last_pt = None
        ui.delay(self.update_emission,0.016)

    def layout(self):
        ObjCInstance(self.scn_view).setFrame_(ObjCInstance(self).bounds())

    def update_camera(self):
        pivot = self.scene.cameraPivot
        camera_node = self.scene.cameraNode
        pivot.eulerAngles = (self.pitch,self.yaw,0)
        camera_node.position = (0,0,self.dist)

    def touch_began(self, touch):
        if touch.tap_count == 2:
            self.yaw = self.pitch = 0.0
            self.dist = 3.5
            self.update_camera()
        self.last_pt = touch.location
        if len(self.overlay.touches) == 2:
            t1,t2 = list(self.overlay.touches.values())
            self.pinch_start = ui.Point(*t1.location).distance(ui.Point(*t2.location))
            self.dist_start = self.dist

    def touch_moved(self, touch):
        if len(self.overlay.touches) == 1:
            pt = touch.location
            dx = pt[0]-self.last_pt[0]
            dy = pt[1]-self.last_pt[1]
            self.yaw += dx*0.01
            self.pitch += dy*0.01
            self.pitch = max(-math.pi/2+0.1, min(math.pi/2-0.1, self.pitch))
            self.last_pt = pt
            self.update_camera()
        elif len(self.overlay.touches) == 2:
            t1,t2 = list(self.overlay.touches.values())
            d = ui.Point(*t1.location).distance(ui.Point(*t2.location))
            scale = d/self.pinch_start if self.pinch_start>0 else 1
            self.dist = max(1.5, min(6.0, self.dist_start/scale))
            self.update_camera()

    def touch_ended(self, touch):
        self.last_pt = None

    def update_emission(self):
        global emission_offset
        emission_offset += 0.002
        for prop in emission_props:
            m = (1,0,0,0, 0,1,emission_offset%1.0,0, 0,0,1,0, 0,0,0,1)
            prop.contentsTransform = m
        ui.delay(self.update_emission,0.016)

def run():
    v = MainView()
    v.present('fullscreen', hide_title_bar=True)

if __name__ == '__main__':
    run()
