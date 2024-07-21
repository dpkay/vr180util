import math
import subprocess
import os
from path import PathManager

#INPUT_EQUIRECT_DIR_NAME = "020_equirect_clog3"
#PROXY_RECTILINEAR_DIR_NAME = "032_rectilinear_bt709_1080p_h264"
#PROXY_EQUIRECT_DIR_NAME = "033_equirect_clog3_2k_h264"


#input_path = r"G:\vr180_work\10bit\A007C148_240707U2_CANON.vr.MP4"
#input_path = r"C:\vr180\work\030_split_10bit\20240618\A004C040_240618N5_CANON.vr-00.00.22.248-00.01.50.825.MP4"   # waterfall
#input_path = r"C:\vr180\work\030_split_10bit\20240618\A004C038_24061816_CANON.vr-00.00.09.168-00.00.12.435-seg1.MP4"   # very small

#input_path = r"C:\vr180\work\tmp\A007C148_240707U2_CANON.vr-00.00.35.510-00.00.37.115.MP4"  # smaller
#rectilinear_output_path = r"C:\vr180\work\tmp\rectilinear_even_smaller_out.mp4"
#equirect_output_path = r"C:\vr180\work\tmp\equirect_even_smaller_out.mp4"



class ProxyGenerator:
    def __init__(self, path_manager):
        self.path_manager = path_manager

    def generate_proxies_for_input_file(
        self, input_path, rectilinear_output_path, equirect_output_path
    ):
        hfov = 120.0
        deg_per_rad = 180 / math.pi
        aspect_ratio = 1920.0 / 1080
        tan_half_hfov = math.tan(hfov / 2 / deg_per_rad)
        tan_half_vfov = tan_half_hfov / aspect_ratio
        vfov = 2 * math.atan(tan_half_vfov) * deg_per_rad

        command = ["ffmpeg"]
        command += ["-hide_banner"]
        command += ["-i", input_path]

        # FILTERS
        filter_chain_strings = []
        # chain 1: split input into two
        filter_chain_strings.append(
            "[0:v]split=2[rectilinear_bt709_1080p][equirect_clog3_2k]"
        )

        # chain 2: rectilinear_bt709_1080p
        filters = []
        filters += ["crop=iw/2:ih:0:0"]
        filters += [
            f"v360=input=hequirect:output=rectilinear:h_fov={hfov}:v_fov={vfov}"
        ]
        filters += ["scale=1920:1080"]
        filters += ["format=yuv420p"]
        filters += ["lut3d=CinemaGamut_CanonLog3-to-BT709_WideDR_33_FF_Ver.2.0.cube"]
        filter_chain_strings.append(
            "[rectilinear_bt709_1080p]"
            + ",".join(filters)
            + "[rectilinear_bt709_1080p_out]"
        )

        # chain 3: equirect_clog3_2k
        filters = []
        filters += ["scale=2048:1024"]
        filter_chain_strings.append(
            "[equirect_clog3_2k]" + ",".join(filters) + "[equirect_clog3_2k_out]"
        )

        command += ["-filter_complex", ";".join(filter_chain_strings)]

        # VIDEO COMPERSSION
        # command += ["-t", "3"]
        # command += ["-vf", "scale=-2:400,format=yuv420p,lut3d=CinemaGamut_CanonLog3-to-BT709_WideDR_33_FF_Ver.2.0.cube"]
        # command += ['-sws_flags', 'lanczos', '-vcodec', 'h264', '-b:v', '1500k']
        # command += ['-c:v', 'libx265', '-vtag', 'hvc1', '-b:v', '80M']
        command += ["-c:v", "libx264", "-crf", "21"]

        # AUDIO COMPRESSION
        command += ["-c:a", "aac", "-b:a", "256k"]
        # command += ['-an']

        # GENERAL STUFF
        command += ["-y"]

        # OUTPUT MAPPINGS
        command += [
            "-map",
            "[rectilinear_bt709_1080p_out]",
            "-map",
            "0:a",
            rectilinear_output_path,
        ]
        command += [
            "-map",
            "[equirect_clog3_2k_out]",
            "-map",
            "0:a",
            equirect_output_path,
        ]
        print(command)
        subprocess.run(command, capture_output=False, text=True)


    def generate_proxies(self):    
        input_dir_sequences = os.listdir(self.path_manager.input_dir_path)

        for sequence in input_dir_sequences:
            print(f"SEQUENCE: {sequence}")
            input_sequence_dir_path = os.path.join(self.path_manager.input_dir_path, sequence)
            proxy_rectilinear_sequence_dir_path = os.path.join(
                self.path_manager.slow_proxy_rectilinear_dir_path, sequence
            )
            proxy_equirect_sequence_dir_path = os.path.join(
                self.path_manager.slow_proxy_equirect_dir_path, sequence
            )

            if not os.path.exists(proxy_rectilinear_sequence_dir_path):
                os.makedirs(proxy_rectilinear_sequence_dir_path)
            if not os.path.exists(proxy_equirect_sequence_dir_path):
                os.makedirs(proxy_equirect_sequence_dir_path)

            input_sequence_filenames = set(
                x
                for x in os.listdir(input_sequence_dir_path)
                if x.lower().endswith(".mp4")
            )
            proxy_rectilinear_sequence_filenames = set(
                os.listdir(proxy_rectilinear_sequence_dir_path)
            )
            proxy_equirect_sequence_filenames = set(
                os.listdir(proxy_equirect_sequence_dir_path)
            )
            proxy_full_filenames = (
                proxy_rectilinear_sequence_filenames & proxy_equirect_sequence_filenames
            )
            filenames_to_process = input_sequence_filenames - proxy_full_filenames

            print(
                f"input ({len(input_sequence_filenames)}): {input_sequence_filenames}"
            )
            print(
                f"rectilinear proxy ({len(proxy_rectilinear_sequence_filenames)}): {proxy_rectilinear_sequence_filenames}"
            )
            print(
                f"equirect proxy ({len(proxy_equirect_sequence_filenames)}): {proxy_equirect_sequence_filenames}"
            )
            print(f"to process ({len(filenames_to_process)}): {filenames_to_process}")

            print(f"Processing {len(filenames_to_process)} input files...")

            for filename in filenames_to_process:
                input_path = os.path.abspath(
                    os.path.join(input_sequence_dir_path, filename)
                )
                proxy_rectilinear_path = os.path.abspath(
                    os.path.join(proxy_rectilinear_sequence_dir_path, filename)
                )
                proxy_equirect_path = os.path.abspath(
                    os.path.join(proxy_equirect_sequence_dir_path, filename)
                )
                # if os.path.exists(output_path):
                #    print("Path already exists: " + output_path)
                #    #assert(False)
                #    print(f"Skipping ${filename} because it already exists.")
                # else:
                #    #print(input_path, output_path)
                self.generate_proxies_for_input_file(
                    input_path, proxy_rectilinear_path, proxy_equirect_path
                )
