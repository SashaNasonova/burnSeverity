# -*- coding: utf-8 -*-
"""
Created on Thu Aug 11 09:55:16 2022

@author: snasonov
"""

#loop through tiles and mosaic

import os
from osgeo import gdal

def getfiles(d,ext):
    paths = []
    for file in os.listdir(d):
        if file.endswith(ext):
            paths.append(os.path.join(d, file))
    return(paths) 


def mosaic_rasters(rasterlist,outpath):
    opts = gdal.WarpOptions(format='GTiff')
    gdal.Warp(outpath,rasterlist)
    
def mosaic(outdir,firenumber):
    print('Mosaicking')
    print(firenumber) 
    ##### pre true color
    t1t = os.path.join(outdir,firenumber,'pre_truecolor')
    t1t_files = getfiles(t1t,'.tif')
    
    #out filename
    base = '_'.join(t1t_files[0].rsplit('_')[0:-1]) 
    outfilename = base + '_mosaic.tif'
    pre_tc_path = outfilename
    
    mosaic_rasters(t1t_files,outfilename)
    
    # ##### post true color
    t2t = os.path.join(outdir,firenumber,'post_truecolor')
    t2t_files = getfiles(t2t,'.tif')
    
    #out filename
    base = '_'.join(t2t_files[0].rsplit('_')[0:-1]) 
    outfilename = base + '_mosaic.tif'
    post_tc_path = outfilename
    
    mosaic_rasters(t2t_files,outfilename)
    
    ##### pre swir
    t1s = os.path.join(outdir,firenumber,'pre_swir')
    t1s_files = getfiles(t1s,'.tif')
    
    #out filename
    base = '_'.join(t1s_files[0].rsplit('_')[0:-1]) 
    outfilename = base + '_mosaic.tif'
    
    mosaic_rasters(t1s_files,outfilename)

    # ##### post swir
    t2s = os.path.join(outdir,firenumber,'post_swir')
    t2s_files = getfiles(t2s,'.tif')
    
    #out filename
    base = '_'.join(t2s_files[0].rsplit('_')[0:-1]) 
    outfilename = base + '_mosaic.tif'
    
    mosaic_rasters(t2s_files,outfilename)
    
    ##### dnbr
    t1t = os.path.join(outdir,firenumber,'dnbr')
    t1t_files = getfiles(t1t,'.tif')
    
    #out filename
    base = '_'.join(t1t_files[0].rsplit('_')[0:-1]) 
    outfilename = base + '_mosaic.tif'
    
    mosaic_rasters(t1t_files,outfilename)
    
    ##### dnbr_scaled
    t1t = os.path.join(outdir,firenumber,'dnbr_scaled')
    t1t_files = getfiles(t1t,'.tif')
    
    #out filename
    base = '_'.join(t1t_files[0].rsplit('_')[0:-1]) 
    outfilename = base + '_mosaic.tif'
    
    mosaic_rasters(t1t_files,outfilename)
    
    # ##### pre_nbr
    # t1t = os.path.join(f,fire,'pre_nbr')
    # t1t_files = getfiles(t1t,'.tif')
    
    # #out filename
    # base = '_'.join(t1t_files[0].rsplit('_')[0:-1]) 
    # outfilename = base + '_mosaic.tif'
    
    # mosaic_rasters(t1t_files,outfilename)
    
    # ##### post_nbr
    # t1t = os.path.join(f,fire,'post_nbr')
    # t1t_files = getfiles(t1t,'.tif')
    
    # #out filename
    # base = '_'.join(t1t_files[0].rsplit('_')[0:-1]) 
    # outfilename = base + '_mosaic.tif'
    
    # mosaic_rasters(t1t_files,outfilename)
    
    return(pre_tc_path,post_tc_path)
    
    
    
    
    
    
    
    
    
    
    
    