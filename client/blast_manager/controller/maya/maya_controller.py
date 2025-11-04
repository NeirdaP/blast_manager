import contextlib
import getpass
import os
import time
import maya.cmds as cmds

from ..base_controller import BaseBlastController, PlayblastError, \
    BlastInfo, MOV, AmbientOcclusionDisplayOption, MotionBlurDisplayOption, AntiAliasingDisplayOption, \
    DepthOfFieldDisplayOption

from . import maya_utils


class MayaAmbientOcclusionDisplayOption(AmbientOcclusionDisplayOption):
    def _store_to_restore(self):
        import maya
        self._to_restore = maya.cmds.getAttr("hardwareRenderingGlobals.ssaoEnable")

    def _apply(self):
        import maya
        maya.cmds.setAttr("hardwareRenderingGlobals.ssaoEnable", self.active)

    def _restore(self):
        import maya
        maya.cmds.setAttr("hardwareRenderingGlobals.ssaoEnable", self._to_restore)


class MayaMotionBlurDisplayOption(MotionBlurDisplayOption):

    def _store_to_restore(self):
        import maya
        self._to_restore = maya.cmds.getAttr("hardwareRenderingGlobals.motionBlurEnable")

    def _apply(self):
        import maya
        v = self.active and 1 or 0
        maya.cmds.setAttr("hardwareRenderingGlobals.motionBlurEnable", v)

    def _restore(self):
        import maya
        maya.cmds.setAttr("hardwareRenderingGlobals.motionBlurEnable", self._to_restore)


class MayaDepthOfFieldDisplayOption(DepthOfFieldDisplayOption):

    def _store_to_restore(self):
        import maya
        self._to_restore = {}
        cam = self._get_camera()
        self._to_restore['cam'] = cam
        self._to_restore['dop'] = maya.cmds.getAttr(cam + '.depthOfField')

    def _apply(self):
        import maya
        cam = self._to_restore['cam']
        v = self.active and 1 or 0
        maya.cmds.setAttr(cam + '.depthOfField', v)

    def _restore(self):
        import maya
        cam = self._to_restore['cam']
        value = self._to_restore['dop']
        maya.cmds.setAttr(cam + '.depthOfField', value)

    @staticmethod
    def _get_camera():
        import maya
        camera = None

        if maya.cmds.about(batch=True):
            for _camera in maya.cmds.ls(cameras=True):
                if int(maya.cmds.getAttr(_camera + '.rnd')):
                    camera = _camera
        else:
            model_panel = maya.cmds.getPanel(wf=True) or []
            if maya.cmds.getPanel(wf=True) not in maya.cmds.getPanel(type='modelPanel'):
                raise PlayblastError("Please select a viewer !")
            camera = maya.cmds.modelPanel(model_panel, q=True, camera=True)

        if not camera:
            raise PlayblastError("Cannot find a valid camera")
        return camera


class MayaAntiAliasingDisplayOption(AntiAliasingDisplayOption):

    def _store_to_restore(self):
        import maya
        self._to_restore = {
            'multiSampleEnable': maya.cmds.getAttr("hardwareRenderingGlobals.multiSampleEnable"),
            'lineAAEnable': maya.cmds.getAttr("hardwareRenderingGlobals.lineAAEnable")
        }

    def _apply(self):
        import maya
        v = self.active and 1 or 0
        maya.cmds.setAttr("hardwareRenderingGlobals.multiSampleEnable", v)
        maya.cmds.setAttr("hardwareRenderingGlobals.lineAAEnable", v)

    def _restore(self):
        import maya
        maya.cmds.setAttr("hardwareRenderingGlobals.multiSampleEnable", self._to_restore['multiSampleEnable'])
        maya.cmds.setAttr("hardwareRenderingGlobals.lineAAEnable", self._to_restore['lineAAEnable'])


