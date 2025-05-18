# imports
import pdal
import json
import os
import time


def run_pipe_with_time(pipeline, streaming=False, chunk_size=10000):
    """
    Run a PDAL pipeline and measure the time taken.
    """
    print("Starting PDAL pipeline execution in streaming mode..." if streaming else "Starting PDAL pipeline execution...")
    start_time = time.time()
    if streaming and pipeline.streamable:
        # Execute the pipeline in streaming mode
        num_points = pipeline.execute_streaming(chunk_size)
    else:
        # Execute the pipeline in normal mode
        num_points = pipeline.execute()
    end_time = time.time()
    elapsed = end_time - start_time
    # print(pipeline.log)
    print(f"Pipeline execution complete. Processed {num_points} points in {elapsed:.2f} seconds.")

# compute the HAG and write to laz and copc files 

# las files many - we don't want the whole lot however. Just stick with the files in the emplacement
# tile filesnames are bottom left indexed
min_x = 295000
max_x = 297000
min_y = 6425000
max_y = 6428000
step = 1000
excluded_files = ['297000_6425000.las']
output_filename = "output\\2025_03_combined.laz"
output_filename_copc = "output\\2025_03_combined.copc.laz"

# root_dir = "L:\\SURVEY\\08 - Projects & Photos\\LiDAR surveys\\2024-2025\\MAR25\\Ground Only (all)\\Clipped_1000m"
root_dir = "intput\\rehab"



las_files = []
file_names = []
for x in range(min_x, max_x+step, step):
    for y in range(min_y, max_y+step, step):
        # skip the excluded files
        if f"{x}_{y}.las" in excluded_files:
            continue
        # create the file name
        file_name = f"{x}_{y}.las"
        file_path = os.path.join(root_dir, file_name)
        las_files.append(file_path)
        file_names.append(file_name)
        # las_files.add(file_name)

# las_files.remove('295000_6425000.las')

# [print(f) for f in las_files]
# print(len(las_files))

# single file for testing
las_files = ['input\\rehab\\296000_6426000.las','input\\rehab\\296000_6427000.las','input\\rehab\\296000_6427000.las']

# First file writes to output directly
print(f"Writing initial file: {las_files[0]}")
init_pipeline = {
    "pipeline": [
        { "type": "readers.las", "filename": las_files[0] },
        { "type": "writers.las", "filename": output_filename, "compression": "laszip" }
    ]
}
# print(json.dumps(init_pipeline, indent=4))
p = pdal.Pipeline(json.dumps(init_pipeline))


run_pipe_with_time(p, streaming=True, chunk_size=10000)


# temporary filename
temp_filename = os.path.join(os.path.dirname(output_filename), "temp.laz")

# Merge subsequent files one-by-one into output
for fpath in las_files[1:]:
    print(f"Merging {fpath} into {output_filename}")
    merge_pipeline = {
        "pipeline": [
            { "type": "readers.las", "filename": output_filename },
            { "type": "readers.las", "filename": fpath },
            { "type": "filters.merge" },
            { "type": "writers.las", "filename": temp_filename, "compression": "laszip" }
        ]
    }
    # print(json.dumps(merge_pipeline, indent=4))
    p = pdal.Pipeline(json.dumps(merge_pipeline))
    run_pipe_with_time(p, streaming=True, chunk_size=10000)

    # remove the output file and rename the temp file
    os.remove(output_filename)
    os.rename(temp_filename, output_filename)
    
    