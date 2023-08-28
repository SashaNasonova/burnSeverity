# -*- coding: utf-8 -*-
"""
Created on Wed Aug  9 13:30:42 2023

Burn Severity Mapping 

Burn Severity Mapping with spaceborne multispectral imagery from Sentinel-2 MSI and Landsat-8/9 OLI Sensors.
The process has been broken down into 4 parts:
    
Part A - Prepare file perimeter vector file
Part B - Burn Severity Product Generation (barc, quicklooks and qa powerpoint)
Part C - Filter and Export 
Part D - Map Generation

This script is focused on Part C and assumes that Part B has been completed and the products have undergone 
quality control.

@author: snasonov
"""

#### Part C
code_loc = r'C:\Dev\git\burnSeverity'

from pathlib import Path
import os, arcpy
import pandas as pd
from datetime import datetime
from arcpy import env

import traceback
import json

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


root = r"C:\Data\Burn_Severity\same_year_2023\G30210" # root folder
dattype = 'S2' #L5,L7,L8,L9,S2
basename = 'provincial_burn_severity'
fire_year = '2023'

##############################################################################
outpath = os.path.join(root,'output',dattype) #root/output
firelist = os.listdir(outpath)

filtered_path = os.path.join(root,'export','filtered')

if not os.path.exists(filtered_path):
    os.makedirs(filtered_path)

arcpy.CheckOutExtension("Spatial")
arcpy.env.overwriteOutput = True

for firenumber in firelist:
    barc_path = os.path.join(outpath,firenumber,'barc')
    i = getfiles(barc_path,'.tif')[0]
    out_name = Path(i).stem + '_filtered.tif'
    out_raster = os.path.join(filtered_path,out_name)
    barc_filter(i,out_raster)
    

#new dict for sceneIds
d = dict.fromkeys(firelist)

df = pd.DataFrame(data=None,columns=['barc_tif','PRE_FIRE_IMAGE','POST_FIRE_IMAGE'])

barc_folder = os.path.join(root,'export','filtered')
barc_files = getfiles(barc_folder,'.tif')

for fire in firelist:
    fire_folder = os.path.join(outpath,fire) 

    barc = [item for item in barc_files if fire in item][0]
    name = Path(barc).stem
    print(name)
    
    #get dates and sensor
    pre_date = name.rsplit('_')[2]
    post_date = name.rsplit('_')[3]
    
    if 'S2' in name:
        sensor = 'S2'
    elif 'L8' in name:
        sensor = 'L8'
    elif 'L9' in name:
        sensor = 'L9'
    elif 'L5' in name:
        sensor = 'L5'
    elif 'L7' in name:
        sensor = 'L7'
    else:
        print('No sensor found!')
    
    # #reformat date for S2 (yymmdd) for landsat it's (yyyy-mm-dd)
    # pre_date_f = pre_date[0:4] + '-' + pre_date[4:6] + '-' + pre_date[6:8]
    # post_date_f = post_date[0:4] + '-' + post_date[4:6] + '-' + post_date[6:8]
    
    # #open pre_sceneMetadata.csv
    # pre_df = pd.read_csv(os.path.join(outpath,fire,'pre_sceneMetadata.csv'))
    # post_df = pd.read_csv(os.path.join(outpath,fire,'post_sceneMetadata.csv'))
    # pre_df['date'] = pre_df['date'].astype(str)
    # post_df['date'] = post_df['date'].astype(str)
    
    # #subset dataframes by date
    # pre_df_sub = pre_df.loc[pre_df['date']==pre_date_f]
    # post_df_sub = post_df.loc[post_df['date']==post_date_f]
    
    # #get PRODUCT_ID for S2 or LANDSAT_SCENE_ID for L8/L9
    # if sensor == 'S2':
    #     pre_scenes = pre_df_sub['PRODUCT_ID'].tolist()
    #     post_scenes = post_df_sub['PRODUCT_ID'].tolist()
    # else:
    #     pre_scenes = pre_df_sub['LANDSAT_SCENE_ID'].tolist()
    #     post_scenes = post_df_sub['LANDSAT_SCENE_ID'].tolist()
    
    # #populate dictionary
    # d[fire]={}
    # d[fire]['barc'] = name
    # d[fire]['pre_scenes'] = pre_scenes
    # d[fire]['post_scenes'] = post_scenes
    
    # #convert list to a comma separated string
    # pre_scenes_str = ','.join(pre_scenes)
    # post_scenes_str = ','.join(post_scenes)
    # d[fire]['pre_scenes_str'] = pre_scenes_str
    # d[fire]['post_scenes_str'] = post_scenes_str
    
    # #append to barc_tif, pre_scenes_str and post_scenes_str to df
    # df_list = [name,pre_scenes_str,post_scenes_str]
    # df.loc[len(df)] = df_list

#write df to csv
#df.to_csv(os.path.join(outpath,'sceneIds.csv'))

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

#load in scenes from csv 
#df =  pd.read_csv(scenes_csv)

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
    metadata_loc = os.path.join(root,'output',dattype,fire_number,'search_params.json')
    with open(metadata_loc, 'r') as json_file:
        data_dict = json.load(json_file)
    
    #PRE_FIRE_IMAGE
    f = 'PRE_FIRE_IMAGE'
    #pre_fire_image = df.loc[df['barc_tif']==barc_tif[:-4]]['PRE_FIRE_IMAGE'].tolist()[0]
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
    #post_fire_image = df.loc[df['barc_tif']==barc_tif[:-4]]['POST_FIRE_IMAGE'].tolist()[0]
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

#copy final layer to a new database
gdb_name_final = basename + '_' + fire_year

#create fgdb to hold outputs:
output_gdb_final = os.path.join(out_gdb_dir, gdb_name_final+'.gdb')
if not arcpy.Exists(output_gdb_final): 
    arcpy.CreateFileGDB_management(out_gdb_dir,gdb_name_final+'.gdb')
    
infile = os.path.join(output_gdb,gdb_name)
outfile = os.path.join(output_gdb_final,gdb_name_final)

arcpy.management.CopyFeatures(infile,outfile)

#delete temps files
#for some reason deleting temporary files doesn't work
# temp_list = arcpy.ListFeatureClasses('temp*')
# for fc in temp_list:
#     print('deleting', fc)
#     arcpy.management.Delete(fc)