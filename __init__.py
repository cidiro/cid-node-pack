from .nodes.cid_save_image import CidSaveImage
from .nodes.cid_extract_image_metadata import CidExtractImageMetadata
from .nodes.cid_extract_metadata import CidExtractMetadata
from .nodes.cid_extract_video_metadata import CidExtractVideoMetadata
from .nodes.cid_extract_audio_metadata import CidExtractAudioMetadata
from .nodes.cid_wildcard_processor import CidWildcardProcessor
from .nodes.cid_load_image_from_dir import CidLoadImageFromDir
from .nodes.cid_any_sync import CidAnySync
from .nodes.cid_any_buffer import CidAnyBuffer
from .nodes.cid_any_queue import CidAnyQueue
from .nodes.cid_concatenate_strings import CidConcatenateStrings
from .nodes.cid_any_list import CidAnyList
from .nodes.cid_store_any import CidStoreAny
from .nodes.cid_reload_image import CidReloadImage
from .nodes.cid_concatenate_image_batches import CidConcatenateImageBatches
from .nodes.cid_load_video_from_dir import CidLoadVideoFromDir
from .nodes.cid_counter import CidCounter
from .nodes.cid_get_global_variable import CidGetGlobalVariable
from .nodes.cid_set_global_variable import CidSetGlobalVariable
from .nodes.cid_boolean_multiplexer import CidBooleanMultiplexer
from .nodes.cid_boolean_demultiplexer import CidBooleanDemultiplexer
from .nodes.cid_json_get import CidJsonGet
from .nodes.cid_json_add import CidJsonAdd
from .nodes.cid_json_append import CidJsonAppend
from .nodes.cid_json_remove import CidJsonRemove
from .nodes.cid_json_save import CidJsonSave
from .nodes.cid_json_load import CidJsonLoad
from .nodes.cid_json_to_yaml import CidJsonToYaml
from .nodes.cid_yaml_to_json import CidYamlToJson
from .nodes.cid_string_contains import CidStringContains
from .nodes.cid_string_list_add import CidStringListAdd
from .nodes.cid_get_directory_name import CidGetDirectoryName
from .nodes.cid_get_file_name import CidGetFileName
from .nodes.cid_get_file_extension import CidGetFileExtension
from .nodes.cid_path_join import CidPathJoin
from .nodes.cid_apply_mask import CidApplyMask
from .nodes.cid_crop_and_stitch import CidCropAndStitch
from .nodes.cid_mask_resize import CidMaskResize
from .nodes.cid_play_sound import CidPlaySound
from .nodes.cid_llm_chat import CidLLMChat
from .nodes.cid_llm_system_prompt import CidLLMSystemPrompt
from .nodes.cid_llm_unload import CidLLMUnload
from .nodes.cid_trigger_every_n import CidTriggerEveryN
from .nodes.cid_trigger_duty_cycle import CidTriggerDutyCycle
from .nodes.cid_assert_type import CidAssertType

WEB_DIRECTORY = "./js"

