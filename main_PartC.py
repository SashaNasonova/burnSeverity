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

# Define variables
root = r"E:\burnSeverity\interim_2024\Nfires_Aug13_eval" # root folder
basename = 'interim_burn_severity' # output geodatabase name
fire_year = '2024' #fire year, will be appended to the basename

# Create ouput folders 
outpath = os.path.join(root,'export','data') #root/export/data
firelist = os.listdir(outpath)

filtered_path = os.path.join(root,'export','filtered')

if not os.path.exists(filtered_path):
    os.makedirs(filtered_path)

# Get Spatial Extension
arcpy.CheckOutExtension("Spatial")
arcpy.env.overwriteOutput = True

# For each firenumber, get barc file 
for firenumber in firelist:
    print('Filtering',firenumber)
    barc_path = os.path.join(outpath,firenumber,'barc')
    arcpy.env.workspace = barc_path
    i = getfiles(barc_path,'_msk.tif')[0]
    print('Input BARC raster:',i)
    out_name = Path(i).stem + '_filtered.tif'
    out_raster = os.path.join(filtered_path,out_name)
    print('Output BARC raster:',out_raster)
    barc_filter(i,out_raster)
    

# New dict for sceneIds
d = dict.fromkeys(firelist)

df = pd.DataFrame(data=None,columns=['barc_tif','PRE_FIRE_IMAGE','POST_FIRE_IMAGE'])

# Look for burn severity 
barc_folder = os.path.join(root,'export','filtered')
barc_files = getfiles(barc_folder,'.tif')
print('Filtered:',barc_files)

## Export to vector
arcpy.CheckOutExtension("Spatial")
env.overwriteOutput = True

delivery_dir = os.path.join(root,'export','filtered')
out_gdb_dir = os.path.join(root,'export')

#scenes_csv = os.path.join(outpath,'sceneIds.csv')

gdb_name = basename + '_' + fire_year + '_temp'

#create fgdb to hold outputs:
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
        
    #print(barc_tif)
    print('converting', os.path.basename(barc_tif), 'to polygon')
    fire_number = barc_tif.rsplit('_')[1]
    pre_img = barc_tif.rsplit('_')[2]
    post_img = barc_tif.rsplit('_')[3]
    print(fire_number)
    out_fc = output_gdb + "\\temp_" + fire_number + "_barc_simplify"
    arcpy.conversion.RasterToPolygon(barc_tif, out_fc, "SIMPLIFY", "VALUE", "SINGLE_OUTER_PART", 10000)
    print('    - simplified polygons created')
    
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
    
    #PRE_FIRE_IMAGE
    f = 'PRE_FIRE_IMAGE'
    pre_fire_image_list = data_dict['pre_scenes']
    pre_fire_image = ','.join(pre_fire_image_list)
    
    arcpy.AddField_management(out_fc, f, "TEXT")
    arcpy.CalculateField_management(out_fc, f, "\"" + pre_fire_image + "\"", "PYTHON_9.3") 
    print('    - added pre img to feature class')
    
    #PRE_FIRE_IMAGE_DATE
    f = "PRE_FIRE_IMAGE_DATE"
    pre_img_date_str = pre_img[0:4] + '-' + pre_img[4:6] + '-' + pre_img[6:8]
    pre_img_date = datetime.strptime(pre_img_date_str, '%Y-%m-%d')
    arcpy.AddField_management(out_fc, f, "DATE")
    
    with arcpy.da.UpdateCursor(out_fc, [f]) as rows:
        for row in rows:
            rows.updateRow([pre_img_date])
   
    print('    - added pre img date to feature class')
    
    #POST_FIRE_IMAGE
    f = 'POST_FIRE_IMAGE'
    post_fire_image_list = data_dict['post_scenes']
    post_fire_image = ','.join(post_fire_image_list)
    arcpy.AddField_management(out_fc, f, "TEXT")
    arcpy.CalculateField_management(out_fc, f, "\"" + post_fire_image + "\"", "PYTHON_9.3") 
    print('    - added post img to feature class')

    
    #POST_FIRE_IMAGE_DATE
    f = "POST_FIRE_IMAGE_DATE"
    post_img_date_str = post_img[0:4] + '-' + post_img[4:6] + '-' + post_img[6:8]
    post_img_date = datetime.strptime(post_img_date_str, '%Y-%m-%d')
    arcpy.AddField_management(out_fc, f, "DATE")
    
    with arcpy.da.UpdateCursor(out_fc, [f]) as rows:
        for row in rows:
            rows.updateRow([post_img_date])

    print('    - added post img date to feature class')
    
    #COMMENTS
    f = "COMMENTS"
    arcpy.AddField_management(out_fc, f, "TEXT")

#make empty fc, append all in
env.workspace = output_gdb
env.overwriteOutput = True

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
   
simplify_fc_list = arcpy.ListFeatureClasses('temp*barc_simplify')
print(simplify_fc_list)
arcpy.Append_management(simplify_fc_list, gdb_name, "NO_TEST")
print('appended simplified fcs')
   
#calc burn sev text values
fields = ['gridcode', 'BURN_SEVERITY_RATING']
with arcpy.da.UpdateCursor(gdb_name, fields) as update_cur:
    for row in update_cur:
        #print(row[0]) #for debug
        if row[0] == 0:
            burnsev = 'Unknown'
        if row[0] == 1:
            burnsev = 'Unburned'
        if row[0] == 2:
            burnsev = 'Low'
        if row[0] == 3:
            burnsev = 'Medium'
        if row[0] == 4:
            burnsev = 'High'
        #print(burnsev)
        row[1] = burnsev
        update_cur.updateRow(row)

#calculate areas and lengths automatically
#calculate FEATURE_AREA_SQM, FEATURE_LENGTH_M, AREA_HA

layer = os.path.join(output_gdb, gdb_name)
arcpy.management.CalculateGeometryAttributes(layer, "AREA_HA AREA", '', "HECTARES", proj, "SAME_AS_INPUT")
arcpy.management.CalculateGeometryAttributes(layer, "FEATURE_AREA_SQM AREA", '', "SQUARE_METERS", proj, "SAME_AS_INPUT")
arcpy.management.CalculateGeometryAttributes(layer, "FEATURE_LENGTH_M PERIMETER_LENGTH", "METERS", '', proj, "SAME_AS_INPUT")

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


