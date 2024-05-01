# burnSeverity

Burn Severity Mapping with spaceborne multispectral imagery from Sentinel-2 MSI and Landsat-8/9 OLI sensors.
The process has been broken down into 4 parts:  
    
Part A - Prepare file perimeter vector file  
Part B - Burn Severity Product Generation (barc, quicklooks and qa powerpoint)  
Part C - Filter and Export  
Part D - Map Generation (not described here)  

Methodology: https://catalogue.data.gov.bc.ca/dataset/fire-burn-severity-same-year

The burn severity products can be generated either using the Jupyter Notebook (BurnSeverity_Mapping.ipynb) or the Python script (main_PartB.py). I recommend that first time users begin with the Jupyter Notebook implementation, especially if the goal is to map fewer than 10 fires at once.

## Google Earth Engine Registration
Please follow the instructions in Getting_Started_with_GEE.md. 

## Part A
Manually prepare fire perimeter shapefile in a GIS software. Ensure that the shapefile contains 5 TEXT fields:  
Fire_NUMBE: firenumber or some unique identifier   
pre_T1: start of pre-fire image interval ("yyyy-mm-dd")  
pre_T2: end of pre-fire image interval ("yyyy-mm-dd")  
post_T1: start of post-fire image interval ("yyyy-mm-dd")  
post_T2: end of pre-fire image interval ("yyyy-mm-dd")  

You can change the field names if you like, just make sure that you update lines 42 - 47 in main_PartB.py.

## Part B
### Jupyter Notebook Version
1. Click on the Notebook (BurnSeverityMapping.ipynb)
2. Click Open in Colab
3. Follow the steps.

### Automated Version
#### Installation
Please follow the instructions outlined here: https://github.com/SashaNasonova/geeMosaics. These scripts require gee, geemap and osgeo gdal packages.

#### Execution
To prepare: 
1. Open main_PartB.py in a code editor (ex. Notepad++)
2. Change line 20 to the location of the scripts  
3. Change lines 33 - 35 to define root folder and location of the perimeter shapefile created in Part A  
4. Review/change lines 42-47 to match the field names in the shapefile created in Part A  
5. Select whether to export alternates (quicklook images of all available images), export data (NBR, dNBR, dNBR_scaled), or override  
Default is:
```
export_alt = True
export_data = False
override = False
```

Override can be used if you already know which image dates you want to use. The script will accept a dictionary of pre- and post-fire image dates along
with the sensor (S2, L8 or L9). It can also be used for reruns with the help of quicklooks in the alt folder if the first attempt isn't satisfactory.

To run:
1. In Anaconda Prompt activate the gee environment
2. Run script (example command): python C:\Dev\git\burnSeverity\main_PartB.py

Please use the test data to get started. The shapefile is already formated and filled out with the correct dates.

## Part C
Script to filter, smooth, vectorize, and save as a geodatabase.  
To run: 
1. Open main_PartC.py in a code editor (ex. Notepad++)
2. Edit lines 48 - 51
3. Copy and paste entire script into the Python window in ArcPro/ArcMap and run

