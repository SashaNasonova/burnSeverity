# -*- coding: utf-8 -*-
"""
Created on Fri Aug 11 11:56:30 2023

@author: snasonov
"""

"""
Create a truecolor or falsecolor, cloud-masked 8-bit RGB mosaic from Sentinel-2 Surface Reflectance Data.
https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S2_SR_HARMONIZED#description
Relies on the s2cloudless dataset: https://developers.google.com/earth-engine/tutorials/community/sentinel-2-s2cloudless

Quarters:
q1: Jan 1 - Mar 30
q2: Apr 1 - Jun 30
q3: Jul 1 - Sept 30
q4: Oct 1 - Dec 31

"""

#Parameters
area_name = 'test' # 'bc' or anything else

if area_name == 'bc':
    p = r"C:\Data\Datasets\WHSE_ADMIN_BOUNDARIES_ADM_NR_AREAS_SP_dissolved.shp"
else:
    p = r"C:\Data\Burn_Severity\same_year_2023\donnie_creek\vectors\donnie_creek_aug10.shp"


q = 'custom' #q1, q2, q3, q4 or custom
comp = 'tc' #tc (truecolor) or fc (falsecolor)
year = '2023'

##for custom define dates "yyyy-mm-dd"
if q == 'custom':
    t1 = '2023-07-25'
    t2 = '2023-08-10'

# Output parameters
scale = 20 #in meters
proj = 'EPSG:3005' #epsg code
outfolder = 'mosaic_' + year + '_' + q #output google drive folder

import ee
import geemap
import os
import math
from osgeo import gdal

def getfiles(d,ext):
    paths = []
    for file in os.listdir(d):
        if file.endswith(ext):
            paths.append(os.path.join(d, file))
    return(paths) 

###Cloud masking functions for s2cloudless 
###(https://developers.google.com/earth-engine/tutorials/community/sentinel-2-s2cloudless)

# Get surface reflectance data and corresponding s2cloudless dataset, merge
def get_s2_sr_cld_col(aoi, start_date, end_date):
    # Import and filter S2 SR.
    s2_sr_col = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
        .filterBounds(aoi)
        .filterDate(start_date, end_date)
        .filter(ee.Filter.lte('CLOUDY_PIXEL_PERCENTAGE', CLOUD_FILTER)))

    # Import and filter s2cloudless.
    s2_cloudless_col = (ee.ImageCollection('COPERNICUS/S2_CLOUD_PROBABILITY')
                        .filterBounds(aoi)
                        .filterDate(start_date, end_date))

    # Join the filtered s2cloudless collection to the SR collection by the 'system:index' property.
    return ee.ImageCollection(ee.Join.saveFirst('s2cloudless').apply(**{
        'primary': s2_sr_col,
        'secondary': s2_cloudless_col,
        'condition': ee.Filter.equals(**{
            'leftField': 'system:index',
            'rightField': 'system:index'
        })
    }))

# Get cloud bands
# Cloud probability is defined in the main body of the script, using 50%, default is 30% but I found that too aggressive
def add_cloud_bands(img):
    # Get s2cloudless image, subset the probability band.
    cld_prb = ee.Image(img.get('s2cloudless')).select('probability')

    # Condition s2cloudless by the probability threshold value.
    is_cloud = cld_prb.gt(CLD_PRB_THRESH).rename('clouds')

    # Add the cloud probability layer and cloud mask as image bands.
    return img.addBands(ee.Image([cld_prb, is_cloud]))

# Create cloud shadow bands
# NIR_DRK_THRESH is defined in the main body of the script
def add_shadow_bands(img):
    # Identify water pixels from the SCL band.
    not_water = img.select('SCL').neq(6)

    # Identify dark NIR pixels that are not water (potential cloud shadow pixels).
    SR_BAND_SCALE = 1e4
    dark_pixels = img.select('B8').lt(NIR_DRK_THRESH*SR_BAND_SCALE).multiply(not_water).rename('dark_pixels')

    # Determine the direction to project cloud shadow from clouds (assumes UTM projection).
    shadow_azimuth = ee.Number(90).subtract(ee.Number(img.get('MEAN_SOLAR_AZIMUTH_ANGLE')));

    # Project shadows from clouds for the distance specified by the CLD_PRJ_DIST input.
    cld_proj = (img.select('clouds').directionalDistanceTransform(shadow_azimuth, CLD_PRJ_DIST*10)
        .reproject(**{'crs': img.select(0).projection(), 'scale': 100})
        .select('distance')
        .mask()
        .rename('cloud_transform'))

    # Identify the intersection of dark pixels with cloud shadow projection.
    shadows = cld_proj.multiply(dark_pixels).rename('shadows')

    # Add dark pixels, cloud projection, and identified shadows as image bands.
    return img.addBands(ee.Image([dark_pixels, cld_proj, shadows]))

