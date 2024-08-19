# -*- coding: utf-8 -*-
"""
Burn Severity Mapping 

Burn Severity Mapping with spaceborne multispectral imagery from Sentinel-2 MSI and Landsat-8/9 OLI Sensors.
The process has been broken down into 4 parts:
    
Part A - Prepare file perimeter vector file
Part B - Burn Severity Product Generation (barc, quicklooks and qa powerpoint)
Part C - Filter and Export 
Part D - Map Generation

This script is focused on Part B and assumes that the vector file created in Part A has appropriate text fields.
Especially pre_T1, pre_T2, post_T1, and post_T2

@author: snasonov
"""

#### Part B
code_loc = r'C:\Dev\git\burnSeverity'

from pathlib import Path
import os, shutil,time,geopandas
os.chdir(code_loc)

from burnsev_gee import * 
from burnsev_ql import *

import logging
import traceback

import sys

## Check if there are sys arguments
if len(sys.argv) > 1:
    fires_poly = sys.argv[1]
    dattype = sys.argv[2]
    root = sys.argv[3]
else:
    fires_poly = 'for_nat.shp'
    dattype = 'L5' #L5,L7,L8,L9,S2
    root = r"E:\burnSeverity\for_nat" # root folder


## Define inputs
fires_shp = os.path.join(root,'vectors',fires_poly)
outpath = os.path.join(root,'output') #root/output

## Define proc type 
proc ='SR'

## Define shapefile fields
fn = 'FIRE_NUMBE'
preT1 = 'pre_T1'
preT2 = 'pre_T2'
postT1 = 'post_T1'
postT2 = 'post_T2'
areaha = 'FIRE_SIZE_'

#Check for available imagery only?
evalOnly = True

## Debug?
debug = False
debug_list = ['N71148']

## Mask clouds?
mask_clouds = False

## Export alternate quicklooks?
preflag = True #export pre-image alternates
postflag = True #export post-image alternates 

## How to select post-fire image? Based on AOT (True, default) or most recent?
postAOT = True

## Export data?
export_data = False

## Override? 
override = False #True or False
overridedict = dict(C50054 = {'pre_mosaic': '2009-07-29', 
                              'post_mosaic': '2011-08-04',
                              'sensor':'L5'})

###############################################################################
## If eval only, set everything to false
if evalOnly:
    preflag = False
    postflag = False 
    mask_clouds = False
    postAOT = False
    export_data = False
    override = False #True or False

## Optional - override dictionary
if override:
    preflag = False
    postflag = False 
    
    print('Override selected')
    override = overridedict
    print(override)
    
bc_boundary = r"C:\Data\Datasets\BC_Boundary_Terrestrial_gcs_simplify.shp"

## Print out parameters 
print('Parameters selected')
print('Debug: ', debug)
print('Eval Only: ', evalOnly)
if debug:
    print('Debug fire list: ',debug_list)
print('Override: ', override)
print('Mask Clouds: ', mask_clouds)
print('Export pre-fire alternates: ',preflag)
print('Export post-fire alternates: ', postflag)

if postAOT: 
    print('Post-fire image selection process: AOT/Scene Cloud Cover')
else:
    print('Post-fire image selection process: Most Recent')

print('Exporting data: ',export_data)

time.sleep(10)

###############################################################################
#create parameter dictionary to feed into barc mapping
opt = {'fn':fn,
       'preT1':preT1,'preT2':preT2,
       'postT1':postT1,'postT2':postT2,
       'dattype':dattype,'areaha':areaha,
       'postAOT':postAOT,
       'export_data':export_data,
       'mask_clouds':mask_clouds,
       'override':override,
       'evalOnly':evalOnly}

#Create output directory
if not os.path.exists(outpath):
    os.makedirs(outpath)

#Create output directory by sensor
outdir = os.path.join(outpath,dattype)
if not os.path.exists(outdir):
        os.makedirs(outdir)

#Create QC directory by sensor
qcdir = os.path.join(root,'QC',dattype)
if not os.path.exists(qcdir):
        os.makedirs(qcdir)
        
#Initialize gee 
try:    
    print('Using test account')
    ee.Initialize(project='burn-severity-2024')
except:
    print('Using operational account')
    ee.Initialize(project='rsfaibfall2024')

#open fires shapefile
fires_df = geopandas.read_file(fires_shp)

