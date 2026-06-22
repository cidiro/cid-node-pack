import os
import logging
import numpy as np
import torch
import cv2
import subprocess
import re
import itertools
import shutil
import time
from collections.abc import Mapping
try:
    import psutil
except ImportError:
    psutil = None

# ComfyUI-specific imports
from comfy.utils import common_upscale, ProgressBar

# --- Start of code for standalone operation ---

logger = logging.getLogger('cid_node_pack')
logger.setLevel(logging.WARNING)

# Constants
ENCODE_ARGS = ("utf-8", 'backslashreplace')
video_extensions = ['webm', 'mp4', 'mkv', 'gif', 'mov']

# FFMPEG path detection logic
def ffmpeg_suitability(path):
    try:
        version = subprocess.run([path, "-version"], check=True,
                                 capture_output=True).stdout.decode(*ENCODE_ARGS)
    except:
        return 0
    score = 0
    simple_criterion = [("libvpx", 20),("264",10), ("265",3),
                        ("svtav1",5),("libopus", 1)]
    for criterion in simple_criterion:
        if version.find(criterion[0]) >= 0:
            score += criterion[1]
    copyright_index = version.find('2000-2')
    if copyright_index >= 0:
        copyright_year = version[copyright_index+6:copyright_index+9]
        if copyright_year.isnumeric():
            score += int(copyright_year)
    return score

if "VHS_FORCE_FFMPEG_PATH" in os.environ:
    ffmpeg_path = os.environ.get("VHS_FORCE_FFMPEG_PATH")
else:
    ffmpeg_paths = []
    try:
        from imageio_ffmpeg import get_ffmpeg_exe
        ffmpeg_paths.append(get_ffmpeg_exe())
    except Exception:
        logger.debug("Failed to import imageio_ffmpeg")

    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg is not None:
        ffmpeg_paths.append(system_ffmpeg)
    if os.path.isfile("ffmpeg"):
        ffmpeg_paths.append(os.path.abspath("ffmpeg"))
    if os.path.isfile("ffmpeg.exe"):
        ffmpeg_paths.append(os.path.abspath("ffmpeg.exe"))
        
    if not ffmpeg_paths:
        logger.error("No valid ffmpeg found.")
        ffmpeg_path = None
    else:
        ffmpeg_path = max(set(ffmpeg_paths), key=ffmpeg_suitability)
logger.info(f"Using ffmpeg: {ffmpeg_path}")


# Helper functions
def strip_path(path):
    path = path.strip()
    if path.startswith("\""):
        path = path[1:]
    if path.endswith("\""):
        path = path[:-1]
    return path

def target_size(width, height, custom_width, custom_height, downscale_ratio=8) -> tuple[int, int]:
    if downscale_ratio is None:
        downscale_ratio = 8
    if custom_width == 0 and custom_height ==  0:
        pass
    elif custom_height == 0:
        height *= custom_width/width
        width = custom_width
    elif custom_width == 0:
        width *= custom_height/height
        height = custom_height
    else:
        width = custom_width
        height = custom_height
    width = int(width/downscale_ratio + 0.5) * downscale_ratio
    height = int(height/downscale_ratio + 0.5) * downscale_ratio
    return (width, height)

def get_audio(file, start_time=0, duration=0):
    if not ffmpeg_path:
        raise RuntimeError("ffmpeg could not be found.")
    args = [ffmpeg_path, "-i", file]
    if start_time > 0:
        args += ["-ss", str(start_time)]
    if duration > 0:
        args += ["-t", str(duration)]
    try:
        res =  subprocess.run(args + ["-f", "f32le", "-"],
                              capture_output=True, check=True)
        audio = torch.frombuffer(bytearray(res.stdout), dtype=torch.float32)
        match = re.search(r', (\d+) Hz, (\w+), ',res.stderr.decode(*ENCODE_ARGS))
    except subprocess.CalledProcessError as e:
        raise Exception(f"Failed to extract audio from {file}:\n" + e.stderr.decode(*ENCODE_ARGS))
    if match:
        ar = int(match.group(1))
        ac_map = {"mono": 1, "stereo": 2}
        ac = ac_map.get(match.group(2), 2)
    else:
        ar = 44100
        ac = 2
    audio = audio.reshape((-1,ac)).transpose(0,1).unsqueeze(0)
    return {'waveform': audio, 'sample_rate': ar}

