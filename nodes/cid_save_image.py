import os
import folder_paths
import numpy as np
import datetime
import sys
import re
import logging
from PIL import Image
from PIL.PngImagePlugin import PngInfo

logger = logging.getLogger('cid_node_pack')

class TokenParser:
    """Handles token substitution in output paths."""
    
    @staticmethod
    def parse_tokens(text):
        """Parse tokens in the format [token_name] or [token_name(args)]."""
        if not text:
            return text
            
        # Handle time tokens: [time] or [time(format)]
        time_pattern = r'\[time(?:\(([^)]+)\))?\]'
        
        def replace_time(match):
            time_format = match.group(1) if match.group(1) else "%Y-%m-%d"
            return datetime.datetime.now().strftime(time_format)
            
        result = re.sub(time_pattern, replace_time, text)
        return result

class CidSaveImage:
    def __init__(self):
        self.output_dir = folder_paths.get_output_directory()
        self.type = "output"
        self.compress_level = 4

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE", ),
            },
            "optional": {
                "output_path": ("STRING", {"default": ""}),
                "filename_suffix": ("STRING", {"default": ""}),
                "metadata": ("STRING", {"default": "", "multiline": True})
            },
            "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"},
        }

    RETURN_TYPES = ()
    FUNCTION = "main"
    OUTPUT_NODE = True
    CATEGORY = "Cid Node Pack/IO"

    def main(self, images, output_path="", filename_suffix="", metadata="", prompt=None, extra_pnginfo=None):
        # Parse output path tokens if provided
        if output_path and output_path.strip() not in ["", "none", "."]:
            parsed_path = TokenParser.parse_tokens(output_path)
            # If path is not absolute, make it relative to default output directory
            if not os.path.isabs(parsed_path):
                full_output_folder = os.path.join(os.getcwd(), self.output_dir, parsed_path)
            else:
                full_output_folder = parsed_path
        else:
            # Use default output directory
            full_output_folder = os.path.join(os.getcwd(), self.output_dir)
        
        # Try to create directory if it doesn't exist
        try:
            os.makedirs(full_output_folder, exist_ok=True)
        except PermissionError:
            logger.error(f"No permission to create directory at {full_output_folder}")
            return {"ui": {"images": [], "error": f"Permission denied: Cannot create directory at {full_output_folder}"}}
        except OSError as e:
            logger.error(f"Error creating output directory: {str(e)}")
            return {"ui": {"images": [], "error": f"Failed to create output directory: {str(e)}"}}
            
        # Validate if directory is writable
        if not os.access(full_output_folder, os.W_OK):
            logger.error(f"Output directory is not writable: {full_output_folder}")
            return {"ui": {"images": [], "error": f"Output directory is not writable: {full_output_folder}"}}
        
        results = []
        for i, image in enumerate(images):
            try:
                img = Image.fromarray(np.clip(255. * image.cpu().numpy(), 0, 255).astype(np.uint8))
                
                # Create metadata if provided
                metadata_info = None
                if metadata:
                    try:
                        metadata_info = PngInfo()
                        # Try to parse metadata as a JSON dict
                        try:
                            import json
                            metadata_dict = json.loads(metadata)
                            if isinstance(metadata_dict, dict):
                                for key, value in metadata_dict.items():
                                    metadata_info.add_text(key, str(value))
                            else:
                                # If not a dict, just add as a single entry
                                metadata_info.add_text("metadata", metadata)
                        except json.JSONDecodeError:
                            # If not valid JSON, just add as a single entry
                            metadata_info.add_text("metadata", metadata)
                        except Exception as e:
                            logger.warning(f"Error processing metadata: {str(e)}")
                            metadata_info.add_text("metadata", metadata)
                    except Exception as e:
                        logger.warning(f"Failed to create PNG metadata: {str(e)}")
                        metadata_info = None
                
                # Generate unique filename
                counter = 0
                max_attempts = 99
                filename = None
                
                if filename_suffix:
                    truncated_suffix = filename_suffix[:75]
                    safe_suffix = ''.join(c if c.isalnum() or c in '._- ' else '_' for c in truncated_suffix)
                    timestamp = datetime.datetime.now().strftime("%H%M%S")
                    filename = f"{timestamp}-{safe_suffix}.png"
                else:
                    datetime_str = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                    filename = f"{datetime_str}.png"
                
                full_path = os.path.join(full_output_folder, filename)
                
                if os.path.exists(full_path):
                    while counter <= max_attempts:
                        file_count_str = f"{counter:02d}"
                        
                        if filename_suffix:
                            filename = f"{timestamp}-{safe_suffix}-{file_count_str}.png"
                        else:
                            filename = f"{datetime_str}-{file_count_str}.png"
                        
                        full_path = os.path.join(full_output_folder, filename)
                        if not os.path.exists(full_path):
                            break
                        counter += 1
                    
                    if counter > max_attempts:
                        logger.error(f"Failed to generate unique filename after {max_attempts} attempts")
                        continue
                
                try:
                    if metadata_info:
                        img.save(full_path, pnginfo=metadata_info, compress_level=self.compress_level)
                    else:
                        img.save(full_path, compress_level=self.compress_level)
                        
                    output_root = os.path.join(os.getcwd(), self.output_dir)
                    relative_path = os.path.relpath(full_output_folder, output_root) if full_output_folder != output_root else ""
                    subfolder = relative_path if relative_path != "." else ""
                    
                    results.append({
                        "filename": filename,
                        "subfolder": subfolder,
                        "type": self.type
                    })
                    
                except PermissionError:
                    logger.error(f"Permission denied when saving to {full_path}")
                except OSError as e:
                    logger.error(f"Error saving image: {str(e)}")
                
            except Exception as e:
                logger.error(f"Error processing image {i}: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
        
        if not results:
            return {"ui": {"images": [], "error": "Failed to save any images. Check logs for details."}}
            
        return {"ui": {"images": results}}
