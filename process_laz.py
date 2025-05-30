import pdal
import json
import os
import time
import argparse
from enum import Enum
from typing import List, Tuple, Dict, Any
from spatial_lib import run_pipe_with_time


# Configuration section - edit these settings as needed
class Config:
    # Processing mode: 'auto', 'single', 'separated'
    # - auto: automatically detect based on directory structure and file types
    # - single: all files are in one directory
    # - separated: files are in separate ground and non-ground directories
    MODE = 'auto'
    
    # Input directory or parent directory containing Ground/Non-Ground folders
    INPUT_DIR = "input/lidar/2024-10-04"
    
    # Only used in separated mode - specify subdirectories for ground and non-ground
    GROUND_DIR = "Ground"  # Subfolder or full path to ground files
    NON_GROUND_DIR = "Non-Ground"  # Subfolder or full path to non-ground files
    
    # Output configuration
    OUTPUT_DIR = None  # If None, will use "output/processed/<input_dir_basename>"
    OUTPUT_FILENAME = "lidar_combined.laz"  # Final filename (always fixed now)
    
    # Spatial filtering (only used in separated mode)
    # Set to None to disable spatial filtering
    SPATIAL_FILTER = {
        "min_x": 295000,
        "max_x": 297000,
        "min_y": 6425000,
        "max_y": 6428000,
        "step": 1000,
        "excluded_prefix": ['297000_6425000']
    }
    
    # PDAL processing options
    STREAMING = True  # Use streaming mode for PDAL processing
    CHUNK_SIZE = 10000  # Chunk size for streaming mode
    
    # Classification values
    GROUND_CLASS = 2
    NON_GROUND_CLASS = 4


class ProcessingMode(Enum):
    AUTO = 'auto'
    SINGLE = 'single'
    SEPARATED = 'separated'


def get_file_list(directory: str, extensions: List[str], prefixes: List[str] = None) -> List[str]:
    """Get list of files with specific extensions and optional prefixes."""
    files = []
    for f in os.listdir(directory):
        # Check if file has one of the specified extensions
        if any(f.lower().endswith(ext.lower()) for ext in extensions):
            # Check prefixes if specified
            if prefixes is None or any(f.startswith(prefix) for prefix in prefixes):
                file_path = os.path.join(directory, f)
                files.append(file_path)
    return files


def generate_spatial_prefixes(config) -> List[str]:
    """Generate file prefixes based on spatial filtering configuration."""
    if config.SPATIAL_FILTER is None:
        return None
        
    sf = config.SPATIAL_FILTER
    included_prefixes = []
    
    for x in range(sf["min_x"], sf["max_x"] + sf["step"], sf["step"]):
        for y in range(sf["min_y"], sf["max_y"] + sf["step"], sf["step"]):
            # Skip excluded prefixes
            if sf["excluded_prefix"] and f"{x}_{y}" in sf["excluded_prefix"]:
                continue
            included_prefix = f"{x}_{y}"
            included_prefixes.append(included_prefix)
            
    return included_prefixes


def detect_processing_mode(config) -> ProcessingMode:
    """
    Detect the appropriate processing mode based on the input directory structure.
    """
    if config.MODE != 'auto':
        return ProcessingMode(config.MODE)
        
    # Check if there are Ground and Non-Ground directories
    ground_dir = os.path.join(config.INPUT_DIR, config.GROUND_DIR)
    non_ground_dir = os.path.join(config.INPUT_DIR, config.NON_GROUND_DIR)
    
    if os.path.isdir(ground_dir) and os.path.isdir(non_ground_dir):
        return ProcessingMode.SEPARATED
    else:
        return ProcessingMode.SINGLE


def is_xyz_file(filepath: str) -> bool:
    """Check if the file is an XYZ file."""
    return filepath.lower().endswith('.xyz')


def generate_tag(prefix, index):
    """Generate a unique tag for PDAL pipeline elements."""
    return f"{prefix}_{index+1}"


def generate_single_pipeline(input_files: List[str], output_file: str) -> Dict[str, Any]:
    """Generate a PDAL pipeline for merging multiple files from a single directory."""
    pipeline = []
    
    # Add all files as readers
    for file_path in input_files:
        if is_xyz_file(file_path):
            pipeline.append({
                "type": "readers.text",
                "filename": file_path,
                "spatialreference": "EPSG:7856",
                "header": "X Y Z",
            })
        else:
            pipeline.append({
                "type": "readers.las",
                "filename": file_path
            })
    
    # Add merge filter if there's more than one input file
    if len(input_files) > 1:
        pipeline.append({
            "type": "filters.merge"
        })
    
    # Add writer
    pipeline.append({
        "type": "writers.las",
        "filename": output_file,
        "compression": "laszip"
    })
    
    return {"pipeline": pipeline}


