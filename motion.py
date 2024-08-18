import os
import math
import cv2
import numpy as np
import wave
import struct
import subprocess


class MotionMagnitudeGenerator:
    def __init__(self, path_manager):
        self.path_manager = path_manager
        self.sample_rate = 44100  # Standard for CD-quality audio

    def generate_good_features(self, frame_gray, feature_params):
        # return cv2.goodFeaturesToTrack(
        #    frame_gray, mask=None, **feature_params
        # )
        hcount = 20
        vcount = 10
        xs = np.linspace(0, frame_gray.shape[1], hcount + 2)[1:-1]
        ys = np.linspace(0, frame_gray.shape[0], vcount + 2)[1:-1]
        xx, yy = np.meshgrid(xs, ys)
        # print(mesh)
        # print(xx)
        # print(yy)
        # print(cv2.goodFeaturesToTrack(
        #    frame_gray, mask=None, **feature_params
        # ))
        result = []
        for i, y in enumerate(ys):
            for j, x in enumerate(xs):
                result.append([[float(int(x.item())), float(int(y.item()))]])
        # result=[result]
        # print(result)
        # sys.exit(1)
        # print(cv2.goodFeaturesToTrack(frame_gray, mask=None, **feature_params))
        # print(np.asarray(result))
        return cv2.goodFeaturesToTrack(frame_gray, mask=None, **feature_params)
        # return np.asarray(result)

    def estimate_motion_magnitude_per_frame(self, video_path, max_num_frames=None):
        """Estimates camera movement between frames in a video.

        Args:
            video_path: Path to the MP4 video file.
        """
        MIN_FEATURES = 70
        UNTRACKABLE_MOTION_MAGNITUDE = 100.0

        motion_magnitudes = []

        cap = cv2.VideoCapture(video_path)  # Open the video
        _, prev_frame = cap.read()  # Read the first frame
        prev_frame_gray = cv2.cvtColor(
            prev_frame, cv2.COLOR_BGR2GRAY
        )  # Convert to grayscale

        # Feature detection and description (you can experiment with different methods)
        feature_params = dict(
            maxCorners=300, qualityLevel=0.3, minDistance=7, blockSize=7
        )
        prev_points = self.generate_good_features(prev_frame_gray, feature_params)
        # prev_points = cv2.goodFeaturesToTrack(
        #    prev_frame_gray, mask=None, **feature_params
        # )

        lk_params = dict(
            winSize=(30, 30),
            maxLevel=2,
            criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03),
        )

        num_frames_to_process = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if max_num_frames:
            num_frames_to_process = min(num_frames_to_process, max_num_frames)
        for frame_num in range(1, num_frames_to_process):
            _, frame = cap.read()  # Read the next frame
            frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            delta = [0, 0]

            # Track features using Lucas-Kanade optical flow
            try:
                next_points, status, error = cv2.calcOpticalFlowPyrLK(
                    prev_frame_gray, frame_gray, prev_points, None, **lk_params
                )

                good_new = next_points[status == 1]
                good_old = prev_points[status == 1]

                print(len(good_new))
                # print(len(good_old))

                # Estimate the transformation (in this case, translation)
                # print(transformation)
                if len(good_new) >= 3:
                    transformation, inliers = cv2.estimateAffinePartial2D(
                        good_old, good_new
                    )
                    delta = transformation[:, 2]  # Extract x/y translation values
                    motion_magnitude = np.linalg.norm(delta).item()
                else:
                    # Handle case with 1 feature
                    motion_magnitude = UNTRACKABLE_MOTION_MAGNITUDE
                    delta = [9999, 9999]
            except:
                # sometimes calcOpticalFlowPyrLK will just fail like this:
                # OpenCV(4.10.0) D:\a\opencv-python\opencv-python\opencv\modules\video\src\lkpyramid.cpp:1260: error: (-215:Assertion failed) (npoints = prevPtsMat.checkVector(2, CV_32F, true)) >= 0 in function 'cv::`anonymous-namespace'::SparsePyrLKOpticalFlowImpl::calc'
                motion_magnitude = UNTRACKABLE_MOTION_MAGNITUDE
                good_new = []

            motion_magnitudes.append(motion_magnitude)

            print(
                f"Frame {frame_num} ({len(good_new)} features): Camera movement (dx, dy) = ({delta[0]:.2f}, {delta[1]:.2f}) -- {motion_magnitude}"
            )

            if len(good_new) < MIN_FEATURES:
                feature_params = dict(
                    maxCorners=100, qualityLevel=0.3, minDistance=7, blockSize=7
                )
                # prev_points = cv2.goodFeaturesToTrack(
                #    prev_frame_gray, mask=None, **feature_params
                # )
                prev_points = self.generate_good_features(
                    prev_frame_gray, feature_params
                )
            else:
                prev_points = good_new.reshape(-1, 1, 2)

            # Update for next iteration
            prev_frame_gray = frame_gray.copy()

        cap.release()
        return motion_magnitudes

    def write_values_to_wav(self, wav_path, values, sample_rate):
        # Open the WAV file
        with wave.open(wav_path, "w") as wave_file:
            wave_file.setnchannels(1)  # Mono audio
            wave_file.setsampwidth(2)  # 16-bit audio
            wave_file.setframerate(sample_rate)

            # Pack the audio samples into bytes
            for sample in values:
                wave_file.writeframes(struct.pack("<h", int(sample)))

    def get_framerate_from_input_mp4(self, input_mp4_path):
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                "-show_entries",
                "stream=r_frame_rate",
                input_mp4_path,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        result_string = result.stdout.decode("utf-8").split()[0].split("/")
        fps = float(result_string[0]) / float(result_string[1])
        return fps

    def generate_motion_wav_from_input_mp4(self, input_mp4_path, output_wav_path):
        print(f"Generating `Motion WAV`: from {input_mp4_path} to {output_wav_path}")
        motion_magnitudes = self.estimate_motion_magnitude_per_frame(
            input_mp4_path, max_num_frames=None
        )

        # Generate WAV signal
        max_amplitude = 32000
        amplitude_factor = 1000
        #frames_per_second = 59.94
        frames_per_second = self.get_framerate_from_input_mp4(input_mp4_path)
        total_duration = len(motion_magnitudes) / frames_per_second  # Seconds
        frequency = 440  # A4 note
        t = np.linspace(
            0, total_duration, int(self.sample_rate * total_duration), False
        )
        audio = np.sin(2 * np.pi * frequency * t)
        for i, motion_magnitude in enumerate(motion_magnitudes):
            i
            range_start = math.floor(float(i) * self.sample_rate / frames_per_second)
            range_end = math.floor(float(i + 1) * self.sample_rate / frames_per_second)
            amplified_magnitude = min(
                max_amplitude, motion_magnitude * amplitude_factor
            )
            # amplified_magnitude = 99999999
            print(i, range_start, range_end, motion_magnitude)
            audio[range_start:range_end] *= amplified_magnitude

        # Write WAV to file
        self.write_values_to_wav(output_wav_path, audio, self.sample_rate)

    def generate_motion_wavs(self):
        # mp4_path = r"g:\vr180_work\032_rectilinear_bt709_1080p_h264\20240630\A005C103_240630BZ_CANON.vr.MP4"  # Replace with your video file path
        # wav_path = "sine_wave8.wav"
        # self.generate_motion_wav_from_input_mp4(mp4_path, wav_path)

        # return

        input_dir_sequences = os.listdir(
            self.path_manager.slow_proxy_rectilinear_dir_path
        )

        for sequence in input_dir_sequences:
            input_sequence_dir_path = os.path.join(
                self.path_manager.slow_proxy_rectilinear_dir_path, sequence
            )
            motion_magnitude_wav_sequence_dir_path = os.path.join(
                self.path_manager.motion_magnitude_wav_dir_path, sequence
            )

            if not os.path.exists(motion_magnitude_wav_sequence_dir_path):
                os.makedirs(motion_magnitude_wav_sequence_dir_path)

            input_sequence_filename_stems = set(
                os.path.splitext(x)[0]
                for x in os.listdir(input_sequence_dir_path)
                if x.lower().endswith(".mp4")
            )

            motion_magnitude_wav_sequence_filename_stems = set(
                os.path.splitext(x)[0]
                for x in os.listdir(motion_magnitude_wav_sequence_dir_path)
            )
            filename_stems_to_process = (
                input_sequence_filename_stems
                - motion_magnitude_wav_sequence_filename_stems
            )

            # print(
            #     f"input ({len(input_sequence_filename_stems)}): {input_sequence_filename_stems}"
            # )
            # print(
            #     f"motion wav ({len(motion_magnitude_wav_sequence_filename_stems)}): {motion_magnitude_wav_sequence_filename_stems}"
            # )
            # print(
            #     f"to process ({len(filename_stems_to_process)}): {filename_stems_to_process}"
            # )

            print(
                f"Motion Magnitude Generator - processing {len(filename_stems_to_process)} input files..."
            )

            for stem in filename_stems_to_process:
                input_path = os.path.abspath(
                    os.path.join(input_sequence_dir_path, f"{stem}.MP4")
                )
                motion_magnitude_wav_path = os.path.abspath(
                    os.path.join(motion_magnitude_wav_sequence_dir_path, f"{stem}.wav")
                )
                # print(input_path, motion_magnitude_wav_path)
                try:
                    self.generate_motion_wav_from_input_mp4(
                        input_path, motion_magnitude_wav_path
                    )
                except Exception as e:
                    print("Error generating motion WAV: ", e)
                    if os.path.exists(motion_magnitude_wav_path):
                        os.remove(motion_magnitude_wav_path)


# mp4_path = r"G:\vr180_work\032_rectilinear_bt709_1080p_h264\20240716\A010C169_240716BS_CANON.vr.MP4"  # Replace with your video file path
# wav_path = "sine_wave7.wav"

# mma = MotionMagnitudeGenerator()
# mma.generate_motion_wav_from_input_mp4(mp4_path, wav_path)