class LazyAudioMap(Mapping):
    def __init__(self, file, start_time, duration):
        self.file = file
        self.start_time = start_time
        self.duration = duration
        self._dict = None
    def __getitem__(self, key):
        if self._dict is None:
            self._dict = get_audio(self.file, self.start_time, self.duration)
        return self._dict[key]
    def __iter__(self):
        if self._dict is None:
            self._dict = get_audio(self.file, self.start_time, self.duration)
        return iter(self._dict)
    def __len__(self):
        if self._dict is None:
            self._dict = get_audio(self.file, self.start_time, self.duration)
        return len(self._dict)
def lazy_get_audio(file, start_time=0, duration=0, **kwargs):
    return LazyAudioMap(file, start_time, duration)

def cv_frame_generator(video, force_rate, frame_load_cap, skip_first_frames,
                       select_every_nth):
    video_cap = cv2.VideoCapture(video)
    if not video_cap.isOpened():
        raise ValueError(f"{video} could not be loaded with OpenCV.")

    fps = video_cap.get(cv2.CAP_PROP_FPS)
    width = int(video_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(video_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(video_cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = (total_frames / fps) if fps > 0 else 0

    if width <= 0 or height <= 0:
        video_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        ret, frame = video_cap.read()
        if not ret:
            raise ValueError("Could not read the first frame to determine dimensions.")
        height, width, _ = frame.shape
        video_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

    total_frame_count = 0
    total_frames_evaluated = -1
    frames_added = 0
    base_frame_time = 1 / fps if fps > 0 else 0

    target_frame_time = 1 / force_rate if force_rate > 0 else base_frame_time
    
    yieldable_frames = total_frames
    if force_rate > 0:
        yieldable_frames = int(total_frames / fps * force_rate)
    if select_every_nth > 1:
        yieldable_frames //= select_every_nth
    if frame_load_cap > 0:
        yieldable_frames = min(frame_load_cap, yieldable_frames)
    
    yield (width, height, fps, duration, total_frames, target_frame_time, yieldable_frames)
    
    pbar = ProgressBar(yieldable_frames)

    while video_cap.isOpened():
        ret = video_cap.grab()
        if not ret:
            break
        
        total_frame_count += 1
        if total_frame_count <= skip_first_frames:
            continue
            
        if (total_frames_evaluated + 1) % select_every_nth != 0:
            total_frames_evaluated += 1
            continue

        ret, frame = video_cap.retrieve()
        if not ret:
            break
        
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = np.array(frame, dtype=np.float32) / 255.0
        
        yield frame

        frames_added += 1
        pbar.update_absolute(frames_added, yieldable_frames, None)

        if frame_load_cap > 0 and frames_added >= frame_load_cap:
            break
        total_frames_evaluated += 1

    video_cap.release()

def resized_cv_frame_gen(custom_width, custom_height, downscale_ratio, **kwargs):
    gen = cv_frame_generator(**kwargs)
    info =  next(gen)
    width, height = info[0], info[1]
    new_size = target_size(width, height, custom_width, custom_height, downscale_ratio)
    yield (*info, new_size[0], new_size[1], False)
    
    if new_size[0] != width or new_size[1] != height:
        def rescale(frame):
            s = torch.from_numpy(frame).permute(2, 0, 1).unsqueeze(0)
            s = common_upscale(s, new_size[0], new_size[1], "lanczos", "center")
            return s.squeeze(0).permute(1, 2, 0).numpy()
        yield from map(rescale, gen)
    else:
        yield from gen

def load_video(generator=resized_cv_frame_gen, **kwargs):
    kwargs['video'] = strip_path(kwargs['video'])
    downscale_ratio = 8
    
    gen = generator(downscale_ratio=downscale_ratio, **kwargs)
    (width, height, fps, duration, total_frames, target_frame_time, yieldable_frames, new_width, new_height, alpha) = next(gen)

    memory_limit_mb = kwargs.get('memory_limit_mb', None)
    memory_limit = None
    if memory_limit_mb is not None:
        memory_limit = memory_limit_mb * (1024 ** 2)
    elif psutil:
        try:
            memory_limit = (psutil.virtual_memory().available + psutil.swap_memory().free) - (128 * 1024 * 1024)
        except Exception:
            logger.warn("Failed to calculate available memory. Memory limit disabled.")
            memory_limit = float('inf')

    bytes_per_pixel = 12 # for float32 RGB
    max_loadable_frames = int(memory_limit // (width * height * bytes_per_pixel)) if memory_limit and width > 0 and height > 0 else float('inf')

    frames = list(itertools.islice(gen, max_loadable_frames))
    if not frames:
        raise RuntimeError("No frames generated from video.")

    images = torch.from_numpy(np.array(frames))

    start_time = kwargs.get('skip_first_frames', 0) * (1/fps if fps > 0 else 0)
    target_frame_time *= kwargs.get('select_every_nth', 1)
    
    audio_duration = len(images) * target_frame_time
    audio = lazy_get_audio(kwargs['video'], start_time, audio_duration)

    return (images, len(images), audio)


# --- End of standalone code ---


class CidLoadVideoFromDir:
    """Loads a video from a directory with various sorting and selection options."""
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "directory": ("STRING", {
                    "default": "",
                    "tooltip": "Path to the directory containing videos to load."
                }),
                "sort_by": (["a-z", "z-a", "last modified", "first modified"], {
                    "default": "a-z",
                    "tooltip": "Determines the order of videos: alphabetically or by modification time."
                }),
                "index": ("INT", {
                    "default": 0, 
                    "min": 0, 
                    "max": 0xffffffffffffffff,
                    "tooltip": "Index of the video to load. Wraps around if the index is larger than the number of videos."
                }),
                "include_subdirectories": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "Include videos from all subdirectories."
                }),
            },
        }

    RETURN_TYPES = ("IMAGE", "INT", "AUDIO", "STRING")
    RETURN_NAMES = ("IMAGE", "frame_count", "audio", "file_path")
    FUNCTION = "main"
    CATEGORY = "Cid Node Pack/IO"

    @classmethod
    def IS_CHANGED(cls, directory, **kwargs):
        if not os.path.isdir(directory):
            return float("NaN")
        # Check for directory mtime changes
        return os.path.getmtime(directory)

    def _get_sorted_files(self, directory, sort_by, include_subdirs):
        """Get a list of video files from a directory, sorted."""
        video_files = []
        extensions_with_dot = ['.' + ext for ext in video_extensions]

        if include_subdirs:
            for root, _, files in os.walk(directory):
                for file in files:
                    if file.lower().endswith(tuple(extensions_with_dot)):
                        video_files.append(os.path.join(root, file))
        else:
            for file in os.listdir(directory):
                if file.lower().endswith(tuple(extensions_with_dot)):
                    full_path = os.path.join(directory, file)
                    if os.path.isfile(full_path):
                        video_files.append(full_path)

        if sort_by == "a-z":
            video_files.sort()
        elif sort_by == "z-a":
            video_files.sort(reverse=True)
        elif sort_by == "last modified":
            video_files.sort(key=os.path.getmtime, reverse=True)
        elif sort_by == "first modified":
            video_files.sort(key=os.path.getmtime)
            
        return video_files

    def main(self, directory, sort_by, index, include_subdirectories):
        """Load a video from the directory."""
        
        if not directory or not os.path.isdir(directory):
            raise Exception(f"Invalid directory: {directory}")

        video_files = self._get_sorted_files(directory, sort_by, include_subdirectories)
        
        if not video_files:
            raise Exception(f"No video files found in directory: {directory}")
            
        num_videos = len(video_files)
        video_index = index % num_videos
        
        video_path = video_files[video_index]
        logger.info(f"Loading video {video_index + 1}/{num_videos}: {video_path}")
        
        # Hardcode parameters that are not exposed as widgets
        kwargs = {
            'video': video_path,
            'force_rate': 0,
            'custom_width': 0,
            'custom_height': 0,
            'frame_load_cap': 0,
            'skip_first_frames': 0,
            'select_every_nth': 1,
        }
        
        images, frame_count, audio = load_video(**kwargs)
        return (images, frame_count, audio, video_path)