NODE_CLASS_MAPPINGS = {
    "CidSaveImage": CidSaveImage,
    "CidExtractMetadata": CidExtractMetadata,
    "CidWildcardProcessor": CidWildcardProcessor,
    "CidLoadImageFromDir": CidLoadImageFromDir,
    "CidAnySync": CidAnySync,
    "CidAnyBuffer": CidAnyBuffer,
    "CidAnyQueue": CidAnyQueue,
    "CidConcatenateStrings": CidConcatenateStrings,
    "CidAnyList": CidAnyList,
    "CidStoreAny": CidStoreAny,
    "CidReloadImage": CidReloadImage,
    "CidConcatenateImageBatches": CidConcatenateImageBatches,
    "CidLoadVideoFromDir": CidLoadVideoFromDir,
    "CidCounter": CidCounter,
    "CidGetGlobalVariable": CidGetGlobalVariable,
    "CidSetGlobalVariable": CidSetGlobalVariable,
    "CidBooleanMultiplexer": CidBooleanMultiplexer,
    "CidBooleanDemultiplexer": CidBooleanDemultiplexer,
    "CidJsonGet": CidJsonGet,
    "CidJsonRemove": CidJsonRemove,
    "CidJsonAdd": CidJsonAdd,
    "CidJsonAppend": CidJsonAppend,
    "CidJsonSave": CidJsonSave,
    "CidJsonLoad": CidJsonLoad,
    "CidJsonToYaml": CidJsonToYaml,
    "CidYamlToJson": CidYamlToJson,
    "CidStringContains": CidStringContains,
    "CidStringListAdd": CidStringListAdd,
    "CidGetDirectoryName": CidGetDirectoryName,
    "CidGetFileName": CidGetFileName,
    "CidGetFileExtension": CidGetFileExtension,
    "CidPathJoin": CidPathJoin,
    "CidApplyMask": CidApplyMask,
    "CidCropAndStitch": CidCropAndStitch,
    "CidMaskResize": CidMaskResize,
    "CidPlaySound": CidPlaySound,
    "CidLLMChat": CidLLMChat,
    "CidLLMSystemPrompt": CidLLMSystemPrompt,
    "CidLLMUnload": CidLLMUnload,
    "CidTriggerEveryN": CidTriggerEveryN,
    "CidTriggerDutyCycle": CidTriggerDutyCycle,
    "CidAssertType": CidAssertType,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "CidSaveImage": "Save Image (Cid)",
    "CidExtractImageMetadata": "Extract Image Metadata (Cid)",
    "CidExtractMetadata": "Extract Metadata (Cid)",
    "CidExtractVideoMetadata": "Extract Video Metadata (Cid)",
    "CidExtractAudioMetadata": "Extract Audio Metadata (Cid)",
    "CidWildcardProcessor": "Wildcard Processor (Cid)",
    "CidLoadImageFromDir": "Load Image From Directory (Cid)",
    "CidAnySync": "Any Sync (Cid)",
    "CidAnyBuffer": "Any Buffer (Cid)",
    "CidAnyQueue": "Any Queue (Cid)",
    "CidConcatenateStrings": "Concatenate Strings (Cid)",
    "CidAnyList": "Any List (Cid)",
    "CidStoreAny": "Store Any (Cid)",
    "CidReloadImage": "Reload Image (Cid)",
    "CidConcatenateImageBatches": "Concatenate Image Batches (Cid)",
    "CidLoadVideoFromDir": "Load Video From Directory (Cid)",
    "CidCounter": "Counter (Cid)",
    "CidGetGlobalVariable": "Get Global Variable (Cid)",
    "CidSetGlobalVariable": "Set Global Variable (Cid)",
    "CidBooleanMultiplexer": "Boolean Multiplexer (Cid)",
    "CidBooleanDemultiplexer": "Boolean Demultiplexer (Cid)",
    "CidJsonGet": "JSON Get (Cid)",
    "CidJsonAdd": "JSON Add (Cid)",
    "CidJsonAppend": "JSON Append (Cid)",
    "CidJsonRemove": "JSON Remove (Cid)",
    "CidJsonSave": "JSON Save (Cid)",
    "CidJsonLoad": "JSON Load (Cid)",
    "CidJsonToYaml": "JSON to YAML (Cid)",
    "CidYamlToJson": "YAML to JSON (Cid)",
    "CidStringContains": "String Contains (Cid)",
    "CidStringListAdd": "String List Add (Cid)",
    "CidGetDirectoryName": "Get Directory Name (Cid)",
    "CidGetFileName": "Get File Name (Cid)",
    "CidGetFileExtension": "Get File Extension (Cid)",
    "CidPathJoin": "Path Join (Cid)",
    "CidApplyMask": "Apply Mask (Cid)",
    "CidCropAndStitch": "Crop and Stitch (Cid)",
    "CidMaskResize": "Mask Resize (Cid)",
    "CidPlaySound": "Play Sound (Cid)",
    "CidLLMChat": "LLM Chat (Cid)",
    "CidLLMSystemPrompt": "LLM System Prompt (Cid)",
    "CidLLMUnload": "LLM Unload (Cid)",
    "CidTriggerEveryN": "Trigger Every N (Cid)",
    "CidTriggerDutyCycle": "Trigger Duty Cycle (Cid)",
    "CidAssertType": "Assert Type (Cid)",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
