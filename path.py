import os


INPUT_EQUIRECT_DIR_NAME = "020_equirect_clog3"
PROXY_RECTILINEAR_DIR_NAME = "032_rectilinear_bt709_1080p_h264"
PROXY_EQUIRECT_DIR_NAME = "033_equirect_clog3_2k_h264"
MOTION_MAGNITUDE_DIR_NAME = "042_motion_magnitude_wav"


class PathManager:
    def __init__(self, slow_work_dir_path, fast_work_dir_path):
        self.slow_work_dir_path = slow_work_dir_path
        self.fast_work_dir_path = fast_work_dir_path

        self.input_dir_path = os.path.join(self.slow_work_dir_path, INPUT_EQUIRECT_DIR_NAME)
        self.slow_proxy_rectilinear_dir_path = os.path.join(self.slow_work_dir_path, PROXY_RECTILINEAR_DIR_NAME)
        self.slow_proxy_equirect_dir_path = os.path.join(self.slow_work_dir_path, PROXY_EQUIRECT_DIR_NAME)
        self.motion_magnitude_wav_dir_path = os.path.join(self.slow_work_dir_path, MOTION_MAGNITUDE_DIR_NAME)


class FilesystemContext:
    def __init__(self, path_manager):
        self.path_manager = path_manager

        # TODO: move all these to path manager
        #self.root_folder = self.path_manager
        #self.equirect_clog3_root_path = os.path.join(
            #self.root_folder, EQUIRECT_CLOG3_DIR_NAME
        #)
        #self.proxy_rectilinear_bt709_root_path = os.path.join(
        #    self.root_folder, PROXY_RECTILINEAR_BT709_DIR_NAME
        #)
        #self.proxy_equirect_clog3_root_path = os.path.join(
        #    self.root_folder, PROXY_EQUIRECT_CLOG3_DIR_NAME
        #)

        #PROXY_EQUIRECT_CLOG3_DIR_NAME

    def GetCLog3SequenceNames(self):
        return os.listdir(self.path_manager.input_dir_path)

    def GetCLog3SequencePath(self, sequence_name):
        return os.path.join(self.path_manager.input_dir_path, sequence_name)

    def GetCLog3ShotNamesForSequence(self, sequence_name):
        #return os.listdir(self.GetCLog3SequencePath(sequence_name))
        return [x for x in os.listdir(self.GetCLog3SequencePath(sequence_name)) if x.lower().endswith(".mp4")]
