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
import os, shutil
os.chdir(code_loc)

from burnsev_gee import * 
from burnsev_mosaic import *
from burnsev_ql import *

import logging
import traceback

## Define inputs
root = r"C:\Data\Burn_Severity\same_year_2023\K52318" # root folder
fires_shp = os.path.join(root,'vectors','K52318_Aug28.shp')
outpath = os.path.join(root,'output') #root/output

## Define datatype 
dattype = 'S2' #L5,L7,L8,L9,S2
proc ='SR'

## Define shapefile fields
fn = 'FIRE_NUMBE'
preT1 = 'pre_T1'
preT2 = 'pre_T2'
postT1 = 'post_T1'
postT2 = 'post_T2'
areaha = 'FIRE_SIZE_'

## Export alternate quicklooks?
export_alt = True

## Export data?
export_data = False

## Override? 
override = False #True or False

## Optional - override dictionary
if override:
    export_alt = False #don't export alternates
    print('Override selected')
    override = dict(G80223 = {'pre_mosaic': '2022-08-16', 'post_mosaic': '2023-08-13','sensor':'S2'})
    print(override)
    
bc_boundary = r"C:\Data\Datasets\BC_Boundary_Terrestrial_gcs_simplify.shp"

###############################################################################
#create parameter dictionary to feed into barc mapping
opt = {'fn':fn,
       'preT1':preT1,'preT2':preT2,
       'postT1':postT1,'postT2':postT2,
       'dattype':dattype,'areaha':areaha,
       'export_data':export_data,'export_alt':export_alt,
       'override':override}

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
        
#Create alternate directory by sensor
altdir = os.path.join(root,'alt',dattype)   
if not os.path.exists(altdir):
    os.makedirs(altdir)

#Initialize gee 
ee.Initialize()

#open fires shapefile
fires_df = geopandas.read_file(fires_shp)

#list of failed fires 
failed = []

#get list of fires
if override:
    ### Use pre-defined override dictionary
    fireslist = list(override.keys())
    fireslist.sort()
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
        if override:
            print('Overriding, deleting previous outdir')
            #delete qa and outdir folders for the fire, keep alt
            #shutil.rmtree(os.path.join(qcdir,firenumber))
            shutil.rmtree(os.path.join(outdir,firenumber))
            
        #Load in shapefile
        poly_df = fires_df[fires_df[fn] == firenumber]
        outshp = os.path.join(root,'vectors',firenumber+'_temp.shp')
        poly_df.to_file(outshp) #overwrites
        poly = geemap.shp_to_ee(outshp)
        
        #Run BARC
        barc_path,pre_sw_8bit,post_sw_8bit,pre_tc_8bit,post_tc_8bit = barc(fires_df,firenumber,outdir,poly,opt,proc,altdir)
        
        #Create QC folder
        qcdirfirenum = os.path.join(qcdir,firenumber)
        if not os.path.exists(qcdirfirenum):
                os.makedirs(qcdirfirenum)
        
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
        inset_map(bc_boundary,fire_perim,map_ql)
        
        #add stats table
        outpath = os.path.join(outdir,firenumber,'barc_stats.csv')
        df = zonal_barc(barc_path,outshp,outpath)
        
        #Add slide to powerpoint
        add_slide(pptpath,pre_tc_ql,post_tc_ql,barc_ql,map_ql,df)
        add_slide(pptpath,pre_sw_ql,post_sw_ql,barc_ql,map_ql,df)
        
        #Create alternate quicklooks and powerpoints
        if export_alt:
            print('Exporting alternates')
            #Create alt folder
            altdirpre = os.path.join(altdir,firenumber,'pre_png')
            if not os.path.exists(altdirpre):
                    os.makedirs(altdirpre)
                    
            altdirpost = os.path.join(altdir,firenumber,'post_png')
            if not os.path.exists(altdirpost):
                    os.makedirs(altdirpost)
                    
            ###pre    
            ##create images
            folder = os.path.join(altdir,firenumber,'pre_truecolor_8bit_alt')
            ql_3band_batch(folder,outshp,altdirpre)
            
            ##create ppt
            pptpath_alt = os.path.join(altdirpre,firenumber+ '_'+ dattype + '_alt-pre-ppt.pptx')
            create_ppt(pptpath_alt)
            ##add slides
            add_slides_batch(altdirpre,pptpath_alt)
            
            ###post
            folder = os.path.join(altdir,firenumber,'post_truecolor_8bit_alt')
            ql_3band_batch(folder,outshp,altdirpost)
            
            ##create ppt
            pptpath_alt = os.path.join(altdirpost,firenumber+ '_'+ dattype + '_alt-post-ppt.pptx')
            create_ppt(pptpath_alt)
            ##add slides
            add_slides_batch(altdirpost,pptpath_alt)
    
    except Exception as e:
        failed.append(firenumber)
        traceback.print_exc()
        pass

# How many failed?
if len(failed) == 0:
    print('All fires complete')
else:
    print(str(len(failed)) + ' failed')
    print(failed)

