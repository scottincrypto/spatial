# imports
import pdal
import json
import os
import time

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

root_dir = "L:\\SURVEY\\08 - Projects & Photos\\LiDAR surveys\\2024-2025\\MAR25\\Ground Only (all)\\Clipped_1000m"

las_files = []
for x in range(min_x, max_x+step, step):
    for y in range(min_y, max_y+step, step):
        # skip the excluded files
        if f"{x}_{y}.las" in excluded_files:
            continue
        # create the file name
        file_name = f"{x}_{y}.las"
        file_path = os.path.join(root_dir, file_name)
        las_files.append(file_path)
        # las_files.add(file_name)

# las_files.remove('295000_6425000.las')

# [print(f) for f in las_files]
# print(len(las_files))

# single file for testing
# las_files = 'input\\296000_6426000.las'

# globbed files - pipeline reader can't take a list 
las_files = root_dir + "\\*.las"

# Create a pipeline 
# initialise the pipeline
pipeline_json = {
    "pipeline": []
}

# add the las files to the pipeline
pipeline_json["pipeline"].append({
    "type": "readers.las",
    "filename": las_files
})

# fix the coordinate system if required
# pipeline_json["pipeline"].append({
#     "type": "filters.reprojection", 
#     "in_srs": "EPSG:7856", 
#     "out_srs": "EPSG:7856"
# })

# this input data is already classified, use these


pipeline_json["pipeline"].append({
    "type": "writers.las",
    "filename": output_filename,
})

pipeline_json["pipeline"].append({
    "type": "writers.copc",
    "filename": output_filename_copc,
})

# set threads - reader/writer op seems slightly slower with more threads
# pipeline_json['threads'] = 12

print(pipeline_json )


# Create and execute the pipeline
pipeline = pdal.Pipeline(json.dumps(pipeline_json))





print("Starting PDAL pipeline execution...")
start_time = time.time()

result = pipeline.execute()

end_time = time.time()
elapsed = end_time - start_time
print(f"Pipeline execution complete. Processed {result} points in {elapsed:.2f} seconds.")

