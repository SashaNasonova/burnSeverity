# burnSeverity

VERY MUCH STILL IN PROGRESS!

Burn Severity Mapping with spaceborne multispectral imagery from Sentinel-2 MSI and Landsat-8/9 OLI Sensors.
The process has been broken down into 4 parts:  
    
Part A - Prepare file perimeter vector file  
Part B - Burn Severity Product Generation (barc, quicklooks and qa powerpoint)  
Part C - Filter and Export  
Part D - Map Generation  

Methodology: https://catalogue.data.gov.bc.ca/dataset/fire-burn-severity-same-year

## Installation
Please follow the instruction outlined here: https://github.com/SashaNasonova/geeMosaics. These scripts require the gee and geemap packages as well as gdal.
Installing gdal can be a huge pain. 

## Part A
Prepare fire perimeter shapefile. Ensure that the shapefile contains 5 TEXT fields:  
Fire_NUMBE: firenumber or some unique identifier   
pre_T1: start of pre-fire image interval ("yyyy-mm-dd")  
pre_T2: end of pre-fire image interval ("yyyy-mm-dd")  
post_T1: start of post-fire image interval ("yyyy-mm-dd")  
post_T2: end of pre-fire image interval ("yyyy-mm-dd")  

You can change the field names if you like, just make sure that you update lines 42 - 47 in main_PartB.py

## Part B
Change line 20 to the location of the scripts  
Change lines 33 - 35 to define root folder and location of the perimeter shapefile created in Part A  
Review/change lines 42-47 to match the field names in the shapefile created in Part A  
Select whether to export alternates (quicklook images of all available images), export data (NBR, dNBR, dNBR_scaled), or override  
Default is:
```
export_alt = True
export_data = False
override = False
```

Override can be used if you already know which image dates you want to use. The script will accept a dictionary of pre- and post-fire image dates along
with the sensor (S2, L8 or L9). It can also be used for reruns with the help of quicklooks in the alt folder if the first attempt isn't satisfactory.
(NOTE: override may not be functioning correctly as of August 28, 2023). 

To run:
1. In Anaconda Prompt active the gee environment
2. Run script (example command): python C:\Dev\git\burnSeverity\main_PartB.py

Please use the test data to get started. The shapefile is already formated and filled out with the correct dates.

## Part C
Script to filter, smooth, vectorize and save as a geodatabase.  
Edit lines 48 - 51.  
Copy and paste entire script into the Python window in ArcPro/ArcMap. 