# Merge cloud and cloud shadow mask, clean up
# BUFFER is defined in the main body of the script, default 50m, I use 10m. Again, too aggressive
# There is confusion between snow and cloud

def add_cld_shdw_mask(img):
    # Add cloud component bands.
    img_cloud = add_cloud_bands(img)

    # Add cloud shadow component bands.
    img_cloud_shadow = add_shadow_bands(img_cloud)

    # Combine cloud and shadow mask, set cloud and shadow as value 1, else 0.
    is_cld_shdw = img_cloud_shadow.select('clouds').add(img_cloud_shadow.select('shadows')).gt(0)

    # Remove small cloud-shadow patches and dilate remaining pixels by BUFFER input.
    # 20 m scale is for speed, and assumes clouds don't require 10 m precision.
    is_cld_shdw = (is_cld_shdw.focalMin(2).focalMax(BUFFER*2/20)
        .reproject(**{'crs': img.select([0]).projection(), 'scale': 20})
        .rename('cloudmask'))

    # Add the final cloud-shadow mask to the image.
    return img_cloud_shadow.addBands(is_cld_shdw)

# Apply all masks
def apply_cld_shdw_mask(img):
    # Subset the cloudmask band and invert it so clouds/shadow are 0, else 1.
    not_cld_shdw = img.select('cloudmask').Not()

    # Subset reflectance bands and update their masks, return the result.
    return img.select('B.*').updateMask(not_cld_shdw)

## Other functions
# Get min and max of an image, for debug 
def get_minmax(image,poly):
    min_max = ee.Image(image).reduceRegion(**{
        'reducer': ee.Reducer.minMax(),
        'geometry': poly.geometry(),
        'scale': 100,
        'maxPixels': 1e10})
    print(min_max.getInfo())

# Convert to 8-bit
# Apply pre-defined gamma values
# Retain 0 as no-data value so stretch between 1 and 255
def convert(image=None,gamma=None,maxValue=None,rgbType=None):
    if rgbType == 'tc':
        img = image.select(['B4','B3','B2'])
    else:
        img = image.select(['B11', 'B8', 'B4'])
    
    #reclass values less than 0 to 0
    img1 = img.where(img.gt(maxValue),maxValue) 
    
    #reclass values greater than 0.4 to 0.4
    img2 = img1.where(img1.lt(0),0)
    
    #apply gamma function
    eqtn = 'pow(x, 1.0/' + str(gamma) + ')'
    gamma_img = img2.expression(eqtn,{'x':img2})
    
    #get max gamma value for 8-bit transformation
    max_gamma = math.pow(maxValue,1.0/gamma)
    
    #Convert to 1 - 255
    eqtn = '((x/' + str(max_gamma) + ')' +'*254)+1'
    img_out = gamma_img.expression(eqtn,{'x':gamma_img}).int()
    return(img_out)

def add_alpha(img):
    eqtn = "b('vis-red') > 0 ? 255 : 0"
    alpha = img.expression(eqtn,{'x':img}).rename('alpha').toUint8()
    return(img.addBands(alpha))

#Intialize gee
ee.Initialize()

#Import vector data
poly = geemap.shp_to_ee(p)

#Look for Sentinel-2 data, apply cloud masks, create a median mosaic, clip to extent of the polygon provided 
#Quarterly mosaics: Q1 (Jan1 - Mar31), Q2 (Apr1 - Jun30), Q3 (Jul1 - Sept30), Q4 (Oct1 - Dec31)

if q == 'q1':
    START_DATE= year + '-01-01'
    END_DATE = year + '-03-31'
    stretch = 'winter'
    interval = year + q
elif q == 'q2':
    START_DATE= year + '-04-01'
    END_DATE = year + '-06-30'
    stretch = 'winter'
    interval = year + q
elif q == 'q3':
    START_DATE= year + '-07-01'
    END_DATE = year + '-09-30'
    stretch = 'summer'
    interval = year + q
elif q == 'q4':
    START_DATE= year + '-10-01'
    END_DATE = year + '-12-31'
    stretch = 'winter'
    interval = year + q
