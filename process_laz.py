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
root_dir = "input\\rehab"


# iterate through root_dir and create a list of file paths
las_files = []
file_names = []
for f in os.listdir(root_dir):
    # check if the file is a .las file
    if f.endswith('.las'):
        # check if the file is in the excluded files list
        if f in excluded_files:
            continue
        # create the file path
        file_path = os.path.join(root_dir, f)
        las_files.append(file_path)
        file_names.append(f)

[print(f) for f in las_files]

# las_files = []
# file_names = []
# for x in range(min_x, max_x+step, step):
#     for y in range(min_y, max_y+step, step):
#         # skip the excluded files
#         if f"{x}_{y}.las" in excluded_files:
#             continue
#         # create the file name
#         file_name = f"{x}_{y}.las"
#         file_path = os.path.join(root_dir, file_name)
#         las_files.append(file_path)
#         file_names.append(file_name)
        # las_files.add(file_name)

# las_files.remove(os.path.join(root_dir,'295000_6425000.las'))

# [print(f) for f in las_files]
# print(len(las_files))

# single file for testing
# las_files = ['input\\rehab\\296000_6426000.las','input\\rehab\\296000_6427000.las','input\\rehab\\296000_6428000.las']

pipeline_json = {
    "pipeline": []
}

for f in las_files:
    pipeline_json["pipeline"].append({
        "type": "readers.las",
        "filename": f
    })

# add the merge filter
pipeline_json["pipeline"].append({
    "type": "filters.merge"
})

# add the writer
pipeline_json["pipeline"].append({
    "type": "writers.las",
    "filename": output_filename,
    "compression": "laszip"
})

# # add the copc writer
# pipeline_json["pipeline"].append({
#     "type": "writers.copc",
#     "filename": output_filename_copc
# })

print(json.dumps(pipeline_json, indent=4))

p = pdal.Pipeline(json.dumps(pipeline_json))
run_pipe_with_time(p, streaming=True, chunk_size=10000)

# this takes forever - use qgis - loading as a layer auto creates the copc
# # write out to copc
# pipeline_json_copc = {
#     "pipeline": [
#         {
#             "type": "readers.las",
#             "filename": output_filename
#         },
#         {
#             "type": "writers.copc",
#             "filename": output_filename_copc
#         }
#     ]
# }

# p = pdal.Pipeline(json.dumps(pipeline_json_copc))
# run_pipe_with_time(p, streaming=True, chunk_size=10000)