#list of failed fires 
failed = []

#get list of fires
if override:
    ### Use pre-defined override dictionary
    fireslist = list(override.keys())
    fireslist.sort()
elif debug:
    fireslist = debug_list  
else:
    fireslist = fires_df[fn].tolist()
    fireslist.sort()

#For QC: create an empty powerpoint if one doesn't exist
pptpath = os.path.join(qcdir,'qc-ppt.pptx')

if not os.path.exists(pptpath):
    create_ppt(pptpath)

### For each fire run burn severity mapping, mosaic, and create quicklook 
for firenumber in fireslist:
    try:
        print(firenumber)
        out = os.path.join(outdir,firenumber)
        
        #Load in shapefile
        poly_df = fires_df[fires_df[fn] == firenumber]
        outshp = os.path.join(root,'vectors',firenumber+'_temp.shp')
        poly_df.to_file(outshp) #overwrites
        poly = geemap.shp_to_ee(outshp)
        
        #Run BARC
        if evalOnly:
            barc_path,pre_sw_8bit,post_sw_8bit,pre_tc_8bit,post_tc_8bit,col_list = barc(fires_df,firenumber,outdir,poly,opt,proc)
        else:
            if os.path.exists(out):
                shutil.rmtree(out)
                print('Deleted previous outdir')
            
            #Create QC folder
            qcdirfirenum = os.path.join(qcdir,firenumber)
            if os.path.exists(qcdirfirenum):
                shutil.rmtree(qcdirfirenum)
                os.makedirs(qcdirfirenum)
                print('Deleted previous qc folder')
            else:
                os.makedirs(qcdirfirenum)
            
            barc_path,pre_sw_8bit,post_sw_8bit,pre_tc_8bit,post_tc_8bit,col_list = barc(fires_df,firenumber,outdir,poly,opt,proc)
            print(barc_path)
            print(pre_sw_8bit)
            print(post_sw_8bit)
            print(pre_tc_8bit)
            print(post_tc_8bit)
            
            #Generate quicklook
            #truecolor
            name = Path(pre_tc_8bit).stem + '.png'
            pre_tc_ql = os.path.join(qcdir,firenumber,name)
            ql_3band(outshp,pre_tc_8bit,pre_tc_ql)
            
            name = Path(post_tc_8bit).stem + '.png'
            post_tc_ql = os.path.join(qcdir,firenumber,name)
            ql_3band(outshp,post_tc_8bit,post_tc_ql)
            
            #swir 
            name = Path(pre_sw_8bit).stem + '.png'
            pre_sw_ql = os.path.join(qcdir,firenumber,name)
            ql_3band(outshp,pre_sw_8bit,pre_sw_ql)
            
            name = Path(post_sw_8bit).stem + '.png'
            post_sw_ql = os.path.join(qcdir,firenumber,name)
            ql_3band(outshp,post_sw_8bit,post_sw_ql)
        
            #barc
            name = Path(barc_path).stem + '.png'
            barc_ql = os.path.join(qcdir,firenumber,name)
            ql_barc(outshp,barc_path,post_tc_8bit,barc_ql)
            
            #add location map
            name = firenumber + '_locmap.png'
            map_ql = os.path.join(qcdir,firenumber,name)
          
            fire_perim = os.path.join(root,'vectors',firenumber+'_temp_gcs.shp')
            if os.path.isfile(fire_perim):
                pass
            else:
                fire_perim = os.path.join(root,'vectors',firenumber+'_temp.shp')
            
            inset_map(bc_boundary,fire_perim,map_ql)
            
            #add stats table
            outpath = os.path.join(outdir,firenumber,'barc_stats.csv')
            df = zonal_barc(barc_path,outshp,outpath)
            
            #Add slide to powerpoint
            add_slide(pptpath,pre_tc_ql,post_tc_ql,barc_ql,map_ql,df)
            add_slide(pptpath,pre_sw_ql,post_sw_ql,barc_ql,map_ql,df)
            
            ### Create alternate quicklooks and powerpoints
            #Create output folder
            if preflag or postflag:
                altdir = os.path.join(root,'alt',dattype,firenumber)
                if os.path.exists(altdir):
                    shutil.rmtree(altdir)
                    os.makedirs(altdir)
                    print('Deleted previous alt folder')
                else:
                    os.makedirs(altdir)
            
            if preflag:            
                imgtype = 'pre'
                print('Exporting pre-fire alternates')
        
                output_folder = export_alternates(altdir,col_list[0],dattype,fires_df,poly,opt,firenumber,imgtype)
                altdirpng = output_folder + '_png'
                if not os.path.exists(altdirpng):
                    os.makedirs(altdirpng)
                
                #Create ppt
                pptpath_alt = os.path.join(altdirpng,firenumber+ '_'+ dattype + '_alt-pre-ppt.pptx')
                create_ppt(pptpath_alt)
                
                ql_3band_batch(output_folder,outshp,altdirpng)
                
                ##add slides
                add_slides_batch(altdirpng,pptpath_alt)
            
            if postflag:
                imgtype = 'post'
                print('Exporting post-fire alternates')
                
                output_folder = export_alternates(altdir,col_list[1],dattype,fires_df,poly,opt,firenumber,imgtype)
                altdirpng = output_folder + '_png'
                if not os.path.exists(altdirpng):
                    os.makedirs(altdirpng)
            
                #Create ppt
                pptpath_alt = os.path.join(altdir,firenumber+ '_'+ dattype + '_alt-post-ppt.pptx')
                create_ppt(pptpath_alt)
            
                ql_3band_batch(output_folder,outshp,altdirpng)
                
                ##add slides
                add_slides_batch(altdirpng,pptpath_alt)
                
        ### check for temp shp files and delete
        print('deleting temp shapefiles')
        shp1 = os.path.join(root,'vectors',firenumber+'_temp_gcs.shp')
        if os.path.isfile(shp1):
            os.remove(os.path.join(root,'vectors',firenumber+'_temp_gcs.shp'))
            os.remove(os.path.join(root,'vectors',firenumber+'_temp_gcs.cpg'))
            os.remove(os.path.join(root,'vectors',firenumber+'_temp_gcs.dbf'))
            os.remove(os.path.join(root,'vectors',firenumber+'_temp_gcs.prj'))
            os.remove(os.path.join(root,'vectors',firenumber+'_temp_gcs.shx'))
            
        
        shp2 = os.path.join(root,'vectors',firenumber+'_temp.shp')
        if os.path.isfile(shp2):    
            #delete shp all files
            os.remove(os.path.join(root,'vectors',firenumber+'_temp.shp'))
            os.remove(os.path.join(root,'vectors',firenumber+'_temp.cpg'))
            os.remove(os.path.join(root,'vectors',firenumber+'_temp.dbf'))
            os.remove(os.path.join(root,'vectors',firenumber+'_temp.prj'))
            os.remove(os.path.join(root,'vectors',firenumber+'_temp.shx'))
                
    except Exception as e:
        failed.append(firenumber)
        traceback.print_exc()
        err = ''.join(traceback.format_exc())
        params = os.path.join(outdir,firenumber,'errors.txt')
        with open(params, 'w') as f:
             f.write(f'\n{err}')
        
        ### check for temp shp files and delete
        shp1 = os.path.join(root,'vectors',firenumber+'_temp_gcs.shp')
        if os.path.isfile(shp1):
            os.remove(os.path.join(root,'vectors',firenumber+'_temp_gcs.shp'))
            os.remove(os.path.join(root,'vectors',firenumber+'_temp_gcs.cpg'))
            os.remove(os.path.join(root,'vectors',firenumber+'_temp_gcs.dbf'))
            os.remove(os.path.join(root,'vectors',firenumber+'_temp_gcs.prj'))
            os.remove(os.path.join(root,'vectors',firenumber+'_temp_gcs.shx'))
            
        
        shp2 = os.path.join(root,'vectors',firenumber+'_temp.shp')
        if os.path.isfile(shp2):    
            #delete shp all files
            os.remove(os.path.join(root,'vectors',firenumber+'_temp.shp'))
            os.remove(os.path.join(root,'vectors',firenumber+'_temp.cpg'))
            os.remove(os.path.join(root,'vectors',firenumber+'_temp.dbf'))
            os.remove(os.path.join(root,'vectors',firenumber+'_temp.prj'))
            os.remove(os.path.join(root,'vectors',firenumber+'_temp.shx'))
            
        pass

# How many failed?
if len(failed) == 0:
    print('All fires complete')
else:
    print(str(len(failed)) + ' failed')
    print(failed)

