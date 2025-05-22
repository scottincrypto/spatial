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

input_dir = "input\\lidar\\2024-10-04"
output_dir = os.path.join("output", "processed", os.path.basename(input_dir))
output_filename = os.path.join(output_dir, "lidar_combined.laz")

print(f"Output directory: {output_dir}")
print(f"Output filename: {output_filename}")




# iterate through input_dir and create a list of file paths
las_files = []
file_names = []
for f in os.listdir(input_dir):
    # check if the file is a .las file
    if f.endswith('.las'):
        # create the file path
        file_path = os.path.join(input_dir, f)
        las_files.append(file_path)
        file_names.append(f)

[print(f) for f in las_files]

# raise ValueError("stop here")

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
# run_pipe_with_time(p, streaming=True, chunk_size=10000)

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