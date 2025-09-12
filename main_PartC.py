## Originally developed by Carole Mahood.
# Import libraries
from pathlib import Path
import os, arcpy
import pandas as pd
from datetime import datetime
from arcpy import env

import traceback
import json

# Import functions
def barc_filter_waternull(barc_path,out_raster):
    ##Set water pixels to NA - test this option with Dave 
    barc = arcpy.sa.Raster(barc_path)
    barc_nonan = arcpy.sa.SetNull(barc,barc,"VALUE=5")

    #Group and smooth
    region_grouped_raster = "bRegGrp"
    arcpy.gp.RegionGroup_sa(barc_nonan, region_grouped_raster, "FOUR", "WITHIN", "ADD_LINK", "")

    nulled_raster = "Nulled"
    arcpy.gp.SetNull_sa(region_grouped_raster, region_grouped_raster, nulled_raster, "COUNT < 10")
    nibbled_raster = "Nibbled"
    arcpy.gp.Nibble_sa(barc_nonan, nulled_raster, nibbled_raster, "DATA_ONLY")

    #Set water back to 5(unburned)
    out_filtered = arcpy.sa.Con(barc==5,barc,nibbled_raster)
    out_filtered.save(out_raster)

def barc_filter(reclassed_raster,out_raster):
	region_grouped_raster = "bRegGrp"
	arcpy.gp.RegionGroup_sa(reclassed_raster, region_grouped_raster, "FOUR", "WITHIN", "ADD_LINK", "")

	nulled_raster = "Nulled"
	arcpy.gp.SetNull_sa(region_grouped_raster, region_grouped_raster, nulled_raster, "COUNT < 10")
	arcpy.gp.Nibble_sa(reclassed_raster, nulled_raster, out_raster, "DATA_ONLY")

def getfiles(d,ext):
    paths = []
    for file in os.listdir(d):
        if file.endswith(ext):
            paths.append(os.path.join(d, file))
    return(paths)

def getbarc_notclipped(d,ext):
    paths = []
    for file in os.listdir(d):
        if file.endswith(ext) and not file.endswith("_clip"+ext):
            paths.append(os.path.join(d, file))
    return(paths)     

def water_masking(barc_raster, water_layer):

    barc_raster_wmsk = barc_raster.rsplit('.')[0] + '_wmasked.tif'
    print(barc_raster_wmsk)

    try:
        arcpy.BuildRasterAttributeTable_management(barc_raster, "OVERWRITE")
    except Exception:
        try:
            arcpy.BuildRasterAttributeTable_management(barc_raster)
        except Exception:
            pass

    # Skip if 5 already present
    values = [i[0] for i in arcpy.da.SearchCursor(barc_raster, "Value")]
    if 5 in values:
        print('Water masking already complete. Exiting.')
        return barc_raster

    if not os.path.exists(water_layer): 
        print('Water layer does not exist. Exiting.')
        return barc_raster

    print('Water layer exists. Continuing.')
    try:
        # Rasterize water directly into BARC extent/alignment
        out_water_rast = barc_raster.rsplit('.')[0] + '_water.tif'
        with arcpy.EnvManager(snapRaster=barc_raster, extent=barc_raster, cellSize=barc_raster):
            arcpy.conversion.PolygonToRaster(
                in_features=water_layer,
                value_field="water", #doesnt really matter what field
                out_rasterdataset=out_water_rast,
                cell_assignment="CELL_CENTER",
                priority_field="NONE",
                cellsize=barc_raster
            )

        # Create mask where water exists
        mask = (~arcpy.sa.IsNull(barc_raster)) & (~arcpy.sa.IsNull(out_water_rast))

        # Apply mask: set 5 where water, keep original elsewhere
        barc = arcpy.sa.Raster(barc_raster)
        masked_raster = arcpy.sa.Con(mask, 5, barc)
        print(barc_raster_wmsk)
        masked_raster.save(barc_raster_wmsk)

        # Clean up temp water raster (optional)
        try:
            arcpy.management.Delete(out_water_rast)
        except Exception:
            pass

        print('Water masking successful.')
        return barc_raster_wmsk

    except Exception as e:
        print("Error: " + str(e))
        print('Water masking failed. Check error.')
        return barc_raster


