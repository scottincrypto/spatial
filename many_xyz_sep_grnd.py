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

#############################################
# this file processes laz files which are in the format of ground and non-ground
#############################################

# todo: change reader to text, add headers, change pipe to classify ground as ground
input_dir = os.path.join("input", "lidar", "2021-12-15")
ground_dir = os.path.join(input_dir, "Ground")
non_ground_dir = os.path.join(input_dir, "Non-Ground")
output_dir = os.path.join("output", "processed", os.path.basename(input_dir))
output_filename = os.path.join(output_dir, "lidar_combined.laz")

print(f"Output directory: {output_dir}")
print(f"Output filename: {output_filename}")


# tile filesnames are bottom left indexed
min_x = 295000
max_x = 297000
min_y = 6425000
max_y = 6428000
step = 1000
excluded_prefix = ['297000_6425000']

# create a list of file prefixes to include
included_prefixes = []

for x in range(min_x, max_x+step, step):
    for y in range(min_y, max_y+step, step):
        # skip the excluded files
        if f"{x}_{y}" in excluded_prefix:
            continue
        # create the file name
        included_prefix = f"{x}_{y}"
        included_prefixes.append(included_prefix)

# [print(f) for f in included_prefixes]


# iterate through both dirs and create a list of file paths
las_files = []
for dirs in [ground_dir, non_ground_dir]:
    for f in os.listdir(dirs):
        # check if the file is a .las file
        if f.endswith('.xyz') and f.startswith(tuple(included_prefixes)):
            # create the file path
            file_path = os.path.join(dirs, f)
            las_files.append(file_path)


# [print(f) for f in las_files]

# Create assign sub-pipelines per non-ground file
# non_ground_pipelines = [
#     [
#         {"type": "readers.las", "filename": path},
#         {"type": "filters.assign", "assignment": "Classification[:]=6"}
#     ]
#     for path in las_files if "Non-Ground" in path
# ]

# # Wrap non-ground sub-pipelines in a filters.merge
# non_ground_merge = {
#     "type": "filters.merge",
#     "pipeline": non_ground_pipelines
# }

# non_ground_pipelines = [
#     [
#         {"type": "readers.las", "filename": path},
#         {"type": "filters.assign", "assignment": "Classification[:]=6"}
#     ]
#     for path in las_files if "Non-Ground" in path
# ]

# # Full pipeline
# full_pipeline = {
#     "pipeline": [
#         non_ground_merge,
#         ground_merge,
#         "merged_output.las"
#     ]
# }

# working pipeline
test_pipe = {
    "pipeline": [
        
        {
            "type": "readers.las",
            "filename": "input\\lidar\\2024-07-29\\Non-Ground\\LAS\\295000_6425000_20240722_MGA56_GDA2020_non-gnd.las"
        },
        {
            "type": "filters.assign",
            "assignment": "Classification[:]=4",
            "tag": "ng_1"
        },
        
        # next reader (ground)
        {
            "type": "readers.las",
            "filename": "input\\lidar\\2024-07-29\\Ground\\LAS\\295000_6425000_20240722_MGA56_GDA2020_gnd.las",
            "tag": "g_1"
        },
        # merge them
        { "type": "filters.merge", "inputs": ["ng_1", "g_1"] },
        # write output
        {
            "type": "writers.las",
            "filename": "output\\processed\\lidar_combined_smoltest.laz"
        }
    ]
}


def generate_tag(prefix, index):
    return f"{prefix}_{index+1}"

def generate_pdal_pipeline(non_ground_files, ground_files, output_file):
    pipeline = []
    input_tags = []

    # Add non-ground files with filters.assign
    for i, ng_file in enumerate(non_ground_files):
        reader_tag = generate_tag("ng", i)
        pipeline.append({
            "type": "readers.las",
            "filename": ng_file,
        })
        pipeline.append({
            "type": "filters.assign",
            "assignment": "Classification[:]=4",
            "tag": reader_tag
        })
        input_tags.append(reader_tag)

    # Add ground files
    for i, g_file in enumerate(ground_files):
        tag = generate_tag("g", i)
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

    # Final writer
    pipeline.append({
        "type": "writers.las",
        "filename": output_file
    })

    return {"pipeline": pipeline}

non_ground_files = [f for f in las_files if "Non-Ground" in f]
ground_files = [f for f in las_files if "Non-Ground" not in f]
pipeline_json = generate_pdal_pipeline(non_ground_files, ground_files, output_filename)

pipe = pipeline_json
print(json.dumps(pipe, indent=4))
p = pdal.Pipeline(json.dumps(pipe))
# run_pipe_with_time(p, streaming=True, chunk_size=10000)