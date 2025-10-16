import os

ALEMBIC_GROUP_NAME = "Alembics"
ALEMBIC_MERGE_NAME = "Alembics_Merge"
FBX_GROUP_NAME = "FBXs"

try:
    import hou
except ImportError as e:
    print(
        "Cannot import hou ! You should use this module in Houdini"
    )
    hou = None


def save_file(file_path, save_to_recent_files=False):

    """
    Saves the Houdini scene to the given path, if file_path is None, saves to the current path
    :param str file_path: Location where to save the path
    :param bool save_to_recent_files: if set to True, will add the file to the open recent menu in Houdini
    """

    hou.hipFile.save(file_path, save_to_recent_files)


def new_scene():
    """
    Creates a new empty houdini scene
    """
    hou.hipFile.clear()


def open_file(file_path):
    """
    Opens the given houdini scene file path
    :param str file_path: houdini scene file path
    """
    print("Opening scene {}".format(file_path))
    hou.hipFile.load(file_path)


def import_alembic(alembic_path, name=None, obj_node=None, scale=1.0):
    """
    Imports given alembic in Houdini
    This will be a single mesh, if you want to have the whole hierarchy with all the meshes, use import_alembic_archive
    Camera alembics are not supported by this method, use import_alembic_archive instead
    :param str alembic_path: alembic path
    :param str name: name of the node
    :param hou.ObjNode obj_node: object node that will contain the alembic
    :param float scale: scale of the imported alembic
    :return: transform node connected to the alembic
    :rtype: hou.SopNode
    """

    if not name:
        name = os.path.splitext(os.path.basename(alembic_path))[0]
    if not obj_node:
        obj_node = create_obj_node(name)

    if file_size(alembic_path) == 0:
        print(f"abc {alembic_path} is empty")

    abc_node = obj_node.createNode("alembic", name)
    abc_node.parm("fileName").set(alembic_path)

    transform_node = obj_node.createNode("xform", f"_{name}")
    transform_node.parm("scale").set(scale)
    transform_node.setInput(0, abc_node)

    return transform_node


def import_alembic_archive(alembic_path, name=None, obj_node=None):
    """
    Imports given alembic in Houdini as an alembic archive
    This will import all the hierarchy of meshes
    :param str alembic_path: alembic path
    :param str name: name of the alembic archive
    :param hou.ObjNode obj_node: object node that will contain the alembic
    :return: created alembic archive node
    :rtype: hou.ObjNode
    """

    if not obj_node:
        obj_node = hou.node("/obj")
    if not name:
        name = os.path.splitext(os.path.basename(alembic_path))[0]
    alembic_archive = obj_node.createNode('alembicarchive', name)
    parameter = alembic_archive.parm('fileName')
    parameter.set(alembic_path)
    alembic_archive.parm('buildHierarchy').pressButton()
    return alembic_archive


def import_fbx(fbx_path, name=None):
    """
    Imports given alembic in Houdini
    :param str fbx_path: path of the fbx to import in Houdini
    :param str name: name of the created node
    :return: created object node
    :rtype: hou.ObjNode
    """
    fbx_node = hou.hipFile.importFBX(fbx_path)[0]
    if not fbx_node:
        print(f"fbx {fbx_path} is empty, skipping fbx import")
        return
    if not name:
        name = os.path.basename(fbx_path)
    fbx_node.setName(name)
    # arrange nodes so they are not all on top of each other
    fbx_node.layoutChildren()

    return fbx_node


def create_obj_node(name, color=(1, 1, 1)):
    """
    Creates a geo node with the given name and color
    :param str name: name of the created node
    :param tuple(float, float, float) color: color of the created node
    :return: created geo node
    :rtype: hou.ObjNode
    """

    obj_node = hou.node("/obj/").createNode("geo", name)
    obj_node.setColor(hou.Color(color))
    obj_node.setDisplayFlag(True)

    return obj_node


def create_subnet_node(name=None, color=(1, 1, 1)):
    """
    Creates a subnet node with the given name and color
    :param str name: name of the created node
    :param color: color of the created node
    :return: created subnet node
    :rtype: hou.ObjNode subnet
    """

    subnet_node = hou.node("/obj").createNode("subnet", name)
    return subnet_node


def arrange_layout(node=None):
    """
    Arrange layout inside the given node
    :param hou.ObjNode node: node to arrange layout
    """
    if not node:
        node = hou.node("/obj")

    node.layoutChildren()