# Define variables
root = r"\\spatialfiles2.bcgov\Work\FOR\VIC\HTS\INV\WorkArea\pmarczak\burnseverity" # root folder
basename = 'one_year_post' # output geodatabase name
fire_year = '2024' #fire year, will be appended to the basename

# Load in water layer from objectstorage
water_layer = r"\\objectstore2.nrs.bcgov\RSImgShare\water\vector\s2_bc_2022JulAug_2023JulAug_2024JulAug_bcalb_10m_water_Province.shp"

# Create ouput folders 
outpath = os.path.join(root,'export','data') #root/export/data

firelist = os.listdir(outpath)

filtered_path = os.path.join(root,'export','filtered')

if not os.path.exists(filtered_path):
    os.makedirs(filtered_path)

arcpy.CheckOutExtension("Spatial")
arcpy.env.overwriteOutput = True
arcpy.env.parallelProcessingFactor = "100%"
arcpy.env.compression = "LZ77"
arcpy.env.pyramid = "PYRAMIDS"


# For each firenumber, get barc file 
# for firenumber in firelist:
#     if firenumber in ("")
#     print('Filtering',firenumber)
#     barc_path = os.path.join(outpath,firenumber,'barc')
#     arcpy.env.workspace = barc_path
#     print("line 149", firenumber)
#     #i = getfiles(barc_path,'_clip.tif')[0]
#     i_full = getbarc_notclipped(barc_path,'.tif')[0]
#     # BuildRasterAttributeTable_management requires FILENAME not PATHNAME
#     #therefore input i should be tif name only
#     i_name = os.path.basename(i_full)
#     print('Masking water, setting water pixels to 5')
#     ii = water_masking(i_name,water_layer)
#     print('Input BARC raster:',i_name) #input is i for water masking, output is ii
#     print('Output water-masked BARC raster', ii) #output after water masking
#     out_name = Path(ii).stem + '_filtered.tif'
#     out_raster = os.path.join(filtered_path,out_name)
#     print('Output BARC raster:',out_raster)
#     barc_filter(ii,out_raster)
    

# # New dict for sceneIds
# d = dict.fromkeys(firelist)

# df = pd.DataFrame(data=None,columns=['barc_tif','PRE_FIRE_IMAGE','POST_FIRE_IMAGE'])

# Look for burn severity 
barc_folder = os.path.join(root,'export','filtered')
barc_files = getfiles(barc_folder,'.tif')
print('Filtered:',barc_files)

## Export to vector
arcpy.CheckOutExtension("Spatial")
env.overwriteOutput = True

delivery_dir = os.path.join(root,'export','filtered')
out_gdb_dir = os.path.join(root,'export')

# #scenes_csv = os.path.join(outpath,'sceneIds.csv')

gdb_name = basename + '_' + fire_year + '_temp'

# #create fgdb to hold outputs:
output_gdb = os.path.join(out_gdb_dir, gdb_name+'.gdb')
if not arcpy.Exists(output_gdb): 
    arcpy.CreateFileGDB_management(out_gdb_dir,gdb_name+'.gdb')

#get list of fires:
env.workspace = delivery_dir
barc_list = arcpy.ListRasters('*.tif')
barc_list.sort()
        
print(barc_list)

