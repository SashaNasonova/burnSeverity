## Function that filters input BARC classification raster

#reclassed_raster = r'' #full path to the BARC classification raster
#out_raster = r'' #full path to output raster 

import os, arcpy
from pathlib import Path

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
    

root = r'C:\Data\Burn_Severity\ElephantHill\barc'
infolder = os.path.join(root,'original')
imglist = getfiles(infolder,'.tif')

outfolder = os.path.join(root,'filtered')
if not os.path.exists(outfolder):
        os.makedirs(outfolder)

arcpy.CheckOutExtension("Spatial")
arcpy.env.overwriteOutput = True

for i in imglist:
    out_name = Path(i).stem + '_filtered.tif'
    out_raster = os.path.join(outfolder,out_name)
    
    barc_filter(i,out_raster)