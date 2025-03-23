from .nodes.cid_save_image import CidSaveImage
from .nodes.cid_wildcard_processor import CidWildcardProcessor
from .nodes.cid_load_image_from_dir import CidLoadImageFromDir
from .nodes.cid_any_sync import CidAnySync
from .nodes.cid_any_buffer import CidAnyBuffer

WEB_DIRECTORY = "./js"

NODE_CLASS_MAPPINGS = {
    "CidSaveImage": CidSaveImage,
    "CidWildcardProcessor": CidWildcardProcessor,
    "CidLoadImageFromDir": CidLoadImageFromDir,
    "CidAnySync": CidAnySync,
    "CidAnyBuffer": CidAnyBuffer
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "CidSaveImage": "Cid Save Image",
    "CidWildcardProcessor": "Cid Wildcard Processor",
    "CidLoadImageFromDir": "Cid Load Image From Dir",
    "CidAnySync": "Cid Any Sync",
    "CidAnyBuffer": "Cid Any Buffer"
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]