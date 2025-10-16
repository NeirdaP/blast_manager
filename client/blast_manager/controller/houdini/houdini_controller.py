import contextlib
import os

from . import houdini_utils
from .. base_controller import (
    BaseBlastController, PlayblastError, BlastInfo, AmbientOcclusionDisplayOption,
    MotionBlurDisplayOption, AntiAliasingDisplayOption, DepthOfFieldDisplayOption
)


class HoudiniAmbientOcclusionDisplayOption(AmbientOcclusionDisplayOption):

    def _store_to_restore(self):
        self._to_restore = {"ambient_occlusion": houdini_utils.get_ambient_occlusion(),
                            "lighting_mode": houdini_utils.get_viewport_lighting_mode()}

    def _apply(self):
        houdini_utils.set_ambient_occlusion(self.active)
        if self.active:
            houdini_utils.set_viewport_high_quality_lighting()

    def _restore(self):
        houdini_utils.set_ambient_occlusion(self._to_restore["ambient_occlusion"])
        houdini_utils.set_viewport_lighting_mode(self._to_restore["lighting_mode"])


class HoudiniMotionBlurDisplayOption(MotionBlurDisplayOption):

    def _store_to_restore(self):
        self._to_restore = houdini_utils.get_flipbook_motion_blur()

    def _apply(self):
        houdini_utils.set_flipbook_motion_blur(self.active)

    def _restore(self):
        houdini_utils.set_flipbook_motion_blur(self._to_restore)


class HoudiniDepthOfFieldDisplayOption(DepthOfFieldDisplayOption):

    def _store_to_restore(self):
        self._to_restore = houdini_utils.get_depth_of_field()

    def _apply(self):
        houdini_utils.set_depth_of_field(self.active)

    def _restore(self):
        houdini_utils.set_depth_of_field(self._to_restore)


class HoudiniAntiAliasingDisplayOption(AntiAliasingDisplayOption):

    def _store_to_restore(self):
        self._to_restore = houdini_utils.get_anti_aliasing()

    def _apply(self):
        if self.active:
            houdini_utils.set_anti_aliasing(32)

    def _restore(self):
        houdini_utils.set_anti_aliasing(self._to_restore)