#expects barc_tif in the following format (BARC_C52648_20220910_20221030_S2_filtered.tif) 
for barc_tif in barc_list:
    print('converting', os.path.basename(barc_tif), 'to polygon')
    fire_number = barc_tif.rsplit('_')[1]
    pre_img = barc_tif.rsplit('_')[2]
    post_img = barc_tif.rsplit('_')[3]
    print(fire_number)
    out_fc_temp = output_gdb + "\\temp_" + fire_number + "_barc_simplify"
    arcpy.conversion.RasterToPolygon(barc_tif, out_fc_temp, "SIMPLIFY", "VALUE", "SINGLE_OUTER_PART", 10000)
    print('    - simplified polygons created')

    #get perim path
    perim = os.path.join(root,'export','data',fire_number,'vectors',fire_number+'.shp')
    print(perim)
    out_fc = output_gdb + "\\temp_" + fire_number + "_barc_simplify_clip"
    arcpy.analysis.Clip(in_features=out_fc_temp,clip_features=perim,out_feature_class=out_fc,cluster_tolerance=None)
    print('    - clipping to fire perimeter')

    #FIRE_NUMBER
    f = 'FIRE_NUMBER'
    arcpy.AddField_management(out_fc, f, "TEXT")
    arcpy.CalculateField_management(out_fc, f, "\"" + fire_number + "\"", "PYTHON_9.3")
    print('    - added fire number to feature class')
    
    #FIRE_YEAR
    f = 'FIRE_YEAR'
    arcpy.AddField_management(out_fc, f, "TEXT")
    arcpy.CalculateField_management(out_fc, f, "\"" + fire_year + "\"", "PYTHON_9.3") 
    print('    - added fire_year to feature class')
    
    #open json
    metadata_loc = os.path.join(root,'export','data',fire_number,'search_params.json')
    with open(metadata_loc, 'r') as json_file:
        data_dict = json.load(json_file)
    
   # PRE_FIRE_IMAGE (list -> CSV)
    arcpy.AddField_management(out_fc, "PRE_FIRE_IMAGE", "TEXT")
    pre_fire_image = ",".join(data_dict.get('pre_scenes', []))
    arcpy.management.CalculateField(out_fc, "PRE_FIRE_IMAGE", f"'{pre_fire_image}'", "PYTHON3")
    print('    - added pre img to feature class')

    # PRE_FIRE_IMAGE_DATE (CalculateField once for all rows)
    pre_img_date_str = f"{pre_img[0:4]}-{pre_img[4:6]}-{pre_img[6:8]}"
    pre_y, pre_m, pre_d = int(pre_img[0:4]), int(pre_img[4:6]), int(pre_img[6:8])
    arcpy.AddField_management(out_fc, "PRE_FIRE_IMAGE_DATE", "DATE")
    arcpy.management.CalculateField(
        out_fc, "PRE_FIRE_IMAGE_DATE",
        f"datetime.datetime({pre_y},{pre_m},{pre_d})",
        "PYTHON3", code_block="import datetime" )
    print('    - added pre img date to feature class')
    
    # POST_FIRE_IMAGE (list -> CSV)
    arcpy.AddField_management(out_fc, "POST_FIRE_IMAGE", "TEXT")
    post_fire_image = ",".join(data_dict.get('post_scenes', []))
    arcpy.management.CalculateField(out_fc, "POST_FIRE_IMAGE", f"'{post_fire_image}'", "PYTHON3")
    print('    - added post img to feature class')

    # POST_FIRE_IMAGE_DATE
    post_y, post_m, post_d = int(post_img[0:4]), int(post_img[4:6]), int(post_img[6:8])
    arcpy.AddField_management(out_fc, "POST_FIRE_IMAGE_DATE", "DATE")
    arcpy.management.CalculateField(
        out_fc, "POST_FIRE_IMAGE_DATE",
        f"datetime.datetime({post_y},{post_m},{post_d})",
        "PYTHON3", code_block="import datetime"
    )

    print('    - added post img date to feature class')
    
    #COMMENTS
    f = "COMMENTS"
    arcpy.AddField_management(out_fc, f, "TEXT")

#make empty fc, append all in
env.workspace = output_gdb
env.overwriteOutput = True

# Set tolerances, needed for BCGW
env.XYTolerance = "0.001 Meters"
env.XYResolution = "0.0001 Meters"

proj = 'PROJCS["NAD_1983_BC_Environment_Albers",GEOGCS["GCS_North_American_1983",DATUM["D_North_American_1983",SPHEROID["GRS_1980",6378137.0,298.257222101]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]],PROJECTION["Albers"],PARAMETER["False_Easting",1000000.0],PARAMETER["False_Northing",0.0],PARAMETER["Central_Meridian",-126.0],PARAMETER["Standard_Parallel_1",50.0],PARAMETER["Standard_Parallel_2",58.5],PARAMETER["Latitude_Of_Origin",45.0],UNIT["Meter",1.0]];-13239300 -8610100 316279566.226605;-100000 10000;-100000 10000;0.001;0.001;0.001;IsHighPrecision'

