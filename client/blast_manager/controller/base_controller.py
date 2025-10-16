"""
This module contains utils for creating Blast with specific parameters
"""

from __future__ import with_statement

import glob
import os
import time

MOV = 'MOV'
SEQ = 'SEQ'


class PlayblastError(RuntimeError):
    pass


class DisplayOption(object):

    def __init__(self):
        super(DisplayOption, self).__init__()

        self.w = None
        self.active = True
        self._to_restore = None

    def name(self):
        raise NotImplementedError()

    def build_controls(self, ctrl_widget, parent):
        self.w = ctrl_widget.add_check(parent, self.name())
        self.w.stateChanged.connect(self._on_control_change)
        self.update_controls()

    def update_controls(self):
        if self.w is None:
            return
        self.w.setChecked(self.active)

    def _on_control_change(self):
        self.active = self.w.isChecked()

    def set_active(self, b):
        """
        Tells whether the option is active or not (should be applied when blasting)
        """
        self.active = b and True or False
        self.update_controls()

    def set_default(self):
        self.active = True
        self.update_controls()

    def _store_to_restore(self):
        """
        You can implement this by giving the param to be restored from your dcc to self._to_restore
        This should be then use in the self._restore method
        """
        self._to_restore = None

    def _apply(self):
        """
        Implement this by applying the changes of this display option depending on self.active
        Call self._store_to_restore before applying the changes to store the current value, so it will be restored later
        """
        raise NotImplementedError()

    def apply(self):
        self._to_restore = None

        self._store_to_restore()
        self._apply()

    def _restore(self):
        """
        Implement this by restoring the dcc's param with what is stored in self._to_restore
        (self._to_restore should be set in the _store_to_restore method)
        """
        raise NotImplementedError()

    def restore(self):
        if self._to_restore is None:
            return

        return self._restore()


class AmbientOcclusionDisplayOption(DisplayOption):

    def name(self):
        return 'Ambient Occlusion'

    def set_default(self):
        self.active = True
        self.update_controls()


class MotionBlurDisplayOption(DisplayOption):

    def name(self):
        return 'Motion Blur'

    def set_default(self):
        self.active = False
        self.update_controls()


class DepthOfFieldDisplayOption(DisplayOption):

    def name(self):
        return 'Depth Of Field'

    def set_default(self):
        self.active = False
        self.update_controls()


class AntiAliasingDisplayOption(DisplayOption):

    def name(self):
        return 'Anti-Aliasing'

    def set_default(self):
        self.active = True
        self.update_controls()


