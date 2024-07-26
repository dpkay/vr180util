import os
import datetime
import re

EQUIRECT_CLOG3_DIR_NAME = "020_equirect_clog3"


class ResolveContext:
    def __init__(self, resolve):
        # general stuff
        self.project_manager = resolve.GetProjectManager()
        self.project = self.project_manager.GetCurrentProject()
        self.media_pool = self.project.GetMediaPool()
        self.root_folder = self.media_pool.GetRootFolder()

        # vr180 work specific stuff
        self.footage_root_folder_path = "/footage_v2"
        self.timelines_by_shoot_root_folder_path = "/timelines_v2/by_shoot"
        self.equirect_clog3_root_path = (
            f"{self.footage_root_folder_path}/{EQUIRECT_CLOG3_DIR_NAME}"
        )
        self.motion_magnitude_wav_root_path = (
            f"{self.footage_root_folder_path}/042_motion_magnitude_wav"
        )

    # general stuff
    def GetFolderByPath(self, path):
        path_folder_names = path.split("/")
        if path_folder_names[0] != "":
            raise Exception("Path must start with /")

        current_folder = self.root_folder
        for i in range(1, len(path_folder_names)):
            folder_name = path_folder_names[i]
            found = False
            for j, folder in current_folder.GetSubFolders().items():
                if folder.GetName() == folder_name:
                    current_folder = folder
                    found = True
                    break

            if not found:
                raise Exception(f"Subfolder not found: {folder_name}")

        return current_folder

    def GetClipNames(self, folder):
        return [f.GetName() for f in folder.GetClips().values()]

    def GetSubFolderNames(self, folder):
        return [f.GetName() for f in folder.GetSubFolders().values()]

    def GetFootageClipsInFolder(self, folder):
        return [
            clip
            for clip in folder.GetClipList()
            if clip.GetClipProperty("type") == "Video + Audio"
        ]

    def GetCLog3SequencePath(self, sequence_name):
        return f"{self.equirect_clog3_root_path}/{sequence_name}"

    def GetCLog3SequenceFolder(self, sequence_name):
        return self.GetFolderByPath(self.GetCLog3SequencePath(sequence_name))

    # vr180 specific stuff
    def GetCLog3SequenceNames(self):
        folder = self.GetFolderByPath(self.equirect_clog3_root_path)
        return self.GetSubFolderNames(folder)

    def GetCLog3ShotNamesForSequence(self, sequence_name):
        return self.GetClipNames(self.GetCLog3SequenceFolder(sequence_name))

    def GetSequenceNameFromMediaPoolItem(self, media_pool_item):
        # Hack: really should be simply getting the Resolve folder the MediaPoolItem is in, but
        # it's not clear whether the Resolve API provides such a function.
        file_path = media_pool_item.GetClipProperty("File Path")

        pattern = r"\\([^\\]+)\\[^\\]+$"  # Regex pattern
        match = re.search(pattern, file_path)
        if match:
            return match.group(1)
        else:
            raise Exception(f"Unable to extract sequence name from path: {file_path}")