def parent(nodes, destination_node):
    """
    Parents nodes to the given parent node
    Beware, certain node types are not compatible with each other for parenting
    :param list[hou.Node] nodes: list of nodes to be parented
    :param hou.Node destination_node: parent node
    """

    hou.moveNodesTo(nodes, destination_node)


def set_frame_range(start_frame, end_frame):
    """
    Set the frame range with given start and end frames
    :param int start_frame: starting frame of timeline
    :param int end_frame: ending frame of timeline
    :return:
    """

    hou.playbar.setFrameRange(start_frame, end_frame)
    hou.playbar.setPlaybackRange(start_frame, end_frame)
    hou.setFrame(start_frame)


def get_playback_range():
    """
    Gets the playback range of the current scene
    :return: frame range (first_frame, last_frame)
    :rtype: tuple(int, int)
    """
    return hou.playbar.playbackRange()


def get_frame_range():
    """
    Gets the global frame range of the current scene
    :return: frame range (first_frame, last_frame)
    :rtype: tuple(int, int)
    """

    return hou.playbar.frameRange()


def get_frame_rate():
    """
    Gets the current frame rate
    :return: frame rate
    :rtype: float
    """

    return hou.fps()


def get_viewport_lighting_mode():
    """
    Gets the current lighting mode used in viewports
    :return: current lighting mode
    :rtype: hou.viewportLighting
    """

    return get_viewport_settings().lighting()


def set_viewport_lighting_mode(mode):
    """
    Sets the lighting mode used in viewports
    :param hou.viewportLighting mode: lighting mode
    """

    get_viewport_settings().setLighting(mode)


def set_viewport_normal_lighting():
    """
    Sets the viewports lighting mode to Normal Lighting
    """
    set_viewport_lighting_mode(hou.viewportLighting.Normal)


def set_viewport_high_quality_lighting():
    """
    Sets the viewports lighting mode to High Quality Lighting
    """
    set_viewport_lighting_mode(hou.viewportLighting.HighQuality)


def set_display_ortho_grid(value):
    """
    Sets the display of the grid, enabled if True, disabled if False
    :param bool value: True or False
    """

    get_viewport_settings().setDisplayOrthoGrid(value)


def get_display_ortho_grid():
    """
    Gets the current display value of orto grids, False if disabled, True if enabled
    :return: True or False
    :rtype: bool
    """
    return get_viewport_settings().displayOrthoGrid()


def set_display_reference_plane(value):
    """
    Sets the value of the display for reference plane (The grid in the perspective view)
    Enabled if True, disabled if False
    :param bool value: True or False
    """
    scene = get_scene()
    reference_plane = scene.referencePlane()
    reference_plane.setIsVisible(value)


def get_display_reference_plane():
    """
    Gets the value of the display for reference plane (The grid in the perspective view)
    False if disabled, True if enabled
    :param value: True or False
    :rtype: bool
    """

    scene = get_scene()
    reference_plane = scene.referencePlane()
    return reference_plane.isVisible()


def get_ambient_occlusion():
    """
    Gets the ambient occlusion value of the current viewport
    :return: ambient occlusion
    :rtype: bool
    """

    return get_viewport_settings().ambientOcclusion()


def set_ambient_occlusion(value):
    """
    Sets the ambient occlusion for the current viewport
    WARNING: ambient occlusion is only visible when viewport's lighting mode is High Quality or above
    see set_viewport_high_quality_lighting()
    :param bool value: True or False
    """
    get_viewport_settings().setAmbientOcclusion(value)


def get_depth_of_field():
    """
    Gets the depth of field from viewport settings
    :return: True or False
    :rtype: bool
    """
    return get_viewport_settings().getDepthOfField()


def set_depth_of_field(value):
    """
    Sets the depth of field of viewport settings
    WARNING: Depth of field also requires the viewport look through a camera with a non-zero fstop
    :param bool value: True or False
    """
    return get_viewport_settings().setDepthOfField(value)


def get_anti_aliasing():
    """
    Gets the anti aliasing level of the viewport
    :return: anti alising level
    :rtype: int
    """
    return get_viewport_settings().sceneAntialias()


def set_anti_aliasing(level):
    """
    Sets the anti aliasing of the viewport to the given level
    Available levels: 1, 2, 4, 8, 16, 32, 64, or 128, the higher being the most defined.
    :param int level: level of anti aliasing
    """
    return get_viewport_settings().setSceneAntialias(level)


def get_current_viewport():
    """
    Gets the current viewport object
    :return: current viewport object
    :rtype: hou.GeometryViewport
    """
    cur_desktop = hou.ui.curDesktop()
    scene_viewer = hou.paneTabType.SceneViewer
    scene = cur_desktop.paneTabOfType(scene_viewer)
    return scene.curViewport()