class BlastInfo(object):
    """
    This class is a data structure containing parameters used for the Blast creation.
    """

    INFO_ATTRS = (
        "user",
        "scene_path",
        "blast_type",
        "start",
        "end",
        "width",
        "height",
        "scale",
        "bg_color",
        "sounds",
        "camera",
        "display_types",
        "display_options",
        "hud_options",
        "timestamp",
        "meta_file",
        "sounds_files",
        "use_sequencer",
        "display_grid",
        "frame_rate"
    )

    INFO_FILENAME = "infos.py"

    @classmethod
    def trash_path(cls):
        import tempfile

        path = os.path.join(tempfile.gettempdir(), 'PLAYBLAST_TRASH')
        try:
            os.makedirs(path)
        except OSError:
            pass
        return path

    @classmethod
    def get_history(cls, blast_path):

        if not os.path.exists(blast_path):
            os.makedirs(blast_path)

        blasts = []
        for blast_id in os.listdir(blast_path):
            blast_dir = blast_path + '/' + blast_id
            blast = cls()
            blast.load(blast_dir)
            blasts.append(blast)

        return blasts

    @classmethod
    def create(cls, blast_path, scene_path, blast_type, camera, sounds,
               start, end, width, height, scale, bg_color,
               display_types, display_options, hud_options, frame_rate,
               use_sequencer=False, display_grid=False):
        path = blast_path
        timestamp = time.time()
        blast_dir = str(int(timestamp))
        blast_path = path + '/' + blast_dir
        i = 0

        while os.path.exists(blast_path):
            i += 1
            blast_path = path + '/' + ('%s_%s' % (blast_dir, i))

        print('Creating Blast Info: %s', blast_path)
        os.makedirs(blast_path)
        blast = cls()
        blast.path = os.path.abspath(blast_path)
        blast.exists = True

        blast.user = os.environ['USERNAME']
        blast.scene_path = os.path.abspath(scene_path)
        blast.type = blast_type
        blast.camera = camera
        blast.sounds = sounds
        blast.start = start
        blast.end = end
        blast.width = width
        blast.height = height
        blast.scale = scale
        blast.bg_color = bg_color
        blast.display_types = display_types
        blast.display_options = display_options  # list of option_type_str:active_bool
        blast.timestamp = timestamp
        blast.hud_options = hud_options
        blast.use_sequencer = use_sequencer
        blast.display_grid = display_grid
        blast.has_mov = False
        blast.has_seq = False
        blast.seq_disk_range = (-1, -1)
        blast.frame_rate = frame_rate
        blast.write_info()
        return blast

    def __init__(self):
        self.path = None
        self.exists = False
        self.user = 'NoUser'
        self.scene_path = ''
        self.blast_type = SEQ

        self.start = self.end = self.width = self.height = self.scale = self.timestamp = 0
        self.bg_color = (160, 160, 160)
        self.display_types = self.camera = ''
        self.sounds = []
        self.sounds_files = self.meta_file = None
        self.display_options = []
        self.hud_options = {}
        self.seq_disk_range = (-1, -1)
        self.use_sequencer = self.has_mov = self.has_seq = self.display_grid = False
        self.frame_rate = 25
        self.reset()

    def reset(self):
        self.start = -1
        self.end = -1
        self.width = -1
        self.height = -1
        self.scale = 1
        self.bg_color = (160, 160, 160)
        self.display_types = '???'
        self.display_options = []
        self.hud_options = {}
        self.timestamp = 0
        self.camera = ''
        self.sounds = []
        self.seq_disk_range = (-1, -1)
        self.has_mov = False
        self.has_seq = False
        self.scene_path = ''
        self.frame_rate = 25
        self.sounds_files = None
        self.meta_file = None
        self.display_grid = False

    def get_file_path(self):
        if self.blast_type == MOV:
            return os.path.join(self.movie_path(), self.movie_name())
        return os.path.join(self.seq_path(), self.seq_pattern())

    def movie_name(self):
        return os.path.basename(os.path.dirname(self.path)) + ".mov"

    def movie_path(self):
        """this is the abs path of the movie"""
        return os.path.join(self.path, 'MOV', self.movie_name())

    def seq_pattern(self, frame_pattern='*'):
        return os.path.basename(os.path.dirname(self.path)) + (".{}.jpg".format(frame_pattern))

    def seq_meta_file_path(self):
        filename = self.seq_pattern().split('.', 1)[0] + ".meta"
        return os.path.join(self.seq_path(), filename)

    def seq_path(self):
        """this is the abs path of the sequence folder"""
        return os.path.join(self.path, 'SEQ')

    def load(self, path):
        self.path = path
        if not os.path.exists(path):
            self.exists = False
            return
        self.exists = True

        # -- Info
        self.reset()
        info_path = path + "/" + self.INFO_FILENAME

        if os.path.exists(info_path):
            try:
                exec(open(info_path).read(), {}, {"blast": self})
            except Exception as e:
                import traceback
                traceback.print_exc()
                print("ERROR when getting blast {}".format(info_path))
                return

        self.check_results()

    def check_results(self):
        # -- MOVIE
        movie_path = self.movie_path()
        if os.path.exists(movie_path):
            self.has_mov = True

        # -- IMAGES
        seq_path = self.seq_path()
        seq_pattern = self.seq_pattern()
        self.seq_disk_range = self.get_seq_range(seq_path, seq_pattern)
        if -1 not in self.seq_disk_range:
            self.has_seq = True

    def write_info(self, allow_overwrite=False):
        info_path = self.path + '/' + self.INFO_FILENAME
        if not allow_overwrite and os.path.exists(info_path):
            raise PlayblastError('Could not save info: file %r exists' % info_path)
        with open(info_path, 'w') as w:
            for attr in self.INFO_ATTRS:
                w.write('blast.%s = %r\n' % (attr, getattr(self, attr)))

    @staticmethod
    def get_seq_range(seq_path, seq_pattern):
        images = glob.glob1(seq_path, seq_pattern)
        start = 99999999
        end = -1

        for image in images:
            s, f, e = image.rsplit('.', 2)
            try:
                f = int(f)
            except ValueError:
                pass
            else:
                if start > f:
                    start = f
                elif f > end:
                    end = f

        return start, end

    def delete(self):
        if not self.exists:
            return
        src = self.path
        dst = os.path.join(self.trash_path(), os.path.basename(self.path), )
        while os.path.exists(dst):
            dst += '_1'
        os.rename(src, dst)