elif q == 'custom':
    START_DATE = t1
    END_DATE = t2
    stretch = 'summer'
    interval = START_DATE + '_' + END_DATE
else:
    print('no quarter specified')

## Define stretches
if stretch == 'summer':
    if comp == 'tc':
        comp_str = '_b432'
        gamma=1.5
        maxValue=0.4
    elif comp == 'fc':
        comp_str = '_b1184'
        gamma=1.5
        maxValue=0.4
elif stretch == 'winter':
    if comp == 'tc':
        comp_str = '_b432'
        gamma=2
        maxValue=1.0
        rgbType=comp
    elif comp == '_fc':
        comp_str = '_b1184'
        gamma=2
        maxValue=1.0
    
CLOUD_FILTER = 30
CLD_PRB_THRESH = 50
NIR_DRK_THRESH = 0.15 
CLD_PRJ_DIST = 1
BUFFER = 100 #10

if comp == 'tc':
    viz = {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max':255}
else: 
    viz = {'bands': ['B11', 'B8', 'B4'], 'min': 0, 'max':255}
    
#Search Sentinel-2 Surface Reflectance collection
s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterDate(START_DATE,END_DATE).filterBounds(poly).filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE',CLOUD_FILTER))

## Create a cloud masked mosaic
col = get_s2_sr_cld_col(poly, START_DATE, END_DATE)
col_wmsks = col.map(add_cld_shdw_mask)

# def cloudDistance(img):
#     cloudDistmax = 2000 #meters
#     dist = ee.Image(img.select('cloudmask').eq(1).distance(**{'kernel':ee.Kernel.euclidean(cloudDistmax, 'meters'), 'skipMasked':True}))
#     dist_int = dist.int()
#     dist_int = dist_int.where(dist_int.gt(2000), 2000)
#     dist_int_out = dist_int.unmask(2000).rename('cloud_dist')
#     return(img.addBands(dist_int_out))


def cloudDistance(img):
    cloudDistmax = 2000  # meters
    # Apply cloud mask
    cloud_mask = img.select('cloudmask').eq(1)
    dist = ee.Image(cloud_mask).distance(**{'kernel': ee.Kernel.euclidean(cloudDistmax, 'meters'), 'skipMasked': True})
    
    # Mask out cloud pixels
    dist_int = dist.updateMask(cloud_mask).int()
    dist_int = dist_int.where(dist_int.gt(2000), 2000)
    dist_int_out = dist_int.unmask(2000).rename('cloud_dist')
    
    return img.addBands(dist_int_out)

s2_cloudDist = col_wmsks.map(cloudDistance)
s2_comp = s2_cloudDist.qualityMosaic('cloud_dist')

#s2_noclouds = col_wmsks.map(apply_cld_shdw_mask).median().multiply(0.0001)
#s2_noclouds_med_vis = convert(image=s2_noclouds,gamma=gamma,maxValue=maxValue,rgbType=comp).clip(poly).visualize(**viz)

print(START_DATE)
print(END_DATE)
s2_comp

outfolder = 'dist_comp'
##Export to google drive
region = poly.geometry()
outname = 's2_' + area_name + '_' + interval + '_bcalb_' + str(scale) +'m_b432_cloud_dist_comp_v2'
print(outname)

task_config = {
    'description': outname,
    'scale': scale,  
    'region': region,
    'crs': proj,
    'folder':outfolder,
    'shardSize':256,
    'fileDimensions':1024,
    'maxPixels':10000000000000,
    'skipEmptyTiles':True}

viz = {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max':4000}
img_viz = s2_comp.visualize(**viz)
task = ee.batch.Export.image.toDrive(img_viz.select(['vis-red', 'vis-green', 'vis-blue']), **task_config)
task.start()

import os
from osgeo import gdal

f = r'C:\Data\Burn_Severity\same_year_2023\distance_test\dist_v2'
outfolder = r'C:\Data\Burn_Severity\same_year_2023\distance_test'
base = 's2_test_2023-07-25_2023-08-10_bcalb_20m_b432_cloud_dist_comp_v2'

files = getfiles(f,'.tif')
outfilename = os.path.join(outfolder,base+'.tif')
gdal.Warp(outfilename,files)

#set no data value to which makes it transparent 
outdata = gdal.Open(os.path.join(outfolder,base+'.tif'))


##Try the same with Landsat