class HoudiniBlastManager(BaseBlastController):
    """
    Here is the main manager for running Houdini blasts (called flipbooks in Houdini),
    it must be initialized with default value and scene info.
    The created blast will be stored in the local storage which is specified by local_path.
    You can create an image sequence, a meta file will be created to specify
    the blast sound if one is used and its montage info (start, end, ...)
    https://www.notion.so/supamonks/SupaBlast-Manager-c42d365905fc4655a1c68c77338d00ba
    """
    ALL_DISPLAY_OPTION_TYPES = (
        HoudiniAmbientOcclusionDisplayOption,
        HoudiniAntiAliasingDisplayOption,
        HoudiniMotionBlurDisplayOption,
        HoudiniDepthOfFieldDisplayOption,
    )

    def __init__(
            self,
            local_path,
            scene_path,
            third_party_open,
            default_camera
    ):
        """
        Args:
            local_path (str): destination of blast in local machine (mandatory)
            scene_path (str): scene path (mandatory)
            default_camera (str): default camera name

            third_party_open (list[tuple]): Optional list of callbacks to open blasts with third party applications
                the first item of the tuple will be the label of the action when right-clicking a blast,
                the second item of the tuple the callback executed when clicking on this action,
                with BlastInfo of the blast as argument.
                For example: [("Open in Pd player", pd_player_callback), ("Open in RV", rv_callback)]
        """
        super().__init__(
            local_path,
            scene_path,
            default_camera,
            third_party_open
        )

        self.third_party_open = third_party_open
        self.default_camera = default_camera
        self.local_path = local_path
        self.scene_path = os.path.abspath(scene_path)

    @staticmethod
    def _get_hou():
        try:
            import hou
        except ImportError:
            raise PlayblastError("You cannot blast outside of Houdini.")
        return hou

    def do_blast(self, blast_type, blast):
        """
        :param blast_type: must be one of MOV / SEQ
        :param (BlastInfo) blast: object that contain all the UI setting parameters
        """
        path = blast.get_file_path().split('.', 1)[0]

        blast = (
            path, blast_type, blast.camera, blast.sounds, blast.start, blast.end, blast.display_types,
            blast.bg_color, blast.display_options,
            blast.hud_options, blast.display_grid, blast.width, blast.height, blast.scale
        )

        self._do_one_blast(*blast)

    def get_default_bg_color(self):
        return "Light"

    def _assert_current_scene(self):
        """
        Ensures the current scene exists
        :return: scene path
        :rtype: str
        """
        hou = self._get_hou()
        scene_path = hou.hipFile.path()
        if not os.path.basename(scene_path) == os.path.basename(self.scene_path):
            raise Exception("The current scene is not:\n  {}\nPlease close and reopen the SupaBlast Manager.".format(
                self.scene_path))

        return scene_path

    @contextlib.contextmanager
    def _blast_context(self, cam, start, end, display_types,
                       bg_color, display_options, hud_options, display_grid):

        restore_data = self._apply_display_overrides(display_grid)
        restore_data.update(self._apply_background_overrides(bg_color))
        restore_data.update(self._apply_camera_overrides(cam))

        display_options_instances = self._apply_playblast_display_options(display_options)

        try:
            yield
        except Exception:
            raise

        finally:
            self._restore_display_options(display_options_instances)
            self._restore_display_overrides(restore_data)
            self._restore_background_overrides(restore_data)
            self._restore_camera(restore_data)

    def _do_one_blast(self, path, blast_type, camera, sounds, start, end, display_types, bg_color,
                      display_options, hud_options, display_grid, width, height, scale):

        hou = self._get_hou()

        with self._blast_context(camera, start, end, display_types, bg_color,
                                 display_options, hud_options, display_grid):
            directory, filename = os.path.split(path)
            if not os.path.exists(directory):
                os.makedirs(directory)

            scene = houdini_utils.get_scene()
            flip_book_settings = houdini_utils.get_flipbook_settings()
            viewport_settings = houdini_utils.get_viewport_settings()

            flip_book_settings.output("{}.$F4.jpg".format(path))  # Provide flipbook full path with padding.
            flip_book_settings.frameRange((start, end))
            flip_book_settings.useResolution(scale)
            flip_book_settings.resolution((width, height))
            visible_types_value = getattr(hou.flipbookObjectType, display_types)
            flip_book_settings.visibleTypes(visible_types_value)
            flip_book_settings.outputToMPlay(False)

            if viewport_settings.ambientOcclusion:
                viewport_settings.setLighting(hou.viewportLighting.HighQuality)

            scene.flipbook(scene.curViewport(), flip_book_settings)

    def _apply_playblast_display_options(self, display_options):
        display_options_instances = []
        for display_option_type_name, active in display_options:
            display_option = eval(display_option_type_name + '()')
            display_option.set_active(active)
            display_options_instances.append(display_option)
            display_option.apply()

        return display_options_instances

    def _apply_camera_overrides(self, camera):
        restore_data = dict()
        restore_data["camera"] = houdini_utils.get_viewport_cam()
        houdini_utils.set_viewport_cam(camera)

        return restore_data

    def _restore_camera(self, restore_data):
        cam = restore_data.get("camera")
        houdini_utils.set_viewport_cam(cam)

    def get_available_cameras(self):
        camera_names = ["Current View"]
        cameras = houdini_utils.get_all_camera_nodes()
        camera_names.extend([cam.name() for cam in cameras])

        return camera_names

    def get_available_audios(self):
        return []

    def sequencer_is_available(self):
        return False

    def get_default_camera(self):
        return self.default_camera

    def get_default_audio(self):
        return "*"

    def get_history(self):
        self._assert_current_scene()
        return BlastInfo.get_history(self.local_path)

    def get_bg_color_options(self):

        return {
            "Light": (126, 146, 155),
            "Dark": (0, 0, 0),
            "Grey": (180, 180, 180)
        }

    def get_frame_rate(self):
        return houdini_utils.get_frame_rate()

    def get_render_size(self):
        return houdini_utils.get_flipbook_resolution()

    def get_scene_frame_range(self):
        return houdini_utils.get_playback_range()

    def get_display_configs(self):
        return {"Visible": "Visible",
                "Geo Only": "GeoOnly",
                "Geo Excluded": "GeoExcluded",
                "All": "AllObjects"}

    def _apply_display_overrides(self, display_grid=False):

        restore_data = dict()
        restore_data["ortho_grid"] = houdini_utils.get_display_ortho_grid()
        restore_data["reference_plane"] = houdini_utils.get_display_reference_plane()
        houdini_utils.set_display_ortho_grid(display_grid)
        houdini_utils.set_display_reference_plane(display_grid)

        return restore_data

    def _apply_background_overrides(self, bg_color_name):
        import hou

        if not bg_color_name:
            return {}
        restore_data = {"color_scheme": houdini_utils.get_viewport_settings().colorScheme()}

        color = getattr(hou.viewportColorScheme, bg_color_name)
        houdini_utils.get_viewport_settings().setColorScheme(color)

        return restore_data

    def _restore_background_overrides(self, restore_data):
        color_scheme = restore_data.get("color_scheme")
        if color_scheme:
            houdini_utils.get_viewport_settings().setColorScheme(color_scheme)

    def _restore_display_overrides(self, restore_data):
        houdini_utils.set_display_ortho_grid(restore_data["ortho_grid"])
        houdini_utils.set_display_reference_plane(restore_data["reference_plane"])

    def get_global_range(self):
        start, end = houdini_utils.get_frame_range()
        return int(start), int(end)

    def get_playback_range(self):
        start, end = houdini_utils.get_playback_range()
        return int(start), int(end)