class MayaBlastController(BaseBlastController):
    """
    Here is the main manager for running Maya blasts, it must be initialized with default value and scene info.
    The created blast will be stored in the local storage which is specified by local_path.
    You can create an image sequence, a meta file will be created to specify
    the blast sound if one is used and its montage info (start, end, ...)
    https://www.notion.so/supamonks/SupaBlast-Manager-c42d365905fc4655a1c68c77338d00ba
    """

    _DISPLAY_TYPE_TO_MENU_NAME = {
        'NURBSCurves': 'NurbsCurvesItemPB',
        'NURBSSurfaces': 'NurbsSurfacesItemPB',
        'PolyMeshes': 'PolymeshesItemPB',
        'SubdivSurfaces': 'SubdivSurfacesItemPB',
        'Planes': 'PlanesItemPB',
        'Lights': 'LightsItemPB',
        'Cameras': 'CamerasItemPB',
        'Joints': 'JointsItemPB',
        'IKHandles': 'IkHandlesItemPB',
        'Deformers': 'DeformersItemPB',
        'Dynamics': 'DynamicsItemPB',
        'Particle Instancers': 'ParticleInstancersItemPB',
        'Fluids': 'FluidsItemPB',
        'HairSystems': 'HairSystemsItemPB',
        'Follicles': 'FolliclesItemPB',
        'NCloths': 'NClothsItemPB',
        'NParticles': 'NParticlesItemPB',
        'NRigids': 'NRigidsItemPB',
        'DynamicConstraints': 'DynamicConstraintsItemPB',
        'Locators': 'LocatorsItemPB',
        'Dimensions': 'DimensionsItemPB',
        'Pivots': 'PivotsItemPB',
        'Handles': 'HandlesItemPB',
        'Textures': 'TexturesItemPB',
        'Strokes': 'StrokesItemPB',
        'MotionTrails': 'MotionTrailsItemPB',
        'CVs': 'NurbsCVsItemPB',
        'Hulls': 'NurbsHullsItemPB',
        'Grid': 'GridItemPB',
        'HUD': 'HUDItemPB',
        'SelectionHighlighting': 'SelectionItemPB',
    }

    ALL_DISPLAY_OPTION_TYPES = (
        MayaAmbientOcclusionDisplayOption,
        MayaAntiAliasingDisplayOption,
        MayaMotionBlurDisplayOption,
        MayaDepthOfFieldDisplayOption
    )
    ALL_DISPLAY_TYPES = list(_DISPLAY_TYPE_TO_MENU_NAME.keys())

    def __init__(
            self,
            local_path,
            scene_path,
            default_camera,
            third_party_open,
    ):

        """
        Args:
            local_path (str): destination of blast in local machine (mandatory)
            scene_path (str): scene path (mandatory)
            default_camera (str): default camera name
            third_party_open (list[tuple]): Optional list of callbacks to open blasts with third party applications
                the first item of the tuple will be the label of the action, when right-clicking a blast,
                the second item of the tuple the callback executed when clicking on this action,
                with BlastInfo of the blast as argument.
                For example: [("Open in Pd player", pd_player_callback), ("Open in RV", rv_callback)]
        """
        super().__init__(
            local_path,
            scene_path,
            default_camera,
            third_party_open,
        )

        self.play_seq_action = third_party_open

        self.default_camera = default_camera
        self.local_path = local_path
        self.scene_path = os.path.abspath(scene_path)

    @staticmethod
    def _get_maya():
        try:
            import maya.cmds  # @UnusedImport
            import maya
        except ImportError:
            raise PlayblastError("You cannot blast outside of Maya.")
        return maya

    def _get_camera(self):
        maya = self._get_maya()
        camera = None

        if maya.cmds.about(batch=True):
            for _camera in maya.cmds.ls(cameras=True):
                if int(maya.cmds.getAttr(_camera + '.rnd')):
                    camera = _camera
                    break
        else:
            model_panel = self._get_visible_model_panel()
            camera = maya.cmds.modelPanel(model_panel, q=True, camera=True)

        return camera

    def get_default_bg_color(self):
        return "Light Grey"

    def _assert_current_scene(self):
        maya = self._get_maya()
        maya_scene = maya.cmds.file(query=True, sceneName=True)
        if not os.path.basename(maya_scene) == os.path.basename(self.scene_path):
            raise Exception('The current scene is not:\n  %s\nPlease close and reopen the PlayBlast Manager.' %
                            (self.scene_path,))
        return maya_scene

    def get_selected_frame_range(self):
        """
        Not used anymore
        """
        maya = self._get_maya()

        try:
            playback_widget = maya.mel.eval('$tmpVar=$gPlayBackSlider')
        except RuntimeError:
            raise PlayblastError('Could not find maya\'s playback widget.')

        if not maya.cmds.timeControl(playback_widget, rangeVisible=True, query=True):
            # fall back to playback range:
            return self.get_playback_range()

        str_range = maya.cmds.timeControl(playback_widget, range=True, query=True)
        try:
            start, end = [int(i) for i in str_range.strip('"').split(':')]
        except Exception as err:
            raise PlayblastError(str(err))

        return start, end

    def get_global_range(self):
        maya = self._get_maya()

        try:
            s = int(maya.cmds.playbackOptions(q=True, animationStartTime=True))
            e = int(maya.cmds.playbackOptions(q=True, animationEndTime=True))
        except Exception as err:
            raise PlayblastError(str(err))
        return s, e

    def get_playback_range(self):
        maya = self._get_maya()

        try:
            s = int(maya.cmds.playbackOptions(q=True, minTime=True))
            e = int(maya.cmds.playbackOptions(q=True, maxTime=True))
        except Exception as err:
            raise PlayblastError(str(err))
        return s, e

    def get_history(self):
        self._assert_current_scene()
        return BlastInfo.get_history(self.local_path)

    def blast_missing_range(self, blast):
        """
        type must be one of .cmds.MOV / .cmds.SEQ
        :param (BlastInfo) blast:
        """

        maya = self._get_maya()
        cmds = maya.cmds
        path = blast.get_file_path().split('.', 1)[0]  # maya will add the extension

        if blast.use_sequencer:
            blasts = []
            blast.sounds = maya_utils.get_all_audios(blast.start, blast.end)

            for shot in maya.cmds.sequenceManager(listShots=True):
                start = cmds.shot(shot, q=True, sequenceStartTime=True)
                end = cmds.shot(shot, q=True, sequenceEndTime=True)
                if start >= blast.end or end < blast.start:
                    continue
                blast.camera = maya.cmds.shot(shot, q=True, currentCamera=True)

                blasts.append((
                    path, blast.blast_type, maya.cmds.shot(shot, q=True, currentCamera=True),
                    None, start, end,
                    blast.display_types, blast.bg_color,
                    blast.display_options, blast.hud_options,
                    blast.width, blast.height,
                    cmds.shot(shot, q=True, scale=True)
                ))
        else:
            if '*' in blast.sounds:
                blast.sounds = maya_utils.get_all_audios(blast.start, blast.end)
            blasts = [(
                path, blast.blast_type, blast.camera, blast.sounds, blast.start, blast.end, blast.display_types,
                blast.bg_color, blast.display_options,
                blast.hud_options, blast.display_grid, blast.width, blast.height, blast.scale
            )]
        self._make_meta_data_file(blast)
        for blast in blasts:
            self._do_one_blast(*blast)

    def _get_visible_model_panel(self):
        maya = self._get_maya()

        model_panels = maya.cmds.getPanel(type='modelPanel') or []
        if maya.cmds.getPanel(wf=True) in model_panels:
            return maya.cmds.getPanel(wf=True)

        visible_panel = maya.cmds.getPanel(visiblePanels=True) or []
        for panel in model_panels:
            if panel in visible_panel:
                maya.cmds.setFocus(panel)
                return panel
        return None

    def _set_camera(self, camera):
        maya = self._get_maya()

        if camera:
            maya_cameras = (maya.cmds.ls(camera + '*', type='camera') or [])
            if not maya_cameras:
                for cam in maya.cmds.ls(camera):
                    maya_cameras += maya.cmds.listRelatives(cam, children=True, type='camera') or []
            if maya_cameras:
                camera = maya_cameras[0]
            else:
                raise PlayblastError("Cannot find the camera %r" % camera)

        restore_data = {}
        if maya.cmds.about(batch=True):
            if not camera:
                camera = "persp"
            restore_data['cams_state'] = {}
            for _camera in maya.cmds.ls(cameras=True):
                restore_data['cams_state'][_camera] = maya.cmds.getAttr(_camera + '.rnd')
                maya.cmds.setAttr(_camera + '.rnd', 0)
            maya.cmds.setAttr(camera + '.rnd', 1)
        else:
            model_panel = self._get_visible_model_panel()
            if not model_panel:
                raise PlayblastError("Please select a viewer !")
            if camera:
                restore_data['current_camera'] = maya.cmds.modelPanel(model_panel, q=True, camera=True)
                maya.cmds.lookThru(model_panel, camera)

        return restore_data

    def _apply_playblast_display(self, display_types):
        maya = self._get_maya()

        try:
            for display_type, menu_name in self._DISPLAY_TYPE_TO_MENU_NAME.items():
                maya.cmds.optionVar(intValue=('playblastShow%s' % display_type, display_type in display_types))

            for display_type, menu_name in self._DISPLAY_TYPE_TO_MENU_NAME.items():
                maya.mel.eval('updatePlayblastMenus("playblastShow%s", "show%s");' % (display_type, menu_name))
        except RuntimeError as err:
            print("RuntimeError cannot update display: %r" % err)

    def _apply_cam_overrides(self):
        maya = self._get_maya()
        cam = self._get_camera()
        restore_data = dict()

        restore_data["cam"] = cam
        restore_data["cam.displaySafeAction"] = maya.cmds.getAttr(cam + ".displaySafeAction")
        maya.cmds.setAttr(cam + ".displaySafeAction", False)
        cam_overscan = maya.cmds.getAttr(cam + ".overscan")

        restore_data["cam.panZoomEnabled"] = maya.cmds.getAttr(cam + ".panZoomEnabled")
        maya.cmds.setAttr(cam + ".panZoomEnabled", 0)
        if cam_overscan:
            restore_data["cam.overscan"] = cam_overscan
            restore_data["cam.displayResolution"] = maya.cmds.getAttr(cam + ".displayResolution")
            restore_data["cam.horizontalFilmOffset"] = maya.cmds.getAttr(cam + ".horizontalFilmOffset")
            restore_data["cam.verticalFilmOffset"] = maya.cmds.getAttr(cam + ".verticalFilmOffset")
            forced_overscan = 1.0
            maya.cmds.camera(cam, e=True, displayResolution=False, overscan=forced_overscan, horizontalFilmOffset=0,
                             verticalFilmOffset=0)
        return restore_data

    def _apply_display_overrides(self, display_grid=False):
        maya = self._get_maya()
        restore_data = {}

        model_panel = self._get_visible_model_panel()
        if model_panel:
            display_flags = (
                ('activeOnly', 0),
                ('wireframeOnShaded', 0),
                ('headsUpDisplay', 1),
                ('selectionHiliteDisplay', 0),
                ('nurbsCurves', 0),
                ('polymeshes', 1),
                ('lights', 0),
                ('cameras', 0),
                ('grid', display_grid),
                ('hulls', 0),
                ('joints', 0),
                ('ikHandles', 0),
                ('deformers', 0),
                ('fluids', 0),
                ('follicles', 0),
                ('dynamicConstraints', 0),
                ('locators', 0),
                ('manipulators', 0),
                ('dimensions', 0),
                ('handles', 0),
                ('pivots', 0),
            )
            changed_flags = []
            for flag, value in display_flags:
                current_value = maya.cmds.modelEditor(model_panel, q=True, **{flag: True})
                if current_value != value:
                    changed_flags.append((flag, current_value))
                    maya.cmds.modelEditor(model_panel, e=True, **{flag: value})
            restore_data['model_panel'] = model_panel
            restore_data['changed_flags'] = changed_flags
        return restore_data

    def _apply_background_overrides(self, bg_color_name):
        if not bg_color_name:
            return {}
        maya = self._get_maya()
        bg_color = [c / 255.0 for c in self.get_bg_color_options()[bg_color_name]]
        background_params = ["background", "backgroundTop", "backgroundBottom"]

        display_rgb_color = {}

        for param in background_params:
            color = maya.cmds.displayRGBColor(param, query=True)
            if color:
                display_rgb_color[param] = color
            maya.cmds.displayRGBColor(param, *bg_color)

        restore_data = {'displayRGBColor': display_rgb_color}
        return restore_data

    def _clear_hud(self):
        maya = self._get_maya()
        for section in range(0, 9 + 1):
            last_block = maya.cmds.headsUpDisplay(nextFreeBlock=section)
            for block in range(last_block):
                maya.cmds.headsUpDisplay(removePosition=[section, block])

    def display_lower_left_hud(self, display_class, hud_options):
        import maya.cmds
        hud_cb_name = 'smks_hud_ll_cb'
        hud_ll_display_name = 'smks_hud_ll_button'
        shot_id = os.path.basename(self.local_path)
        dt = time.strftime(time.strftime('%Y-%m-%d'))

        def hud_update_ll(hbt=hud_ll_display_name, _shot_id=shot_id, _dt=dt):
            maya.cmds.currentTime(query=True)
            label = '%s - %s' % (_shot_id, _dt)
            display_class(hbt, e=True, l=label)

        maya.cmds.headsUpDisplay(
            hud_cb_name,
            label='',
            section=5,
            block=1,
            blockSize=hud_options.get('blockSize', 'large'),
            labelFontSize=hud_options.get('labelFontSize', 'large'),
            command=hud_update_ll,
        )

        display_class(
            hud_ll_display_name,
            section=5,
            block=0,
            visible=True,
            label='',
            buttonWidth=400,
            blockSize=hud_options.get('blockSize', 'large'),
            labelFontSize=hud_options.get('labelFontSize', 'large')
        )

    def display_lower_right_hud(self, display_class, hud_options, start, end):
        import maya.cmds

        hud_cb_name = 'smks_hud_lr_cb'
        hud_lr_display_name = 'smks_hud_lr_button'
        m_first, m_last = self.get_montage_range()
        b_first, b_last = start, end
        if (m_first, m_last) != (b_first, b_last):
            range_lb = '[%04i->%04i] [!!! %04i->%04i !!!]' % (
                b_first, b_last, m_first, m_last
            )
            bw = 500
        else:
            range_lb = '[%04i->%04i]' % (m_first, m_last)
            bw = 300
        user = getpass.getuser().upper()

        def hud_update_lr(hbt=hud_lr_display_name, _range_lb=range_lb, _user=user):
            curr = maya.cmds.currentTime(query=True)
            label = '%s - %04i %s' % (_user, curr, _range_lb)
            display_class(hbt, e=True, l=label)

        maya.cmds.headsUpDisplay(
            hud_cb_name, label='',
            section=9,
            block=1,
            blockSize=hud_options.get('blockSize', 'large'),
            labelFontSize=hud_options.get('labelFontSize', 'large'),
            command=hud_update_lr,
            attachToRefresh=True,
        )

        display_class(
            hud_lr_display_name,
            section=9,
            block=0,
            visible=True,
            label='',
            buttonWidth=bw,
            blockSize=hud_options.get('blockSize', 'large'),
            labelFontSize=hud_options.get('labelFontSize', 'large')
        )

    @staticmethod
    def display_upper_right_hud(display_class, hud_options, camera):
        import maya.cmds

        hud_cb_name = 'smks_hud_tr_cb'
        hud_lr_display_name = 'smks_hud_tr_button'
        bw = 300

        def hud_update_lr(hbt=hud_lr_display_name, _camera=camera):
            focal = maya.cmds.getAttr(_camera + ".focalLength")
            display_class(hbt, e=True, l="Camera: %s  (foc: %.02f)" % (_camera, focal))

        maya.cmds.headsUpDisplay(
            hud_cb_name, label='',
            section=4,
            block=1,
            blockSize=hud_options.get('blockSize', 'large'),
            labelFontSize=hud_options.get('labelFontSize', 'large'),
            command=hud_update_lr,
            attachToRefresh=True,
        )

        display_class(
            hud_lr_display_name,
            section=4,
            block=0,
            visible=True,
            label='',
            buttonWidth=bw,
            blockSize=hud_options.get('blockSize', 'large'),
            labelFontSize=hud_options.get('labelFontSize', 'large')
        )

    def _add_playblast_hud(self, camera, start, end, hud_options):
        maya = self._get_maya()
        self._clear_hud()

        restore_data = {}

        if hud_options.get('text_background'):
            display_class = maya.cmds.hudButton
            color_index = maya.cmds.displayColor('headsUpDisplayButtons', q=True, dormant=True)
            restore_data['text_background'] = maya.cmds.colorIndex(color_index, q=True)
            maya.cmds.colorIndex(color_index, *hud_options.get('text_background'))
            try:
                maya.cmds.displayColor('headsUpDisplayButtons', int(color_index))
            except RuntimeError:
                pass  # I don't know why but Maya say 'headsUpDisplayLabels' is an unknown display color name
        else:
            def headsUpDisplay(name, **kwargs):
                if 'buttonWidth' in kwargs:
                    del kwargs['buttonWidth']
                return maya.cmds.headsUpDisplay(name, **kwargs)

            display_class = headsUpDisplay

        if hud_options.get('text_color'):
            color_index = maya.cmds.displayColor('headsUpDisplayLabels', q=True, dormant=True)
            restore_data['text_color'] = maya.cmds.colorIndex(color_index, q=True)
            maya.cmds.colorIndex(color_index, *hud_options.get('text_color'))
            try:
                maya.cmds.displayColor('headsUpDisplayLabels', int(color_index))
            except RuntimeError:
                pass  # I don't know why but Maya say 'headsUpDisplayLabels' is an unknown display color name

        self.display_lower_left_hud(display_class, hud_options)
        self.display_lower_right_hud(display_class, hud_options, start, end)
        self.display_upper_right_hud(display_class, hud_options, camera)

        return restore_data

    def _restore_camera(self, restore_data):
        maya = self._get_maya()

        if maya.cmds.about(batch=True):
            cams_state = restore_data.get('cams_state', {})
            for _camera, value in cams_state.items():
                maya.cmds.setAttr(_camera + '.rnd', value)
        else:
            model_panel = self._get_visible_model_panel()
            current_camera = restore_data.get('current_camera')
            if current_camera:
                maya.cmds.lookThru(model_panel, current_camera)

    def _restore_cam_overrides(self, restore_data):
        maya = self._get_maya()
        cam = restore_data.get('cam')

        if cam:
            panZoomEnabled = restore_data.get('cam.panZoomEnabled')
            if panZoomEnabled is not None:
                maya.cmds.setAttr(cam + '.panZoomEnabled', panZoomEnabled)

            overscan = restore_data.get('cam.overscan')
            if overscan is not None:
                maya.cmds.camera(cam, e=True, overscan=overscan)

            displayResolution = restore_data.get('cam.displayResolution')
            if displayResolution is not None:
                maya.cmds.camera(cam, e=True, displayResolution=displayResolution)

            horizontalFilmOffset = restore_data.get('cam.horizontalFilmOffset')
            if horizontalFilmOffset is not None:
                maya.cmds.camera(cam, e=True, horizontalFilmOffset=horizontalFilmOffset)

            verticalFilmOffset = restore_data.get('cam.verticalFilmOffset')
            if verticalFilmOffset is not None:
                maya.cmds.camera(cam, e=True, verticalFilmOffset=verticalFilmOffset)

    def _restore_display_overrides(self, restore_data):
        model_panel = restore_data.get('model_panel')
        if not model_panel:
            return
        maya = self._get_maya()

        changed_flags = restore_data.get('changed_flags', [])
        for flag, value in changed_flags:
            maya.cmds.modelEditor(model_panel, e=True, **{flag: value})

    def _restore_background_overrides(self, restore_data):
        maya = self._get_maya()

        displayRGBColor = restore_data.get('displayRGBColor')
        if displayRGBColor:
            for param, value in displayRGBColor.items():
                maya.cmds.displayRGBColor(param, *value)

    def _restore_hud_overrides(self, restore_data):
        maya = self._get_maya()

        text_color = restore_data.get('text_color')
        if text_color:
            color_index = maya.cmds.displayColor('headsUpDisplayLabels', q=True, dormant=True)
            maya.cmds.colorIndex(color_index, *text_color)
            try:
                maya.cmds.displayColor('headsUpDisplayLabels', int(color_index))
            except RuntimeError:
                pass  # I don't know why but Maya say 'headsUpDisplayLabels' is an unknown display color name

        text_background = restore_data.get('text_background')
        if text_background:
            color_index = maya.cmds.displayColor('headsUpDisplayButtons', q=True, dormant=True)
            maya.cmds.colorIndex(color_index, *text_background)
            try:
                maya.cmds.displayColor('headsUpDisplayButtons', int(color_index))
            except RuntimeError:
                pass  # I don't know why but Maya say 'headsUpDisplayLabels' is an unknown display color name

    @contextlib.contextmanager
    def _blast_context(self, cam, start, end, display_types,
                       bg_color, display_options, hud_options, display_grid):
        maya = self._get_maya()
        is_gui = not maya.cmds.about(batch=True)
        cam = cam or self.default_camera

        restore_data = self._set_camera(cam)

        maya.cmds.optionVar(intValue=('playblastOverrideViewport', True))
        self._apply_playblast_display(display_types)
        restore_data.update(self._apply_cam_overrides())
        restore_data.update(self._apply_display_overrides(display_grid=display_grid))

        if is_gui and hud_options is not None:
            restore_data.update(self._add_playblast_hud(cam, start, end, hud_options))
            maya.mel.eval('updatePlayblastMenus("playblastOverrideViewport","overrideViewportItemPB");')

        image_format = maya.cmds.getAttr('defaultRenderGlobals.imageFormat')
        maya.cmds.setAttr('defaultRenderGlobals.imageFormat', 32)

        restore_data.update(self._apply_background_overrides(bg_color))
        display_options_instances = self._apply_playblast_display_options(display_options)

        try:
            yield
        except Exception:
            raise
        finally:
            self._restore_display_options(display_options_instances)
            self._restore_background_overrides(restore_data)

            maya.cmds.setAttr('defaultRenderGlobals.imageFormat', image_format)

            if is_gui:
                maya.mel.eval('updatePlayblastMenus("playblastOverrideViewport","overrideViewportItemPB");')
                self._clear_hud()
                self._restore_hud_overrides(restore_data)

            self._restore_display_overrides(restore_data)
            self._restore_cam_overrides(restore_data)
            maya.cmds.optionVar(intValue=('playblastOverrideViewport', False))

            self._restore_camera(restore_data)

    def eval_camera_focal(self, camera, frame):
        maya = self._get_maya()

        attribute = "%s.focalLength" % camera
        connection = maya.cmds.listConnections(attribute, s=True, d=False, plugs=True)
        while connection:
            connections = maya.cmds.listConnections(connection[0].split('.output')[0], s=True, d=False,
                                                    plugs=True) or []
            connection = [c for c in connections if 'FOV' in c or 'focal' in c]
            if connection:
                attribute = connection[0]
                break
            connection = connections
        focal = maya.cmds.keyframe(attribute, q=True, eval=True, time=(frame, frame))

        if not focal:
            focal = maya.cmds.getAttr(attribute)
        else:
            focal = focal[0]
        return focal

    @staticmethod
    def _apply_playblast_display_options(display_options):
        display_options_instances = []
        for display_option_type_name, active in display_options:
            display_option = eval(display_option_type_name + '()')
            display_option.set_active(active)
            display_options_instances.append(display_option)
            display_option.apply()

        return display_options_instances

    def _make_meta_data_file(self, blast):
        import shutil
        from json import dump

        maya = self._get_maya()

        frame_count = (blast.end - blast.start + 1)
        focal = maya.cmds.getAttr(blast.camera + ".focalLength")
        frame_data = dict()

        for frame in range(blast.start, blast.end + 1):
            frame_data[frame] = dict(frame=frame)

        for shot in (maya.cmds.sequenceManager(listShots=True) or []):
            start = int(maya.cmds.shot(shot, q=True, sequenceStartTime=True))
            end = int(maya.cmds.shot(shot, q=True, sequenceEndTime=True))
            camera = maya.cmds.ls(maya.cmds.shot(shot, q=True, currentCamera=True), cameras=True)

            for frame in range(start, end + 1):
                if camera and frame in frame_data:
                    frame_data[frame]['camera'] = camera[0]
                    frame_data[frame]['camera_focal'] = self.eval_camera_focal(camera[0], frame)

        meta_data = {
            "frame_rate": self.get_frame_rate(),
            "frame_data": frame_data,
            "camera": blast.camera,
            "scene": blast.scene_path,
            "camera_focal": focal,
            "frame_count": frame_count,
            "user": getpass.getuser().lower(),
        }
        meta_file = blast.seq_meta_file_path()
        directory = os.path.dirname(meta_file)
        try:
            os.makedirs(directory)
        except OSError:
            pass
        if blast.sounds:
            meta_data["sounds"] = []
            blast.sounds_files = []
            for sound in blast.sounds:
                try:
                    sound_file = maya.cmds.sound(sound, q=True, file=True)
                except Exception as e:
                    print("Cannot load sound %s: %s" % (sound, e))
                    continue
                filename = os.path.basename(sound_file)
                if not os.path.exists(sound_file):
                    if not maya.cmds.about(batch=True):
                        maya.cmds.confirmDialog(title='Sound', message="Cannot find %r !" % sound_file, button=['Ok'],
                                                defaultButton='Ok', dismissString='Ok')
                else:
                    dest_sound_file = os.path.join(directory, filename)
                    shutil.copyfile(sound_file, dest_sound_file)
                    source_start = maya.cmds.sound(sound, q=True, sourceStart=True)
                    source_end = maya.cmds.sound(sound, q=True, sourceEnd=True)
                    offset = maya.cmds.sound(sound, q=True, offset=True) - blast.start - source_start
                    meta_data["sounds"].append({
                        "filename": filename,
                        "offset": offset,
                        "source_start": source_start,
                        "source_end": source_end
                    })
                    blast.sounds_files.append(dest_sound_file)
        with open(meta_file, 'w') as fp:
            dump(meta_data, fp)
        blast.meta_file = meta_file
        blast.write_info(True)
        return meta_file

    def _do_one_blast(self, path, blast_type, camera, sounds, start, end, display_types, bg_color,
                      display_options, hud_options, display_grid, width, height, scale):
        maya = self._get_maya()

        with self._blast_context(camera, start, end, display_types, bg_color,
                                 display_options, hud_options, display_grid):
            blast_dir, filename = os.path.split(path)
            filename = filename.split('.')[0]

            if not os.path.exists(blast_dir):
                os.makedirs(blast_dir)

            if blast_type == MOV:
                blast_format = "qt"
                compression = 'H.264'
            else:
                blast_format = "image"
                compression = "jpg"

            maya.cmds.playblast(
                startTime=start,
                endTime=end,
                format=blast_format,
                filename=os.path.join(blast_dir, filename),
                sequenceTime=0,
                clearCache=1,
                viewer=0,
                sound=sounds[0] if sounds else None,
                showOrnaments=1,
                offScreen=True,
                fp=4,
                percent=100.0 * scale,
                compression=compression,
                quality=100,
                w=width,
                h=height,
            )

    def do_blast(self, blast_type, blast):
        """
        :param blast_type: must be one of .cmds.MOV / .cmds.SEQ
        :param (BlastInfo) blast: object that contain all the UI setting parameters
        """
        maya = self._get_maya()
        cmds = maya.cmds
        path = blast.get_file_path()
        path, extension = os.path.splitext(path)
        print(f"{path=}")

        if blast.use_sequencer:
            blasts = []
            blast.sounds = maya_utils.get_all_audios(blast.start, blast.end)

            for shot in maya.cmds.sequenceManager(listShots=True):
                start = cmds.shot(shot, q=True, sequenceStartTime=True)
                end = cmds.shot(shot, q=True, sequenceEndTime=True)
                if start >= blast.end or end < blast.start:
                    continue
                blast.camera = maya.cmds.shot(shot, q=True, currentCamera=True)

                blasts.append((
                    path, blast_type, maya.cmds.shot(shot, q=True, currentCamera=True),
                    None, start, end,
                    blast.display_types, blast.bg_color,
                    blast.display_options, blast.hud_options, blast.display_grid,
                    blast.width, blast.height,
                    cmds.shot(shot, q=True, scale=True)
                ))
        else:
            if '*' in blast.sounds:
                blast.sounds = maya_utils.get_all_audios(blast.start, blast.end)
            blasts = [(
                path, blast_type, blast.camera, blast.sounds, blast.start, blast.end, blast.display_types,
                blast.bg_color, blast.display_options,
                blast.hud_options, blast.display_grid, blast.width, blast.height, blast.scale
            )]

        self._make_meta_data_file(blast)
        for blast in blasts:
            self._do_one_blast(*blast)

    def get_bg_color_options(self):
        return {
            "Red": (255, 0, 0),
            "Green": (0, 255, 0),
            "Blue": (0, 0, 255),
            "Black": (0, 0, 0),
            "Dark Grey": (100, 100, 100),
            "Light Grey": (150, 150, 150),
            "White": (255, 255, 255)
        }

    def get_scene_frame_range(self):
        first = min(
            cmds.playbackOptions(q=True, min=True), cmds.playbackOptions(q=True, ast=True)
        )
        last = max(
            cmds.playbackOptions(q=True, max=True), cmds.playbackOptions(q=True, aet=True)
        )
        return int(first), int(last)

    def get_render_size(self):
        maya = self._get_maya()
        w = maya.cmds.getAttr('defaultResolution.width')
        h = maya.cmds.getAttr('defaultResolution.height')
        return int(w), int(h)

    def get_default_camera(self):
        return self.default_camera

    def get_available_cameras(self):
        try:
            maya = self._get_maya()
        except PlayblastError:
            return [self.default_camera]
        maya_cameras = maya.cmds.ls(cameras=True)
        return maya.cmds.listRelatives(maya_cameras, parent=True)

    def sequencer_is_available(self):
        try:
            maya = self._get_maya()
        except PlayblastError:
            return True
        return bool(maya.cmds.sequenceManager(listShots=True))

    def get_default_audio(self):
        return "*"

    def get_current_audio(self):
        try:
            maya = self._get_maya()
        except PlayblastError:
            return []

        import maya.mel
        aPlayBackSliderPython = maya.mel.eval('$tmpVar=$gPlayBackSlider')
        return maya.cmds.timeControl(aPlayBackSliderPython, sound=True, query=True)

    def get_available_audios(self):
        try:
            maya = self._get_maya()
        except PlayblastError:
            return []
        return maya.cmds.ls(type='audio')

    def save_file(self):
        maya = self._get_maya()
        maya.cmds.file(save=True)

    def get_display_configs(self):
        return {"Meshes Only": ("NURBSSurfaces", "PolyMeshes", "HUD"),
                "Meshes & Texture": ("NURBSSurfaces", "PolyMeshes", "Textures", "HUD"),
                "Meshes & Hairs": ("NURBSSurfaces", "PolyMeshes", "Cameras", "HairSystems", "HUD"),
                "Meshes & Controllers": ("NURBSSurfaces", "PolyMeshes", "Cameras",
                                         "Handles", "NURBSCurves", "Deformers", "HUD"),
                "Meshes & Dynamics": ("NURBSSurfaces", "PolyMeshes", "Dynamics", "Particle Instancers", "HUD"),
                "Manja": ("NURBSSurfaces", "PolyMeshes", "Cameras", "Fluids", "NParticles", "HUD"),
                "All": self.ALL_DISPLAY_TYPES
                }

    def get_frame_rate(self):
        return maya_utils.get_frame_rate()


def get_maya_main_window(on_fail_message=""):
    from qtpy import QtWidgets

    try:
        from shiboken import wrapInstance  # @UnresolvedImport
    except ImportError:
        from shiboken2 import wrapInstance
    import maya.OpenMayaUI  # @UnresolvedImport

    mw = None
    ptr = maya.OpenMayaUI.MQtUtil.mainWindow()
    if ptr is not None:
        try:
            mw = wrapInstance(long(ptr), QtWidgets.QMainWindow)
        except NameError:
            mw = wrapInstance(int(ptr), QtWidgets.QMainWindow)
    if not mw:
        raise RuntimeError(f"Could not find the Main Window. {on_fail_message}")
    return mw