class BaseBlastController(object):
    """
    Here is the base manager class for running blasts, it must be initialized with default value and scene info.
    Subclass this and implement the NotImplemented methods with the dcc's functions
    The created blast will be stored in the local storage which is specified by local_path.
    You can create a video Blast or an image sequence, a meta file will be created to specify
    the blast sound if one is used and its montage info (start, end, ...)
    https://www.notion.so/supamonks/SupaBlast-Manager-c42d365905fc4655a1c68c77338d00ba
    """

    def __init__(
            self,
            local_path,
            scene_path,
            default_camera,
            third_party_open
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

        self.third_party_open = third_party_open
        self.default_camera = default_camera
        self.local_path = local_path
        self.scene_path = os.path.abspath(scene_path)

    def blast(self, blast_type, camera, sounds, start, end, width, height, scale, bg_color,
              display_types, display_options, hud_options, use_sequencer=False, display_grid=False):
        """
        Make a new blast into the defined local path.
        :param blast_type: Blast type, can be playblast_manager.MOV or playblast_manager.SEQ. the first one make a
        video blast and the second one make an image sequence
        :param camera: The name of the camera from which we make the blast
        :param sounds: list of maya sounds objects which contains the sounds files. Can be None,
        otherwise the sounds will be integrated to the video if the type is MOV or specified in the meta file
        in the other case.
        :param start: first frame number
        :param end: last frame number
        :param width: output resolution
        :param height: output resolution
        :param scale: output quality (float: 0.5 for half, 1 for full)
        :param bg_color: tuple of RGB defining the background color. Can be None, in this case, the background should
        be transparent.
        :param display_types:
        :param display_options: list
        :param hud_options: dict with different parameter defining HUD appearance ('text_background', 'text_color',
        'block_size', ...)
        :param use_sequencer: Use the maya camera sequencer to make the blast
        :param display_grid: Show the grid inside the blast
        :return: the created blast info (see BlastInfo)
        """
        frame_rate = self.get_frame_rate()
        scene_name = self._assert_current_scene()
        blast = BlastInfo.create(self.local_path, scene_name, blast_type, camera, sounds,
                                 start, end, width, height, scale, bg_color,
                                 display_types,
                                 display_options, hud_options, frame_rate, use_sequencer,
                                 display_grid=display_grid)
        print('Blast Created: %s', blast.path)
        self.do_blast(blast_type, blast)
        return blast

    def get_history(self):
        """
        Gets the history of blast infos
        :return: list of blasts
        :rtype: list(BlastInfo)
        """
        self._assert_current_scene()
        return BlastInfo.get_history(self.local_path)

    @staticmethod
    def _restore_display_options(display_options_instances):
        """
        Restores the display options  of the given instances
        :param list(_DisplayOption) display_options_instances:
        """
        for display_option in display_options_instances:
            display_option.restore()

    def get_montage_range(self):
        """
        Gets the montage range for this shot/sequence
        :return: start frame, end frame
        :rtype: int, int
        """
        scene_frame_range = self.get_scene_frame_range()
        return scene_frame_range

    def view_blast_seq(self, blast):
        """
        Called when double clicking a blast in the blast manager
        :param BlastInfo blast: blast to open
        """
        self.third_party_open(blast.seq_path())

    @staticmethod
    def explore_blast(blast):
        """
        Called when clicking "Explore Blast" in the right click menu of a blast in the Blast Manager
        Opens a Windows explorer at the stored location of the blast
        :param BlastInfo blast: blast to explore
        """
        import os
        os.startfile(blast.path)

    def get_scene_frame_range(self):
        """
        Implement this by returning the scene frame range with dcc functions
        :return: start frame, end frame
        :rtype: int, int
        """
        raise NotImplementedError()

    def get_frame_rate(self):
        raise NotImplementedError()

    def _assert_current_scene(self):
        raise NotImplementedError()

    def get_global_range(self):
        """
        Implement this by returning the animation frame range from the time slider
        :return: start frame and end frame
        :rtype: int, int
        """
        raise NotImplementedError()

    def get_playback_range(self):
        """
        Implement this by returning the playback range from the time slider
        :return: start frame and end frame
        :rtype: int, int
        """
        raise NotImplementedError()

    def get_display_configs(self):
        """
        Implement this by returning a dict of configs for display
        The key should be the name of the mode of display (used in the gui for choices)
        The value should be the dcc's specific attributes that you will use to toggle this mode
        E.G:
        >>> return {"Visible": "Visible",
        >>>         "Geo Only": "GeoOnly",
        >>>         "Geo Excluded": "GeoExcluded",
        >>>         "All": "AllObjects"}
        :return: dict of display configs
        :rtype: dict
        """
        raise NotImplementedError()

    def do_blast(self, blast_type, blast):
        raise NotImplementedError()

    def get_render_size(self):
        """
        Implement this by returning the render size in the render settings of your dcc
        :return: width, height
        :rtype: int, int
        """
        raise NotImplementedError()

    def get_default_camera(self):
        """
        Default camera used when opening the blast manager
        :return: default camera
        :rtype: str
        """
        return self.default_camera

    def get_available_cameras(self):
        """
        Implement this by returning a list of camera names that are currently available in the scene
        :return: list of cameras
        :rtype: list(str)
        """
        raise NotImplementedError()

    def get_default_audio(self):
        """
        Implement this by returning the default audio that will be used when opening the blast manager
        :return: default audio
        :rtype: str
        """
        raise NotImplementedError()

    def get_available_audios(self):
        """
        Implement this by returning a list of audio names that are currently available in the scene
        If you don't want to handle audio, return an empty list
        :return: list of audios
        :rtype: list(str)
        """
        raise NotImplementedError()

    def save_file(self):
        """
        Implement this by saving the current scene with the dcc's function
        Used when publishing a blast in the publish_blast method
        """
        NotImplementedError()

    def get_bg_color_options(self):
        """
        Implement this by returning a dict of colors
        The key should be the name of the colors (This will be used by the gui for displaying choices of colors)
        The value a tuple for the corresponding rgb color (This will be used by the gui for the background of
        the line edit, and should be used for coloring the background of the dcc).
        E.G:

        >>> return{
        >>>    "Red": (255, 0, 0),
        >>>    "Green": (0, 255, 0),
        >>>    "Blue": (0, 0, 255),
        >>>    "Black": (0, 0, 0),
        >>>    "Dark Grey": (100, 100, 100),
        >>>    "Light Grey": (150, 150, 150),
        >>>    "White": (255, 255, 255)
        >>>}

        :return: dict of colors
        :rtype: dict
        """
        raise NotImplementedError()