def generate_separated_pipeline(ground_files: List[str], non_ground_files: List[str], output_file: str) -> Dict[str, Any]:
    """Generate a PDAL pipeline for merging ground and non-ground files."""
    pipeline = []
    input_tags = []
    
    # Check if files are XYZ or LAS/LAZ
    is_xyz = any(is_xyz_file(f) for f in ground_files + non_ground_files)
    
    # Add non-ground files
    for i, ng_file in enumerate(non_ground_files):
        reader_tag = generate_tag("ng", i)
        
        if is_xyz:
            pipeline.append({
                "type": "readers.text",
                "filename": ng_file,
                "spatialreference": "EPSG:7856",
                "header": "X Y Z",
            })
            pipeline.append({
                "type": "filters.assign",
                "value": f"Classification={Config.NON_GROUND_CLASS}",
                "tag": reader_tag
            })
        else:
            pipeline.append({
                "type": "readers.las",
                "filename": ng_file,
            })
            pipeline.append({
                "type": "filters.assign",
                "assignment": f"Classification[:]={Config.NON_GROUND_CLASS}",
                "tag": reader_tag
            })
            
        input_tags.append(reader_tag)

    # Add ground files
    for i, g_file in enumerate(ground_files):
        tag = generate_tag("g", i)
        
        if is_xyz:
            pipeline.append({
                "type": "readers.text",
                "filename": g_file,
                "spatialreference": "EPSG:7856",
                "header": "X Y Z",
            })
            pipeline.append({
                "type": "filters.assign",
                "value": f"Classification={Config.GROUND_CLASS}",
                "tag": tag
            })
            input_tags.append(tag)
        else:
            pipeline.append({
                "type": "readers.las",
                "filename": g_file,
                "tag": tag
            })
            input_tags.append(tag)

    # Merge all tagged inputs
    pipeline.append({
        "type": "filters.merge",
        "inputs": input_tags
    })

    # Add HAG detection filter
    pipeline.append({
        "type": "filters.hag_nn"
    })

    # Final writer
    pipeline.append({
        "type": "writers.las",
        "filename": output_file,
        "compression": "laszip",
        "extra_dims": "HeightAboveGround=float32" 
    })

    return {"pipeline": pipeline}


def process_files():
    """Main function to process files based on configuration."""
    # Determine processing mode
    mode = detect_processing_mode(Config)
    print(f"Operating in {mode.value} mode")
    
    # Setup output directory
    if Config.OUTPUT_DIR is None:
        output_dir = os.path.join("output", "processed", os.path.basename(Config.INPUT_DIR))
    else:
        output_dir = Config.OUTPUT_DIR
        
    os.makedirs(output_dir, exist_ok=True)
    output_filename = os.path.join(output_dir, Config.OUTPUT_FILENAME)
    
    print(f"Output directory: {output_dir}")
    print(f"Output filename: {output_filename}")
    
    # Generate spatial prefixes if spatial filtering is enabled
    prefixes = generate_spatial_prefixes(Config)
    if prefixes:
        print(f"Using spatial prefixes filter with {len(prefixes)} prefixes")
    
    # Process based on mode
    if mode == ProcessingMode.SINGLE:
        # Get all LAS/LAZ/XYZ files from the input directory
        input_files = get_file_list(Config.INPUT_DIR, ['.las', '.laz', '.xyz'], prefixes)
        
        print(f"Found {len(input_files)} input files")
        if not input_files:
            print("No input files found. Check your configuration.")
            return
            
        pipeline_json = generate_single_pipeline(input_files, output_filename)
        
    elif mode == ProcessingMode.SEPARATED:
        # Get paths for ground and non-ground directories
        ground_dir = os.path.join(Config.INPUT_DIR, Config.GROUND_DIR)
        if not os.path.isdir(ground_dir):
            ground_dir = Config.GROUND_DIR  # Use as absolute path if subfolder doesn't exist
            
        non_ground_dir = os.path.join(Config.INPUT_DIR, Config.NON_GROUND_DIR)
        if not os.path.isdir(non_ground_dir):
            non_ground_dir = Config.NON_GROUND_DIR  # Use as absolute path if subfolder doesn't exist
        
        print(f"Ground directory: {ground_dir}")
        print(f"Non-ground directory: {non_ground_dir}")
        
        # Handle LAS or XYZ directories - search for both extensions
        file_extensions = ['.las', '.laz', '.xyz']
        ground_files = get_file_list(ground_dir, file_extensions, prefixes)
        non_ground_files = get_file_list(non_ground_dir, file_extensions, prefixes)
        
        print(f"Found {len(ground_files)} ground files and {len(non_ground_files)} non-ground files")
        if not ground_files and not non_ground_files:
            print("No input files found. Check your configuration.")
            return
            
        pipeline_json = generate_separated_pipeline(ground_files, non_ground_files, output_filename)
    
    # Execute the pipeline
    print(json.dumps(pipeline_json, indent=4))
    p = pdal.Pipeline(json.dumps(pipeline_json))
    run_pipe_with_time(p, streaming=Config.STREAMING, chunk_size=Config.CHUNK_SIZE)


if __name__ == "__main__":
    # Optional command-line arguments - can be extended as needed
    parser = argparse.ArgumentParser(description='Process LiDAR files (LAS, LAZ, XYZ).')
    parser.add_argument('--mode', choices=['auto', 'single', 'separated'], 
                        help='Processing mode (auto, single, separated)', default=Config.MODE)
    parser.add_argument('--input', help='Input directory', default=Config.INPUT_DIR)
    parser.add_argument('--output', help='Output directory (will be created if it doesn\'t exist)', 
                        default=Config.OUTPUT_DIR)
    
    args = parser.parse_args()
    
    # Override configuration with command-line arguments if provided
    if args.mode:
        Config.MODE = args.mode
    if args.input:
        Config.INPUT_DIR = args.input
    if args.output:
        Config.OUTPUT_DIR = args.output
        
    process_files()
