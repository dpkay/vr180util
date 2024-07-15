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
        self.equirect_clog3_root_path = (
            f"{self.footage_root_folder_path}/{EQUIRECT_CLOG3_DIR_NAME}"
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

    def GetSubFolderNames(self, folder):
        return [f.GetName() for f in folder.GetSubFolders().values()]

    def GetCLog3SequencePath(self, sequence_name):
        return f"{self.equirect_clog3_root_path}/{sequence_name}"

    def GetCLog3SequenceFolder(self, sequence_name):
        return self.GetFolderByPath(self.GetCLog3SequencePath(sequence_name))

    # vr180 specific stuff
    def GetCLog3SequenceNames(self):
        folder = self.GetFolderByPath(self.equirect_clog3_root_path)
        return self.GetSubFolderNames(folder)

    def GetCLog3ShotNamesForSequence(self, sequence_name):
        return self.GetSubFolderNames(self.GetCLog3SequenceFolder(sequence_name))

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
            #self.filesystem_context.rectilinear_bt709_root_path,
            proxy_root_filesystem_path,
            sequence_name,
            shot_name,
        )
        if not media_pool_item.LinkProxyMedia(proxy_filesystem_path):
            raise Exception(
                f"LinkProxyMedia for proxy path failed: {proxy_filesystem_path}"
            )

        #print(shot_rectilinear_bt709_filesystem_path)
        #print(os.path.exists(shot_rectilinear_bt709_filesystem_path))
        #print(media_pool_item.LinkProxyMedia(shot_rectilinear_bt709_filesystem_path))


    def LinkProxyForAllMediaPoolItemsInCurrentTimeline(self, proxy_root_filesystem_path):
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

        #print(timeline_items)        

    def CreateMissingShotsInResolveForSequence(self, sequence_name):
        filesystem_shot_names = set(
            self.filesystem_context.GetCLog3ShotNamesForSequence(sequence_name)
        )
        resolve_shot_names = set(
            self.resolve_context.GetCLog3ShotNamesForSequence(sequence_name)
        )

        missing_shot_names = filesystem_shot_names - resolve_shot_names

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

        # returns a clip for each path (even if some clips already existed, it just returns those instead of re-importing)
        media_pool_items = resolve_context.media_pool.ImportMedia(
            missing_shot_clog3_filesystem_paths
        )
        for media_pool_item in media_pool_items:
            self.LinkProxyForMediaPoolItem(media_pool_item, self.filesystem_context.path_manager.slow_proxy_rectilinear_dir_path)

        timeline_name = f"{sequence_name} all (created at {datetime.datetime.now().strftime('%m/%d/%Y %H:%M:%S')})"
        resolve_context.media_pool.CreateTimelineFromClips(
            timeline_name, media_pool_items
        )
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

        equirect_clog3_root_resolve_folder = resolve_context.GetFolderByPath(
            resolve_context.equirect_clog3_root_path
        )
        for sequence_name in filesystem_sequence_names:
            # Create folder if it doesn't exist yet
            if not sequence_name in self.resolve_context.GetSubFolderNames(
                equirect_clog3_root_resolve_folder
            ):
                self.resolve_context.media_pool.AddSubFolder(
                    equirect_clog3_root_resolve_folder, sequence_name
                )

            # Create any missing shots
            self.CreateMissingShotsInResolveForSequence(sequence_name)


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