arcpy.CreateFeatureclass_management(output_gdb, gdb_name,'POLYGON',None,"DISABLED","DISABLED",proj)
arcpy.AddField_management(gdb_name, "FIRE_NUMBER", "TEXT")
arcpy.AddField_management(gdb_name, "FIRE_YEAR", "TEXT")
arcpy.AddField_management(gdb_name, 'BURN_SEVERITY_RATING', 'TEXT')
arcpy.AddField_management(gdb_name, 'PRE_FIRE_IMAGE', 'TEXT')
arcpy.AddField_management(gdb_name, 'PRE_FIRE_IMAGE_DATE', 'DATE')
arcpy.AddField_management(gdb_name, 'POST_FIRE_IMAGE', 'TEXT')
arcpy.AddField_management(gdb_name, 'POST_FIRE_IMAGE_DATE', 'DATE')
arcpy.AddField_management(gdb_name, 'COMMENTS', 'TEXT')
arcpy.AddField_management(gdb_name, 'gridcode', 'SHORT')
   
simplify_fc_list = arcpy.ListFeatureClasses('temp*barc_simplify_clip')
print(simplify_fc_list)
arcpy.Append_management(simplify_fc_list, gdb_name, "NO_TEST")
print('appended simplified fcs')
   
#calc burn sev text values
#Map gridcode -> burn severity via CalculateField (faster than UpdateCursor)
mapping_code = {
    0: "Unknown",
    1: "Unburned",
    2: "Low",
    3: "Medium",
    4: "High",
    5: "Unburned"
}
arcpy.management.CalculateField(
    gdb_name, "BURN_SEVERITY_RATING",
    "mapping.get(!gridcode!, 'Unknown')",
    "PYTHON3",
    code_block=f"mapping={mapping_code}"
)
arcpy.management.CalculateField(
    gdb_name, "COMMENTS",
    "'Satellite-derived water polygon' if !gridcode! == 5 else None",
    "PYTHON3"
)

#calculate areas and lengths automatically
#calculate FEATURE_AREA_SQM, FEATURE_LENGTH_M, AREA_HA

layer = os.path.join(output_gdb, gdb_name)
geom_fields = [[ "FEATURE_AREA_SQM", "AREA" ], [ "FEATURE_LENGTH_M", "PERIMETER_LENGTH" ]]
arcpy.management.CalculateGeometryAttributes(
    gdb_name,
    geom_fields,
    length_unit="METERS",
    area_unit="SQUARE_METERS",
    coordinate_system=proj)

geom_fields_ha = [["AREA_HA","AREA"]]
arcpy.management.CalculateGeometryAttributes(
    layer,
    geom_fields_ha,
    area_unit="HECTARES",
    coordinate_system=proj
)

# Run a topology check and fix any errors
arcpy.management.CheckGeometry(
    in_features=layer,
    out_table=os.path.join(output_gdb,"geom_check_ogc"),
    validation_method="OGC"
)

## Run repair
arcpy.management.RepairGeometry(
    in_features=layer,
    delete_null="DELETE_NULL",
    validation_method="OGC"
)

print('Creating final geodatabase')

#copy final layer to a new database
gdb_name_final = basename + '_' + fire_year

#create fgdb to hold outputs:
output_gdb_final = os.path.join(out_gdb_dir, gdb_name_final+'.gdb')
if not arcpy.Exists(output_gdb_final): 
    arcpy.CreateFileGDB_management(out_gdb_dir,gdb_name_final+'.gdb')
    
infile = layer
outfile = os.path.join(output_gdb_final,gdb_name_final)

# Created a temp database because I couldn't delete gridcode field in place
arcpy.management.CopyFeatures(infile,outfile)
arcpy.DeleteField_management(outfile,["gridcode"]) #delete gridcode field

print('Processing complete')