def get_scene():
    """
    Gets the scene object
    :return: scene object
    :rtype: hou.paneTabType.SceneViewer
    """

    cur_desktop = hou.ui.curDesktop()
    scene_viewer = hou.paneTabType.SceneViewer
    return cur_desktop.paneTabOfType(scene_viewer)


def get_viewport_settings():
    current_viewport = get_current_viewport()
    return current_viewport.settings()


def get_flipbook_settings():
    """
    Gets the flipbook settings object of the current scene
    :return: flipbook settings object
    :rtype: hou.FlipbookSettings
    """

    scene = get_scene()

    return scene.flipbookSettings()


def get_flipbook_resolution():
    """
    Gets the current resolution of flipbook settings
    :return: resolution (width, height)
    :rtype: tuple(int, int)
    """

    return get_flipbook_settings().resolution()


def get_flipbook_motion_blur():
    """
    Gets if the motion blur is enabled in flipbook settings
    :return: True or False
    :rtype: bool
    """
    return get_flipbook_settings().useMotionBlur()


def set_flipbook_motion_blur(value):
    """
    Sets the motion blur with the given value in flipbook settings
    :param bool value: True or False (True enables, False disables)
    """
    get_flipbook_settings().useMotionBlur(value)


def merge_nodes(node_list, merge_node=None, name=None):
    """
    Connect all given nodes in a merge node
    All objects need to be under the same object
    :param list[hou.SopNode] node_list: list of nodes that will be connected to a merge node
    :param hou.SopNode merge_node: merge node
    :param str name: name of the created merge node
    :return: created merge node
    :rtype: hou.SopNode
    """

    if not merge_node:
        obj_node = node_list[0].parent()
        merge_node = obj_node.createNode("merge", name)

    for i, node in enumerate(node_list):
        merge_node.setInput(i, node)


def disable_all_display():
    """
    Function to disable display on all nodes
    This will make viewport empty and reduce launch time drastically
    """

    nodes = hou.node("/obj").children()

    for node in nodes:
        node.setDisplayFlag(False)


def get_node(name):
    """
    Gets the node in the houdini scene from the given name
    :param str name: houdini node name
    :return: houdini node
    :rtype: hou.Node
    """
    nodes = hou.node("/obj").allNodes()

    for node in nodes:
        if node.name() == name:
            return node


def set_frame_rate(frame_rate):
    """
    Sets the frame rate of the current frame
    :param int frame_rate: frame rate
    """

    hou.setFps(frame_rate)


def set_viewport_cam(cam_name):
    """
    Sets the camera of the current viewport
    :param cam_name: name of the camera node
    """
    cam_node = get_node(cam_name)
    viewport = get_current_viewport()
    viewport.setCamera(cam_node)


def get_viewport_cam():
    return get_current_viewport().camera()


def get_alembic_group():
    """
    Finds the alembic group node, or creates it if does not exist
    :return: alembic group node
    :rtype: hou.ObjNode
    """
    node = get_node(ALEMBIC_GROUP_NAME)
    if not node:
        node = create_obj_node(ALEMBIC_GROUP_NAME)

    return node


def get_fbx_group():
    """
    Finds the fbx group node, or creates it if does not exist
    :return: fbx group subnet node
    :rtype: hou.ObjNode subnet
    """

    node = get_node(FBX_GROUP_NAME)
    if not node:
        node = create_subnet_node(FBX_GROUP_NAME)

    return node


def get_alembic_merge_node():
    """
    Finds the alembic merge node, or creates it if does not exist
    :return: merge node
    :rtype: hou.SopNode merge
    """
    alembic_group = get_alembic_group()
    node = get_node(ALEMBIC_MERGE_NAME)
    if not node:
        node = alembic_group.createNode("merge", ALEMBIC_MERGE_NAME)

    return node


def get_all_camera_nodes():
    root = hou.node('/')
    return root.recursiveGlob('*', hou.nodeTypeFilter.ObjCamera)


def get_main_window():
    """
    Gets the Qt main window of houdini
    :return: houdini main window
    :rtype: QWidget
    """
    return hou.qt.mainWindow()


def file_size(path):
    """
    http://stackoverflow.com/a/39501288/1709587
    return size in bytes
    """

    import os
    import platform

    if not os.path.exists(path):
        return 0
    if platform.system() == 'Windows':
        return os.path.getsize(path)
    else:
        stat = os.stat(path)
        return stat.st_size