class ResolveUpdater:
    def __init__(self, resolve_context, filesystem_context):
        self.resolve_context = resolve_context
        self.filesystem_context = filesystem_context

    def LinkProxyForMediaPoolItem(self, media_pool_item, proxy_root_filesystem_path):
        shot_name = media_pool_item.GetName()
        sequence_name = self.resolve_context.GetSequenceNameFromMediaPoolItem(
            media_pool_item
        )
        proxy_filesystem_path = os.path.join(
            # self.filesystem_context.rectilinear_bt709_root_path,
            proxy_root_filesystem_path,
            sequence_name,
            shot_name,
        )
        if not media_pool_item.LinkProxyMedia(proxy_filesystem_path):
            # raise Exception(
            print(
                f"LinkProxyMedia for shot {sequence_name}/{shot_name} and proxy path failed: {proxy_filesystem_path}"
            )

        # print(shot_rectilinear_bt709_filesystem_path)
        # print(os.path.exists(shot_rectilinear_bt709_filesystem_path))
        # print(media_pool_item.LinkProxyMedia(shot_rectilinear_bt709_filesystem_path))

    def LinkProxyForAllMediaPoolItemsInCurrentTimeline(
        self, proxy_root_filesystem_path
    ):
        # Get all TimelineItems in the current Timeline.
        timeline = self.resolve_context.project.GetCurrentTimeline()
        video_track_count = timeline.GetTrackCount("video")
        timeline_items = []
        for i in range(1, video_track_count + 1):
            timeline_items += timeline.GetItemListInTrack("video", i)

        for timeline_item in timeline_items:
            media_pool_item = timeline_item.GetMediaPoolItem()
            self.LinkProxyForMediaPoolItem(media_pool_item, proxy_root_filesystem_path)
            # sequence_name =
            # print(extracted_text)  # Output: 20240713a
            # print(media_pool_item.GetMetadata())
            # print(media_pool_item.GetMediaId())

        # print(timeline_items)
        #

    def LinkProxyForAllShotsWithoutProxy(self, proxy_root_filesystem_path):
        for sequence_name in self.resolve_context.GetCLog3SequenceNames():
            folder = self.resolve_context.GetCLog3SequenceFolder(sequence_name)
            clips = self.resolve_context.GetFootageClipsInFolder(folder)
            print(sequence_name)
            for clip in clips:
                print(clip.GetClipProperty("type"))
                proxy_media_path = clip.GetClipProperty("Proxy Media Path")
                if not proxy_media_path:
                    print(clip.GetClipProperty())
                    print(
                        f"Linking proxy for shot without previous proxy: {sequence_name}/{clip.GetName()}"
                    )
                    self.LinkProxyForMediaPoolItem(clip, proxy_root_filesystem_path)
            # self.
            # for shot_name in self.resolve_context.GetCLog3ShotNamesForSequence(sequence_name):
            #   print(sequence_name, shot_name)

    def CreateMissingShootSummaryTimelines(self):
        footage_sequence_names = set(self.resolve_context.GetCLog3SequenceNames())
        timeline_sequence_names = set(
            self.resolve_context.GetSubFolderNames(
                self.resolve_context.GetFolderByPath(
                    self.resolve_context.timelines_by_shoot_root_folder_path
                )
            )
        )
        print(footage_sequence_names)
        print(timeline_sequence_names)

        timelines_by_shoot_root_folder = self.resolve_context.GetFolderByPath(
            self.resolve_context.timelines_by_shoot_root_folder_path
        )
        missing_timeline_sequence_names = (
            footage_sequence_names - timeline_sequence_names
        )
        for sequence_name in missing_timeline_sequence_names:
            self.resolve_context.media_pool.AddSubFolder(
                timelines_by_shoot_root_folder, sequence_name
            )

        for sequence_name in footage_sequence_names:
            self.MaybeCreateMissingShootSummaryTimeline(sequence_name)

    def MaybeImportMotionMagnitudeWavClips(self, sequence_name, parent_folder):
        shot_names = self.filesystem_context.GetCLog3ShotNamesForSequence(sequence_name)
        shot_stems = [os.path.splitext(x)[0] for x in shot_names]
        motion_magnitude_wav_filenames = [f"{stem}.wav" for stem in shot_stems]
        existing_motion_magnitude_wav_clips = set(
            self.resolve_context.GetClipNames(parent_folder)
        )
        missing_motion_magnitude_wav_filenames = list(
            set(motion_magnitude_wav_filenames) - existing_motion_magnitude_wav_clips
        )
        missing_motion_magnitude_wav_filenames.sort()

        missing_motion_magnitude_wav_paths = [
            os.path.join(
                self.filesystem_context.path_manager.motion_magnitude_wav_dir_path,
                sequence_name,
                x,
            )
            for x in missing_motion_magnitude_wav_filenames
        ]
        print(missing_motion_magnitude_wav_paths)
        media_pool_items = self.resolve_context.media_pool.ImportMedia(
            missing_motion_magnitude_wav_paths
        )
        self.resolve_context.media_pool.MoveClips(media_pool_items, parent_folder)

    def MaybeCreateMissingShootSummaryTimeline(self, sequence_name):
        timeline_name = f"{sequence_name}_autogenerated"
        timeline_folder = self.resolve_context.GetFolderByPath(
            f"{self.resolve_context.timelines_by_shoot_root_folder_path}/{sequence_name}"
        )

        # deal with motion magnitude wavs
        motion_magnitude_root_folder = self.resolve_context.GetFolderByPath(
            self.resolve_context.motion_magnitude_wav_root_path
        )
        motion_magnitude_sequence_names = self.resolve_context.GetSubFolderNames(
            motion_magnitude_root_folder
        )
        if not sequence_name in motion_magnitude_sequence_names:
            self.resolve_context.media_pool.AddSubFolder(
                motion_magnitude_root_folder, sequence_name
            )
        motion_magnitude_folder_path = (
            f"{self.resolve_context.motion_magnitude_wav_root_path}/{sequence_name}"
        )
        print(motion_magnitude_folder_path)
        motion_magnitude_folder = self.resolve_context.GetFolderByPath(
            motion_magnitude_folder_path
        )
        self.MaybeImportMotionMagnitudeWavClips(sequence_name, motion_magnitude_folder)
        motion_magnitude_clips = list(motion_magnitude_folder.GetClips().values())
        motion_magnitude_clips.sort(key=lambda clip: clip.GetName())
        # print(f"mmc: {motion_magnitude_clips}")

        if not timeline_name in self.resolve_context.GetClipNames(timeline_folder):
            # get all the footage for this new timeline
            footage_folder = self.resolve_context.GetCLog3SequenceFolder(sequence_name)
            footage_clips = self.resolve_context.GetFootageClipsInFolder(footage_folder)
            footage_clips.sort(key=lambda clip: clip.GetName())

            print(f"Creating shoot summary timeline {timeline_name}")
            self.resolve_context.media_pool.SetCurrentFolder(timeline_folder)
            timeline = self.resolve_context.media_pool.CreateEmptyTimeline(
                timeline_name
            )
            #            timeline = self.resolve_context.media_pool.CreateTimelineFromClips(
            # timeline_name, footage_clips
            #
            self.resolve_context.project.SetCurrentTimeline(timeline)
            timeline.AddTrack("audio", "mono")
            timeline.SetTrackEnable("audio", 2, False)


            print(timeline.GetCurrentTimecode())

            for footage_clip, motion_magnitude_clip in zip(
                footage_clips, motion_magnitude_clips
            ):
                [footage_video_tli] = self.resolve_context.media_pool.AppendToTimeline(
                    [
                        {
                            "mediaPoolItem": footage_clip,
                            "mediaType": 1,
                            "trackIndex": 1,
                        }
                    ]
                )
                [footage_audio_tli] = self.resolve_context.media_pool.AppendToTimeline(
                    [
                        {
                            "mediaPoolItem": footage_clip,
                            "mediaType": 2,
                            "trackIndex": 1,
                            #"endFrame": footage_video_tli.GetDuration(),
                            "recordFrame": footage_video_tli.GetStart(),
                        }
                    ]
                )

                [motion_magnitude_tli] = self.resolve_context.media_pool.AppendToTimeline(
                    [
                        {
                            "mediaPoolItem": motion_magnitude_clip,
#                            "startFrame": 0,
                            #"endFrame": footage_video_tli.GetDuration(),
                            "mediaType": 2,
                            "trackIndex": 2,
                            "recordFrame": footage_video_tli.GetStart(),
                        }
                    ]
                )

                #print(motion_magnitude_tlis)

                # timeline.SetClipsLinked(footage_tlis + motion_magnitude_tlis, True)
                timeline.SetClipsLinked([footage_video_tli, footage_audio_tli, motion_magnitude_tli], True)

                #return

                # print(f"start: {timeline_item.GetStart()}")
                # print(f"end: {timeline_item.GetEnd()}")
                # print(f"duration: {timeline_item.GetDuration()}")

            # print(timeline.GetCurrentTimecode())
            # timeline.SetCurrentTimecode("01:00:00;00")
            """
            for i, clip in enumerate(motion_magnitude_clips):
                self.resolve_context.media_pool.AppendToTimeline(
                    [
                        {
                            "mediaPoolItem": clip,
                            "startFrame": 0,
                            "endFrame": 999,
                            "mediaType": 2,
                            "trackIndex": 2,
                            "recordFrame": timeline.GetStartFrame()+i*1000,
                        }
                    ]
                )
            """

            # print(timeline.GetCurrentTimecode())

            # print(f"addtrack result: {result}")

            # result = self.resolve_context.media_pool.MoveClips([timeline.GetMediaPoolItem()], timeline_folder)
            # print(f"moveclips result: {result}")
            # print(f"folder name: {timeline_folder.GetName()}")
            # print(f"timeline: {timeline}")

    def CreateMissingShotsInResolveForSequence(self, sequence_name):
        print(f"CreateMissingShotsInResolveForSequence: {sequence_name}")
        filesystem_shot_names = set(
            self.filesystem_context.GetCLog3ShotNamesForSequence(sequence_name)
        )
        resolve_shot_names = set(
            self.resolve_context.GetCLog3ShotNamesForSequence(sequence_name)
        )

        missing_shot_names = filesystem_shot_names - resolve_shot_names
        # print(f"resolve shot names: {resolve_shot_names}")
        print(f"missing shot names: {missing_shot_names}")

        # equirect_clog3_sequence_resolve_folder = resolve_context.GetFolderByPath(
        #     resolve_context.GetCLog3SequencePath(sequence_name)
        # )

        # TMP!!
        # missing_shot_names = set(list(missing_shot_names)[:3])

        clog3_sequence_filesystem_path = self.filesystem_context.GetCLog3SequencePath(
            sequence_name
        )
        missing_shot_clog3_filesystem_paths = [
            os.path.join(clog3_sequence_filesystem_path, shot_name)
            for shot_name in missing_shot_names
        ]

        # for shot_name in missing_shot_names_in_resolve:

        # resolve_sequence_folder =
        # resolve_sequence_names = set(self.resolve_context.GetCLog3SequenceNames())

        # creates the clip in a random folder
        # returns a clip for each path (even if some clips already existed, it just returns those instead of re-importing)
        media_pool_items = self.resolve_context.media_pool.ImportMedia(
            missing_shot_clog3_filesystem_paths
        )

        # print(f'mpi: {media_pool_items}')
        # clean up location of the new clips
        self.resolve_context.media_pool.MoveClips(
            media_pool_items, self.resolve_context.GetCLog3SequenceFolder(sequence_name)
        )

        # if media_pool_items:
        #    for media_pool_item in media_pool_items:
        #        print(media_pool_item.GetClipProperty('Proxy Media Path'))
        """
        for media_pool_item in media_pool_items:
            self.LinkProxyForMediaPoolItem(media_pool_item, self.filesystem_context.path_manager.slow_proxy_rectilinear_dir_path)

        timeline_name = f"{sequence_name} all (created at {datetime.datetime.now().strftime('%m/%d/%Y %H:%M:%S')})"
        resolve_context.media_pool.CreateTimelineFromClips(
            timeline_name, media_pool_items
        )
        """
        # shot_name = media_pool_item.GetName()
        # shot_rectilinear_bt709_filesystem_path = os.path.join(
        #     self.filesystem_context.rectilinear_bt709_root_path,
        #     sequence_name,
        #     shot_name,
        # )
        # print(shot_rectilinear_bt709_filesystem_path)
        # print(os.path.exists(shot_rectilinear_bt709_filesystem_path))
        # print(
        #     media_pool_item.LinkProxyMedia(shot_rectilinear_bt709_filesystem_path)
        # )

        # print(result)
        # print(missing_shot_filesystem_paths)

    def CreateMissingSequencesAndShotsInResolve(self):
        filesystem_sequence_names = set(self.filesystem_context.GetCLog3SequenceNames())
        resolve_sequence_names = set(self.resolve_context.GetCLog3SequenceNames())

        equirect_clog3_root_resolve_folder = self.resolve_context.GetFolderByPath(
            self.resolve_context.equirect_clog3_root_path
        )
        for sequence_name in filesystem_sequence_names:
            # Create folder if it doesn't exist yet
            if not sequence_name in resolve_sequence_names:
                # if not sequence_name in self.resolve_context.GetSubFolderNames(
                #    equirect_clog3_root_resolve_folder
                # ):
                self.resolve_context.media_pool.AddSubFolder(
                    equirect_clog3_root_resolve_folder, sequence_name
                )

            # Create any missing shots
            self.CreateMissingShotsInResolveForSequence(sequence_name)

        # self.LinkProxyForAllShotsWithoutProxy(self.filesystem_context.path_manager.slow_proxy_rectilinear_dir_path)
        self.CreateMissingShootSummaryTimelines()

    """
    def CreateMissingSequenceFoldersInResolve(self):
        filesystem_sequence_names = set(self.filesystem_context.GetCLog3SequenceNames())
        resolve_sequence_names = set(self.resolve_context.GetCLog3SequenceNames())
        print(filesystem_sequence_names)
        print(resolve_sequence_names)

        missing_sequence_names_in_resolve = (
            filesystem_sequence_names - resolve_sequence_names
        )

        equirect_clog3_root_resolve_folder = resolve_context.GetFolderByPath(
            resolve_context.equirect_clog3_root_path
        )
        for sequence_name in missing_sequence_names_in_resolve:
            resolve_context.media_pool.AddSubFolder(
                equirect_clog3_root_resolve_folder, sequence_name
            )
    """
