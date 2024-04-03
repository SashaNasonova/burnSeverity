# -*- coding: utf-8 -*-
"""
Created on Tue Oct 18 10:16:47 2022

@author: snasonov
"""
from datetime import datetime,timedelta
import ee
import geemap
import geopandas
import os,json
#from datetime import datetime as dt
import pandas as pd
from osgeo import gdal
from osgeo.gdalconst import GA_Update
import sys

def export_alternates(folder,pre_mosaic_col,post_mosaic_col,dattype,fires_df,poly,opt,firenumber,preflag,postflag):
    def grid_footprint(footprint,nx,ny):
        from shapely.geometry import Polygon, LineString, MultiPolygon
        from shapely.ops import split
        
        #polygon = footprint
        polygon = Polygon(footprint['coordinates'][0])
        #polygon = Polygon(footprint)
        
        minx, miny, maxx, maxy = polygon.bounds
        dx = (maxx - minx) / nx  # width of a small part
        dy = (maxy - miny) / ny  # height of a small part
        
        horizontal_splitters = [LineString([(minx, miny + i*dy), (maxx, miny + i*dy)]) for i in range(ny)]
        vertical_splitters = [LineString([(minx + i*dx, miny), (minx + i*dx, maxy)]) for i in range(nx)]
        splitters = horizontal_splitters + vertical_splitters

        result = polygon
        for splitter in splitters:
            result = MultiPolygon(split(result, splitter))

        coord_list = [list(part.exterior.coords) for part in result.geoms]
        
        poly_list = []
        for cc in coord_list:
            p = ee.Geometry.Polygon(cc)
            poly_list.append(p)
        return(poly_list)

    def apply_scale_factors(image):
        opticalBands = image.select('SR_B.').multiply(0.0000275).add(-0.2)
        thermalBands = image.select('ST_B.*').multiply(0.00341802).add(149.0)
        return image.addBands(opticalBands, None, True).addBands(thermalBands, None, True)
    
    
    #Exporting alternates
    poly_area = fires_df[fires_df[opt['fn']] == firenumber].iloc[0][opt['areaha']]
    print('Fire Area: ' + str(poly_area))
    
    if poly_area < 10000:
        n = 2
    elif poly_area > 10000 and poly_area < 100000:
        n = 3
    elif poly_area > 100000 and poly_area < 400000:
        n = 4
    else: 
        n = 5 
    
    print('Number of tiles: ' + str(n*n))
    
    #export pre and post rgbs, tile to avoid pixel limit issues.
    footprint = poly.geometry().bounds().getInfo()
    grids = grid_footprint(footprint,n,n) #3,3 works for a fire that's ~90 000 ha large, if larger, increase the number of tiles
    
    if preflag:
        ## Export all pre qls
        pre_tc_8bit = os.path.join(folder,'pre_truecolor_8bit_alt')
        if not os.path.exists(pre_tc_8bit):
                os.makedirs(pre_tc_8bit)
        
        pre_mosaic_col_list = pre_mosaic_col.toList(1000)
        
        if pre_mosaic_col.size().getInfo() == 0:
            print('No pre alternatives')
            pass
        else:
            for i in range(0,pre_mosaic_col_list.length().getInfo()):
                pre_img = ee.Image(pre_mosaic_col_list.get(i))
                pre_date = pre_img.get("system:index").getInfo()
                
                if dattype.startswith('S2'):
                    pre_img_export = pre_img.multiply(0.0001)
                elif (dattype == 'L8') | (dattype == 'L9'):
                    pre_img_export = apply_scale_factors(pre_img)
                elif (dattype == 'L5') | (dattype == 'L7'):
                    pre_img_export = apply_scale_factors(pre_img)
                else:
                    pass
                    
                pre_img_list = []
                for i in range(0,len(grids)):
                    roi = grids[i]
                    filename = os.path.join(pre_tc_8bit, dattype + '_' + pre_date + '_truecolor_pre_8bit_alt_' + str(i) + '.tif')
                    pre_img_list.append(filename)
                    if dattype.startswith('S2'):
                        viz = {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max':0.3,'gamma':1.5}
                        geemap.ee_export_image(pre_img_export.clip(roi).visualize(**viz), filename=filename, scale=10, file_per_band=False,crs='EPSG:3005')
                    elif (dattype == 'L8') | (dattype == 'L9'): 
                        viz = {'bands': ['SR_B4', 'SR_B3', 'SR_B2'], 'min': 0, 'max':0.3,'gamma':1.5}
                        geemap.ee_export_image(pre_img_export.clip(roi).visualize(**viz), filename=filename, scale=30, file_per_band=False,crs='EPSG:3005')
                    elif (dattype == 'L5') | (dattype == 'L7'):
                        viz = {'bands': ['SR_B3','SR_B2','SR_B1'], 'min': 0, 'max':0.3,'gamma':1.5}
                        geemap.ee_export_image(pre_img_export.clip(roi).visualize(**viz), filename=filename, scale=30, file_per_band=False,crs='EPSG:3005')
                    else:
                        pass
                
                #mosaic 
                outfilename = dattype + '_' + pre_date + '_truecolor_pre_8bit_alt' + '.tif'
                out = os.path.join(pre_tc_8bit,outfilename)
                gdal.Warp(out,pre_img_list)
                for file in pre_img_list: os.remove(file) #delete tiles
        
    if postflag:
        ## Export all post qls
        post_tc_8bit = os.path.join(folder,'post_truecolor_8bit_alt')
        if not os.path.exists(post_tc_8bit):
                os.makedirs(post_tc_8bit)
       
        post_mosaic_col_list = post_mosaic_col.toList(1000)
        
        if post_mosaic_col.size().getInfo() == 0:
            print('No post alternatives')
            pass
        
        else:
            for i in range(0,post_mosaic_col_list.length().getInfo()):
                post_img = ee.Image(post_mosaic_col_list.get(i))
                post_date = post_img.get("system:index").getInfo()
                
                if dattype.startswith('S2'):
                    post_img_export = post_img.multiply(0.0001)
                elif (dattype == 'L8') | (dattype == 'L9'):
                    post_img_export = apply_scale_factors(post_img)
                elif (dattype == 'L5') | (dattype == 'L7'):
                    post_img_export = apply_scale_factors(post_img)
                else:
                    pass
    
                post_img_list = []
                for i in range(0,len(grids)):
                    roi = grids[i]
                    filename = os.path.join(post_tc_8bit, dattype + '_' + post_date + '_truecolor_post_8bit_alt_' + str(i) + '.tif')
                    
                    post_img_list.append(filename)
                    if dattype.startswith('S2'):
                        viz = {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max':0.3,'gamma':1.5}
                        geemap.ee_export_image(post_img_export.clip(roi).visualize(**viz), filename=filename, scale=10, file_per_band=False,crs='EPSG:3005')
                    elif (dattype == 'L8') | (dattype == 'L9'): 
                        viz = {'bands': ['SR_B4', 'SR_B3', 'SR_B2'], 'min': 0, 'max':0.3,'gamma':1.5}
                        geemap.ee_export_image(post_img_export.clip(roi).visualize(**viz), filename=filename, scale=30, file_per_band=False,crs='EPSG:3005')
                    elif (dattype == 'L5') | (dattype == 'L7'):
                        viz = {'bands': ['SR_B3','SR_B2','SR_B1'],'min': 0, 'max':0.3,'gamma':1.5}
                        geemap.ee_export_image(post_img_export.clip(roi).visualize(**viz), filename=filename, scale=30, file_per_band=False,crs='EPSG:3005')
                    else:
                        pass
            
                #post truecolor
                outfilename = dattype + '_' + post_date + '_truecolor_post_8bit_alt' + '.tif'
                out = os.path.join(post_tc_8bit,outfilename)
                gdal.Warp(out,post_img_list)
                for file in post_img_list: os.remove(file)
        
    print('Alternates exported')


def barc(fires_df,firenumber,outdir,poly,opt,proc,altdir=None):
    def getfiles(d,ext):
        paths = []
        for file in os.listdir(d):
            if file.endswith(ext):
                paths.append(os.path.join(d, file))
        return(paths) 

    #Helper function must be nested within barc
    
    def getDate(im):
        return(ee.Image(im).date().format("YYYY-MM-dd"))

    def getSceneIds(im):
        return(ee.Image(im).get('PRODUCT_ID'))

    def mosaicByDate(indate):
        d = ee.Date(indate)
        #print(d)
        im = col.filterBounds(poly).filterDate(d, d.advance(1, "day")).mosaic()
        #print(im)
        return(im.set("system:time_start", d.millis(), "system:index", d.format("YYYY-MM-dd")))
        
    def runDateMosaic(col_list):
        #get a list of unique dates within the list
        date_list = col_list.map(getDate).getInfo()
        udates = list(set(date_list))
        udates.sort()
        udates_ee = ee.List(udates)
        
        #mosaic images by unique date
        mosaic_imlist = udates_ee.map(mosaicByDate)
        return(ee.ImageCollection(mosaic_imlist))

    def NBR_S2(image):
        nbr = image.expression(
            '(NIR - SWIR) / (NIR + SWIR)', {
                'NIR': image.select('B8'),
                'SWIR': image.select('B12')}).rename('nbr')
        return(nbr)

    def NBR_Landsat(image,dattype):
        if (dattype == 'L5')|(dattype == 'L7'):
            nbr = image.expression(
                '(NIR - SWIR) / (NIR + SWIR)', {
                    'NIR': image.select('SR_B4'),
                    'SWIR': image.select('SR_B7')}).rename('nbr')
        elif (dattype == 'L8')|(dattype == 'L9'):
            nbr = image.expression(
                '(NIR - SWIR) / (NIR + SWIR)', {
                    'NIR': image.select('SR_B5'),
                    'SWIR': image.select('SR_B7')}).rename('nbr')
        else:
            print('Incorrect Landsat sensor specified')
        return(nbr)

    def grid_footprint(footprint,nx,ny):
        from shapely.geometry import Polygon, LineString, MultiPolygon
        from shapely.ops import split
        
        #polygon = footprint
        polygon = Polygon(footprint['coordinates'][0])
        #polygon = Polygon(footprint)
        
        minx, miny, maxx, maxy = polygon.bounds
        dx = (maxx - minx) / nx  # width of a small part
        dy = (maxy - miny) / ny  # height of a small part
        
        horizontal_splitters = [LineString([(minx, miny + i*dy), (maxx, miny + i*dy)]) for i in range(ny)]
        vertical_splitters = [LineString([(minx + i*dx, miny), (minx + i*dx, maxy)]) for i in range(nx)]
        splitters = horizontal_splitters + vertical_splitters

        result = polygon
        for splitter in splitters:
            result = MultiPolygon(split(result, splitter))

        coord_list = [list(part.exterior.coords) for part in result.geoms]
        
        poly_list = []
        for cc in coord_list:
            p = ee.Geometry.Polygon(cc)
            poly_list.append(p)
        return(poly_list)

    def apply_scale_factors(image):
        opticalBands = image.select('SR_B.').multiply(0.0000275).add(-0.2)
        thermalBands = image.select('ST_B.*').multiply(0.00341802).add(149.0)
        return image.addBands(opticalBands, None, True).addBands(thermalBands, None, True)

    #Landsat cloud mask from metadata 
    ## Check this!!!
    def get_cloud(img1):
        ### Change as of Oct 24, 2023: cloud shadow is too inaccurate, remove
        ### Though it is picking up topographic shadow. Questions!
        # Bits 3 and 4 are cloud and cloud shadow, respectively.
        #cloudShadowBitMask = (1 << 4)
        cloudBitMask = (1 << 3)
        # Get the pixel QA band.
        qa = img1.select('QA_PIXEL')
        #set both flags to 1
        #clouds = qa.bitwiseAnd(cloudBitMask).eq(0).And(qa.bitwiseAnd(cloudShadowBitMask).eq(0)).rename('cloudmsk')
        clouds = qa.bitwiseAnd(cloudBitMask).eq(0).rename('cloudmsk')
        return(img1.addBands(clouds))
    

    #TODO: add scene IDs! Check S2 cloud masks
    searchd = {'Id':firenumber,'sensor':opt['dattype'],
               'cld_pre':'','pre_T1':'','pre_T2':'',
               'cld_post':'','post_T1':'','post_T2':'',
               'pre_mosaic_date':'','pre_scenes':'',
               'post_mosaic_date':'','post_scenes':''}
    
    firelist = [firenumber]
    
    if opt['override']:
        dattype = opt['override'][firenumber]['sensor']
    else:
        dattype = opt['dattype']
    
    # Select data type, only SR as an option, may need to change
    if dattype == 'S2':
        col = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') 
        print('Selected S2 SR')
    elif dattype == 'L9':
        if proc == 'TOA':
            col = ee.ImageCollection("LANDSAT/LC09/C02/T1_TOA")
            print('Selected L9 TOA')
        else:
            col = ee.ImageCollection('LANDSAT/LC09/C02/T1_L2') 
            print('Selected L9 SR')
    elif dattype == 'L8':
        if proc == 'TOA':
            col = ee.ImageCollection("LANDSAT/LC08/C02/T1_TOA")
            print('Selected L8 TOA')
        else:    
            col = ee.ImageCollection('LANDSAT/LC08/C02/T1_L2')
            print('Selected L8 SR')
    elif dattype == 'L5':
        col = ee.ImageCollection("LANDSAT/LT05/C02/T1_L2")
        print('Selected L5 SR')
    elif dattype == 'L7':
        col = ee.ImageCollection("LANDSAT/LE07/C02/T1_L2")
        print('Selected L7 SR')
    else:
        print('wrong data type selected')
    
    
    ### Create folders
    outfolder = os.path.join(outdir,firenumber)
    if not os.path.exists(outfolder):
            os.makedirs(outfolder)
            
    altfolder = os.path.join(altdir,firenumber)
    if not os.path.exists(altfolder):
            os.makedirs(altfolder)
            
    ######### Find pre-fire images 
    # TO DO: add an option for multiple date ranges
    if opt['override']:
        startdate = (datetime.strptime(opt['override'][firenumber]['pre_mosaic'],'%Y-%m-%d') + timedelta(days=-2)).strftime('%Y-%m-%d') ## for reruns
        enddate =  (datetime.strptime(opt['override'][firenumber]['pre_mosaic'],'%Y-%m-%d') + timedelta(days=2)).strftime('%Y-%m-%d') ## for reruns
    else:
        startdate = fires_df[fires_df[opt['fn']] == firenumber].iloc[0][opt['preT1']]
        searchd[opt['preT1']] = startdate
        enddate = fires_df[fires_df[opt['fn']] == firenumber].iloc[0][opt['preT2']]
        searchd[opt['preT2']] = enddate
    
    # Search archive
    cld =100 #cloud cover percentage
    searchd['cld_pre'] = cld
    
    if dattype.startswith('S2'):
        before = col.filterDate(startdate,enddate).filterBounds(poly).filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE',cld))
    elif dattype.startswith('L'):
        before = col.filterDate(startdate,enddate).filterBounds(poly).filter(ee.Filter.lt('CLOUD_COVER',cld))
    else:
        pass
    
    before_list = before.toList(1000)
    
    if before_list.size().getInfo() == 0:
        print('Zero before scenes were found! Rerun!')
        #failed.append(firenumber)
    
  
    # Create before mosaics 
    pre_mosaic_col = runDateMosaic(before_list)
    pre_mosaic_col_list = pre_mosaic_col.toList(1000)
    
    # Ask server for individual scene metadata
    metadata = before.getInfo()
    
    # Turn metadata into table format
    features = metadata['features']
    
    out = []
    for i in features:
        d1 = pd.DataFrame([{'id':i['id']}])
        p1 = pd.DataFrame([i['properties']])
        t1 = d1.join(p1)
        out.append(t1)
    
    meta_df = pd.concat(out)
    
    def strDate(string):
        u_str = string.rsplit('_')[1].rsplit('T')[0]
        s = u_str[0:4] + '-' + u_str[4:6] + '-' + u_str[6:8]
        return(s)
    
    
    #add date column 
    if dattype.startswith('S2'):
        meta_df['date'] = meta_df['DATATAKE_IDENTIFIER'].apply(strDate)
    else:
        meta_df['date'] = meta_df['DATE_ACQUIRED']
    
    outpath = os.path.join(outfolder,'pre_sceneMetadata.csv')
    meta_df.to_csv(outpath)
    
    #make a copy of meta_df 
    pre_meta_scenes = meta_df.copy()
    
    # Ask server for mosaic metadata
    mosaic_meta = pre_mosaic_col.getInfo()
    
    # Classify to get coverage and cloud extent, fix this to check if any bands are equal to 0
    def classify_extent(img1):
        if dattype.startswith('S2'):
            classes = img1.expression("((B2 + B3 + B4) !=0) ? 1 "
                                       ": 0",{'B2': img1.select('B2'),
                                              'B3': img1.select('B3'),
                                              'B4': img1.select('B4')}).rename('c').clip(poly)
        else: 
            classes = img1.expression("((B2 + B3 + B4) !=0) ? 1 "
                                       ": 0",{'B2': img1.select('SR_B2'),
                                              'B3': img1.select('SR_B3'),
                                              'B4': img1.select('SR_B4')}).rename('c').clip(poly)
        return(classes)
    pre_mosaic_extent = pre_mosaic_col.map(classify_extent).toBands()
    
    
    def classify_cc(img1):
        if dattype.startswith('S2'):
            classes = img1.expression("(MSK_CLDPRB > 30) ? 1 "
                               ": 0",{'MSK_CLDPRB': img1.select('MSK_CLDPRB')}).rename('c').clip(poly)
        else:
            classes = img1.expression("(cloudmsk == 1) ? 0 "
                               ": 1",{'cloudmsk': img1.select('cloudmsk')}).rename('c').clip(poly)
        return(classes)     
    
    if dattype.startswith('S2'):
        pre_mosaic_cc = pre_mosaic_col.map(classify_cc).toBands()
    else:
        pre_mosaic_cloudmsk = pre_mosaic_col.map(get_cloud)
        pre_mosaic_cc = pre_mosaic_cloudmsk.map(classify_cc).toBands()
    
    #Calculate statistics, if the image is too big this may fail.
    #This step causes problems sometimes due to maxPixels limits
    reduced_sum = pre_mosaic_extent.reduceRegion(reducer=ee.Reducer.sum(),geometry=poly.geometry(),scale=30,maxPixels=100000000000).getInfo()
    reduced_count = pre_mosaic_extent.reduceRegion(reducer=ee.Reducer.count(),geometry=poly.geometry(),maxPixels=100000000000,scale=30).getInfo()
    
    reduced_sum_cc = pre_mosaic_cc.reduceRegion(reducer=ee.Reducer.sum(),geometry=poly.geometry(),maxPixels=100000000000,scale=30).getInfo()
    reduced_count_cc = pre_mosaic_cc.reduceRegion(reducer=ee.Reducer.count(),geometry=poly.geometry(),maxPixels=100000000000,scale=30).getInfo()
    
    print('Pre image statistics calculated')
    
    #Rearrange and calculate percent coverage and percent cloud cover
    #extent
    df_sum = pd.DataFrame([reduced_sum]).T
    df_sum.columns = ['sum']
    
    df_count = pd.DataFrame([reduced_count]).T
    df_count.columns = ['count']
    
    df_perc = df_sum.join(df_count)
    df_perc['percent_coverage'] = (df_perc['sum']/df_perc['count'])*100
    
    #cloud cover
    df_sum_cc = pd.DataFrame([reduced_sum_cc]).T
    df_sum_cc.columns = ['sum_cc']
    
    df_count_cc = pd.DataFrame([reduced_count_cc]).T
    df_count_cc.columns = ['count_cc']
    
    df_perc_cc = df_sum_cc.join(df_count_cc)
    df_perc_cc['percent_cc'] = (df_perc_cc['sum_cc']/df_perc_cc['count_cc'])*100 
    
    #join extent and cc 
    meta_df_ext = df_perc.join(df_perc_cc)
    
    #get rid of cc suffix
    oldnames = meta_df_ext.index
    newnames = [s.rsplit('_')[0] for s in oldnames]
    meta_df_ext.index = newnames
    
    #get average scene cloud cover and join to mosaic metadata
    if dattype.startswith('S2'):
        pre_meta_scenes_cld = pre_meta_scenes.groupby('date')['CLOUDY_PIXEL_PERCENTAGE'].mean()
        temp = pd.DataFrame(pre_meta_scenes_cld)
        pre_meta_scenes_cld = temp.rename(columns={'date':'date','CLOUDY_PIXEL_PERCENTAGE':'percent_cc_scene'})
    else:
        pre_meta_scenes_cld = pre_meta_scenes.groupby('date')['CLOUD_COVER'].mean()
        temp = pd.DataFrame(pre_meta_scenes_cld)
        pre_meta_scenes_cld = temp.rename(columns={'CLOUD_COVER':'percent_cc_scene'})
    
    meta_df_ext = meta_df_ext.join(pre_meta_scenes_cld)
    
    outpath = os.path.join(outfolder,'pre_mosaicMetadata.csv')
    meta_df_ext.to_csv(outpath)
    
    #Finally! Select best pre-mosaic. Coverage >99% and least cloud cover
    #full_cov = meta_df_ext.loc[(meta_df_ext['percent_coverage'] > 99)]
    full_cov = meta_df_ext.loc[(meta_df_ext['percent_coverage'] == max(meta_df_ext['percent_coverage'])) | (meta_df_ext['percent_coverage'] > 99)]
    
    # if max(meta_df_ext['percent_coverage']) < 90:
    #     raise Exception('No pre-fire scenes available with coverage >=90%')
        
    # #pre_mosaic_date = full_cov['percent_cc'].idxmin()
    
    # if min(full_cov['percent_cc']) > 10:
    #     raise Exception('No pre-fire scenes available with cloud cover <= 10%')
    
    #if greater than 90% coverage not available print error and exit 
    if max(meta_df_ext['percent_coverage']) < 90:
        if opt['override']:
            print('Override selected. Warning! Pre-image has less than 90% coverage!')
            pass
        else:
            raise Exception('No post-fire scenes available with coverage >=90%')
    
    if min(full_cov['percent_cc']) > 10:
        if opt['override']:
            print('Override selected. Warning! Pre-image has more than 10% cloud cover!')
            pass
        else:
            raise Exception('No pre-fire scenes available with cloud cover <= 10%')
    
    #select by minimum scene cloud cover too
    x = full_cov[full_cov['percent_cc'] == full_cov['percent_cc'].min()]
    pre_mosaic_date = x['percent_cc_scene'].idxmin()
    print(x)
    
    if opt['export_alt']:
        #select only mosaics that have greater >= 90% coverage AND < 20% cloud cover 
        pre_export_sub = meta_df_ext.loc[(meta_df_ext['percent_coverage'] >=90) & (meta_df_ext['percent_cc'] < 20)]
        pre_export_sub_index = pre_export_sub.index.tolist()
        pre_mosaic_col_export = pre_mosaic_col.filter(ee.Filter.inList('system:index',pre_export_sub_index))
        

    print('Pre image date selected: ' + pre_mosaic_date)
    
    ######### Find post-fire images 
    # TO DO: add an option for multiple date ranges 
    if opt['override']:
        startdate = (datetime.strptime(opt['override'][firenumber]['post_mosaic'],'%Y-%m-%d') + timedelta(days=-2)).strftime('%Y-%m-%d') ## for reruns
        enddate =  (datetime.strptime(opt['override'][firenumber]['post_mosaic'],'%Y-%m-%d') + timedelta(days=2)).strftime('%Y-%m-%d') ## for reruns
    else:
        startdate = fires_df[fires_df[opt['fn']] == firenumber].iloc[0][opt['postT1']]
        searchd['post_T1'] = startdate
        enddate = fires_df[fires_df[opt['fn']] == firenumber].iloc[0][opt['postT2']]
        searchd['post_T2'] = enddate
    
    # Search archive
    cld = 100 #cloud cover percentage
    searchd['cld_post'] = cld
    if dattype.startswith('S2'):
        after = col.filterDate(startdate,enddate).filterBounds(poly).filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE',cld))
    elif dattype.startswith('L'):
        after = col.filterDate(startdate,enddate).filterBounds(poly).filter(ee.Filter.lt('CLOUD_COVER',cld))
    else:
        pass
    
    after_list = after.toList(1000)
    #print('# of after scenes: ' + str(after_list.size().getInfo())) #for debug
    
    if after_list.size().getInfo() == 0:
        #failed.append(firenumber)
        print('Zero after scenes were found! Rerun!')
    
    # Create before mosaics 
    post_mosaic_col = runDateMosaic(after_list)
    post_mosaic_col_list = post_mosaic_col.toList(1000)
    
    # Ask server for individual scene metadata
    metadata = after.getInfo()
    
    # Turn metadata into table format
    features = metadata['features']
    
    out = []
    for i in features:
        d1 = pd.DataFrame([{'id':i['id']}])
        p1 = pd.DataFrame([i['properties']])
        t1 = d1.join(p1)
        out.append(t1)
    
    meta_df = pd.concat(out)
    
    def strDate(string):
        u_str = string.rsplit('_')[1].rsplit('T')[0]
        s = u_str[0:4] + '-' + u_str[4:6] + '-' + u_str[6:8]
        return(s)
    
    #add date column 
    if dattype.startswith('S2'):
        meta_df['date'] = meta_df['DATATAKE_IDENTIFIER'].apply(strDate)
    else:
        meta_df['date'] = meta_df['DATE_ACQUIRED']
    
    outpath = os.path.join(outfolder,'post_sceneMetadata.csv')
    meta_df.to_csv(outpath)
    
    #make a copy of meta_df 
    post_meta_scenes = meta_df.copy()
    
    # Ask server for mosaic metadata
    mosaic_meta = post_mosaic_col.getInfo()
    
    # Classify to get coverage and cloud extent
    post_mosaic_extent = post_mosaic_col.map(classify_extent).toBands()
     
    
    if dattype.startswith('S2'):
        post_mosaic_cc = post_mosaic_col.map(classify_cc).toBands()
    else:
        post_mosaic_cloudmsk = post_mosaic_col.map(get_cloud)
        post_mosaic_cc = post_mosaic_cloudmsk.map(classify_cc).toBands()
    
    #Calculate statistics, if the image is too big this may fail
    reduced_sum = post_mosaic_extent.reduceRegion(reducer=ee.Reducer.sum(),geometry=poly.geometry(),scale=30,maxPixels=100000000000).getInfo()
    reduced_count = post_mosaic_extent.reduceRegion(reducer=ee.Reducer.count(),geometry=poly.geometry(),scale=30,maxPixels=100000000000).getInfo()
    
    reduced_sum_cc = post_mosaic_cc.reduceRegion(reducer=ee.Reducer.sum(),geometry=poly.geometry(),scale=30,maxPixels=100000000000).getInfo()
    reduced_count_cc = post_mosaic_cc.reduceRegion(reducer=ee.Reducer.count(),geometry=poly.geometry(),scale=30,maxPixels=100000000000).getInfo()
    print('Post image statistics calculated')
    
    #Rearrange and calculate percent coverage and percent cloud cover
    #extent
    df_sum = pd.DataFrame([reduced_sum]).T
    df_sum.columns = ['sum']
    
    df_count = pd.DataFrame([reduced_count]).T
    df_count.columns = ['count']
    
    df_perc = df_sum.join(df_count)
    df_perc['percent_coverage'] = (df_perc['sum']/df_perc['count'])*100
    
    #cloud cover
    df_sum_cc = pd.DataFrame([reduced_sum_cc]).T
    df_sum_cc.columns = ['sum_cc']
    
    df_count_cc = pd.DataFrame([reduced_count_cc]).T
    df_count_cc.columns = ['count_cc']
    
    df_perc_cc = df_sum_cc.join(df_count_cc)
    df_perc_cc['percent_cc'] = (df_perc_cc['sum_cc']/df_perc_cc['count_cc'])*100 
    
    #join extent and cc 
    meta_df_ext = df_perc.join(df_perc_cc)
    meta_df_ext
    
    #get rid of cc suffix
    oldnames = meta_df_ext.index
    newnames = [s.rsplit('_')[0] for s in oldnames]
    meta_df_ext.index = newnames
    
    #get average scene cloud cover and join to mosaic metadata
    if dattype.startswith('S2'):
        post_meta_scenes_cld = post_meta_scenes.groupby('date')['CLOUDY_PIXEL_PERCENTAGE'].mean()
        temp = pd.DataFrame(post_meta_scenes_cld)
        post_meta_scenes_cld = temp.rename(columns={'date':'date','CLOUDY_PIXEL_PERCENTAGE':'percent_cc_scene'})
    else:
        post_meta_scenes_cld = post_meta_scenes.groupby('date')['CLOUD_COVER'].mean()
        temp = pd.DataFrame(post_meta_scenes_cld)
        post_meta_scenes_cld = temp.rename(columns={'CLOUD_COVER':'percent_cc_scene'})
    
    meta_df_ext = meta_df_ext.join(post_meta_scenes_cld)
    
    outpath = os.path.join(outfolder,'post_mosaicMetadata.csv')
    meta_df_ext.to_csv(outpath)
    
    #Finally! Select best post-mosaic. Coverage >99% or maximum available coverage, and least cloud cover
    full_cov = meta_df_ext.loc[(meta_df_ext['percent_coverage'] == max(meta_df_ext['percent_coverage'])) | (meta_df_ext['percent_coverage'] > 99)]
    #full_cov.sort_index(inplace=True,ascending=False) #sort descending, to get most recent image, instead of getting most recent, now looking for least cloudy with scene meta
    #test = os.path.join(outfolder,'post_mosaicMetadata_fullcov.csv') #debug
    #full_cov.to_csv(test) #debug
    
    #if greater than 90% coverage not available print error and exit 
    if max(meta_df_ext['percent_coverage']) < 90:
        if opt['override']:
            print('Override selected. Warning! Post-image has less than 90% coverage!')
            pass
        else:
            raise Exception('No post-fire scenes available with coverage >=90%')
    
    if min(full_cov['percent_cc']) > 10:
        if opt['override']:
            print('Override selected. Warning! Post-image has more than 10% cloud cover!')
            pass
        else:
            #raise Exception('No post-fire scenes available with cloud cover <= 10%')
            print('ignoring cloud cover cut off')
            pass
    
    #select by minimum scene cloud cover too
    x = full_cov[full_cov['percent_cc'] == full_cov['percent_cc'].min()]
    post_mosaic_date = x['percent_cc_scene'].idxmin()
    print(x)
    
    #post_mosaic_date = full_cov['percent_cc'].idxmin()
    
    if opt['export_alt']:
        #select only mosaics that have greater >= 90% coverage AND < 10% cloud cover 
        post_export_sub = meta_df_ext.loc[(meta_df_ext['percent_coverage'] >=90) & (meta_df_ext['percent_cc'] < 20)]
        post_export_sub_index = post_export_sub.index.tolist()
        post_mosaic_col_export = post_mosaic_col.filter(ee.Filter.inList('system:index',post_export_sub_index))
        
    print('Post image selected: ' + post_mosaic_date)
    
    #add pre and post images to the txt file
    # if dattype.startswith('S2'):
    #     pre_scenes_info = pre_meta_scenes.loc[pre_meta_scenes['date'] == pre_mosaic_date]['PRODUCT_ID'].tolist()
    #     post_scenes_info = post_meta_scenes.loc[post_meta_scenes['date'] == post_mosaic_date]['PRODUCT_ID'].tolist()
    # else:
    #     pre_scenes_info = pre_meta_scenes.loc[pre_meta_scenes['date'] == pre_mosaic_date]['LANDSAT_SCENE_ID'].tolist()
    #     post_scenes_info = post_meta_scenes.loc[post_meta_scenes['date'] == post_mosaic_date]['LANDSAT_SCENE_ID'].tolist()
    

    pre_scenes_info = pre_meta_scenes.loc[pre_meta_scenes['date'] == pre_mosaic_date]['system:index'].tolist()
    post_scenes_info = post_meta_scenes.loc[post_meta_scenes['date'] == post_mosaic_date]['system:index'].tolist()
    
    #check if over-riding automatic selection
    if opt['override']:
        print('Overriding')
        pre_mosaic_date = opt['override'][firenumber]['pre_mosaic'] ## for reruns
        post_mosaic_date = opt['override'][firenumber]['post_mosaic'] ## for reruns
    else:
        pass
    
    print('Calculating NBR')
    #select pre-image and post-image
    pre_col = pre_mosaic_col.filter(ee.Filter.inList("system:index",ee.List([pre_mosaic_date]))) 
    if dattype.startswith('S2'):
        pre_img = ee.Image(pre_col.toList(1).get(0)).multiply(0.0001)
    else:
        #TODO: no scale factors for TOA
        pre_img = apply_scale_factors(ee.Image(pre_col.toList(1).get(0)))
    
    post_col = post_mosaic_col.filter(ee.Filter.inList("system:index",ee.List([post_mosaic_date])))
    if dattype.startswith('S2'):
        post_img = ee.Image(post_col.toList(1).get(0)).multiply(0.0001)
    else:
        #TODO: no scale factors for TOA
        post_img = apply_scale_factors(ee.Image(post_col.toList(1).get(0)))
    
    #clip to boundary
    #pre_img_c = pre_img.clip(poly)
    #post_img_c = post_img.clip(poly)
    
    #TODO: remove clipping here 
    pre_img_c = pre_img
    post_img_c = post_img
    
    #calculate NBR
    if dattype.startswith('S2'):
        pre_nbr = NBR_S2(pre_img_c)
        post_nbr = NBR_S2(post_img_c)
    else:
        pre_nbr = NBR_Landsat(pre_img_c,dattype)
        post_nbr = NBR_Landsat(post_img_c,dattype)

    #calculate dNBR
    print('Creating BARC map')
    dNBR = pre_nbr.subtract(post_nbr).rename('dNBR')
    
    #scale dNBR
    dNBR_scaled = dNBR.expression('(dNBR * 1000 + 275)/5',{'dNBR': dNBR.select('dNBR')}).rename('dNBR_scaled')
    #dNBR_scaled_int = dNBR_scaled.int().rename('dNBR_scaled_int')
    
    
    # classes = dNBR_scaled_int.expression("(dNBR_scaled_int > 186) ? 4 "
    #                                 ": (dNBR_scaled_int > 109) ? 3 "
    #                                 ": (dNBR_scaled_int > 75) ? 2 "
    #                                 ": 1",{'dNBR_scaled_int': dNBR_scaled_int.select('dNBR_scaled_int')})
    
    classes = dNBR_scaled.expression("(dNBR_scaled >= 187) ? 4 "
                                    ": (dNBR_scaled >= 110) ? 3 "
                                    ": (dNBR_scaled >= 76) ? 2 "
                                    ": 1",{'dNBR_scaled': dNBR_scaled.select('dNBR_scaled')})
    
    
    print('Applying cloud mask if necessary')
    #Grab pre and post image cloud masks
    cm = pre_mosaic_date + '_c'
    pre_img_cloudmsk = pre_mosaic_cc.select([cm]).Not().clip(poly)
    cm = post_mosaic_date + '_c'
    post_img_cloudmsk = post_mosaic_cc.select([cm]).Not().clip(poly)
    
    #Union masks and apply to classes
    comb_cloudmsk = pre_img_cloudmsk.multiply(post_img_cloudmsk)    
    
    #clip, remap 0 to 9 and set 9 to NoData upon export
    classes_clipped_nodata = classes.clip(poly).remap([0,1,2,3,4],[9,1,2,3,4]) 
    
    mask_clouds = False
    if mask_clouds:
        classes_clipped_export = classes_clipped_nodata.multiply(comb_cloudmsk) #0 is cloudmasked, or unknown
    else:
        classes_clipped_export = classes_clipped_nodata
    
    #get stats
    #outcsv = os.path.join(outfolder,'barc_percent.csv')
    #geemap.zonal_statistics_by_group(classes_clipped_export,poly.geometry(),outcsv,statistics_type='PERCENTAGE')
    
    roi = poly.geometry()

    if not os.path.exists(outfolder):
            os.makedirs(outfolder)
    
    print('Beginning image export')
    #get dates 
    pre_date = pre_mosaic_date.replace('-','') 
    post_date = post_mosaic_date.replace('-','')
    
    if dattype.startswith('S2'):
        px = 20 #20 for S2
    else:
        px = 30 #30 for landsat
    
    ## Define tiling rules
    poly_area = fires_df[fires_df[opt['fn']] == firenumber].iloc[0][opt['areaha']]
    print('Fire Area: ' + str(poly_area))
    
    if poly_area < 10000:
        n = 2
    elif poly_area > 10000 and poly_area < 100000:
        n = 3
    elif poly_area > 100000 and poly_area < 400000:
        n = 4
    else: 
        n = 5 
    
    print('Number of tiles: ' + str(n*n))
    
    #export pre and post rgbs, tile to avoid pixel limit issues.
    footprint = poly.geometry().bounds().getInfo()
    grids = grid_footprint(footprint,n,n) #3,3 works for a fire that's ~90 000 ha large, if larger, increase the number of tiles
    
    ##debug export extent image
    #filename = os.path.join(outfolder,'extent_raster.tif')
    #geemap.ee_export_image(post_mosaic_extent.clip(footprint), filename=filename, scale=30, file_per_band=False,crs='EPSG:3005')
    
    for i in range(0,len(grids)):
        roi = grids[i]
        ## Export BARC
        barc_folder = os.path.join(outfolder,'barc')
        if not os.path.exists(barc_folder):
                os.makedirs(barc_folder)
                
        name = 'BARC_' + firenumber + '_' + pre_date + '_' + post_date + '_' + dattype +'_' + str(i) + '_.tif'
        barc_filename = os.path.join(barc_folder,name)
        geemap.ee_export_image(classes_clipped_export.unmask(9).clip(roi), filename=barc_filename, scale=px, file_per_band=False,crs='EPSG:3005')
        ras = gdal.Open(barc_filename,GA_Update)
        dat = ras.GetRasterBand(1)
        dat.SetNoDataValue(9)
        ras = None
        dat = None
         
        ## Export cloudmasks
        pre_cloud_mask_folder = os.path.join(outfolder,'pre_cloud_mask')
        if not os.path.exists(pre_cloud_mask_folder):
                os.makedirs(pre_cloud_mask_folder)
                
        filename = os.path.join(pre_cloud_mask_folder,pre_date + '_cloudmsk_' + str(i) + '.tif')
        geemap.ee_export_image(pre_img_cloudmsk.unmask(9).clip(roi), filename=filename, scale=px, file_per_band=False,crs='EPSG:3005')
        ras = gdal.Open(filename,GA_Update)
        dat = ras.GetRasterBand(1)
        dat.SetNoDataValue(9)
        ras = None
        dat = None
        
        post_cloud_mask_folder = os.path.join(outfolder,'post_cloud_mask')
        if not os.path.exists(post_cloud_mask_folder):
                os.makedirs(post_cloud_mask_folder)
                
        filename = os.path.join(post_cloud_mask_folder,post_date + '_cloudmsk_' + str(i) + '.tif')
        geemap.ee_export_image(post_img_cloudmsk.unmask(9).clip(roi), filename=filename, scale=px, file_per_band=False,crs='EPSG:3005')
        ras = gdal.Open(filename,GA_Update)
        dat = ras.GetRasterBand(1)
        dat.SetNoDataValue(9)
        ras = None
        dat = None
        
        combined_cloud_mask_folder = os.path.join(outfolder,'comb_cloud_mask')
        if not os.path.exists(combined_cloud_mask_folder):
                os.makedirs(combined_cloud_mask_folder)
                
        filename = os.path.join(combined_cloud_mask_folder,pre_date + '_' + post_date + '_comb_cloudmsk_' + str(i) +'.tif')
        geemap.ee_export_image(comb_cloudmsk.unmask(9).clip(roi), filename=filename, scale=px, file_per_band=False,crs='EPSG:3005')
        ras = gdal.Open(filename,GA_Update)
        dat = ras.GetRasterBand(1)
        dat.SetNoDataValue(9)
        ras = None
        dat = None
        
        ## Export 8-bit truecolor images
        #pre, truecolor
        pre_tc_8bit = os.path.join(outfolder,'pre_truecolor_8bit')
        if not os.path.exists(pre_tc_8bit):
                os.makedirs(pre_tc_8bit)
        filename = os.path.join(pre_tc_8bit, dattype + '_' + pre_date + '_truecolor_pre_8bit_' + str(i) + '.tif')
        pre_tc_8bit_path = filename
        if dattype.startswith('S2'):
            viz = {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max':0.3,'gamma':1.5}
            geemap.ee_export_image(pre_img.clip(roi).visualize(**viz), filename=filename, scale=10, file_per_band=False,crs='EPSG:3005')
        elif (dattype == 'L8') | (dattype == 'L9'): 
            viz = {'bands': ['SR_B4', 'SR_B3', 'SR_B2'], 'min': 0, 'max':0.3,'gamma':1.5}
            geemap.ee_export_image(pre_img.clip(roi).visualize(**viz), filename=filename, scale=30, file_per_band=False,crs='EPSG:3005')
        elif (dattype == 'L5') | (dattype == 'L7'):
            viz = {'bands': ['SR_B3','SR_B2','SR_B1'], 'min': 0, 'max':0.3,'gamma':1.5}
            geemap.ee_export_image(pre_img.clip(roi).visualize(**viz), filename=filename, scale=30, file_per_band=False,crs='EPSG:3005')
        else:
            pass
            
        post_tc_8bit = os.path.join(outfolder,'post_truecolor_8bit')
        if not os.path.exists(post_tc_8bit):
                os.makedirs(post_tc_8bit)
        filename = os.path.join(post_tc_8bit, dattype + '_' + post_date + '_truecolor_post_8bit_' + str(i) + '.tif')
        post_tc_8bit_path = filename
        if dattype.startswith('S2'):
            viz = {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max':0.3,'gamma':1.5}
            geemap.ee_export_image(post_img.clip(roi).visualize(**viz), filename=filename, scale=10, file_per_band=False,crs='EPSG:3005')
        elif (dattype == 'L8') | (dattype == 'L9'): 
            viz = {'bands': ['SR_B4', 'SR_B3', 'SR_B2'], 'min': 0, 'max':0.3,'gamma':1.5}
            geemap.ee_export_image(post_img.clip(roi).visualize(**viz), filename=filename, scale=30, file_per_band=False,crs='EPSG:3005')
        elif (dattype == 'L5') | (dattype == 'L7'):
            viz = {'bands': ['SR_B3','SR_B2','SR_B1'],'min': 0, 'max':0.3,'gamma':1.5}
            geemap.ee_export_image(post_img.clip(roi).visualize(**viz), filename=filename, scale=30, file_per_band=False,crs='EPSG:3005')
        else:
            pass
        
        ## Export swir too
        pre_sw_8bit = os.path.join(outfolder,'pre_swir_8bit')
        if not os.path.exists(pre_sw_8bit):
                os.makedirs(pre_sw_8bit)
        filename = os.path.join(pre_sw_8bit, dattype + '_' + pre_date + '_swir_pre_8bit_' + str(i) + '.tif')
        pre_sw_8bit_path = filename
        if dattype.startswith('S2'):
            viz = {'bands': ['B12', 'B8', 'B4'], 'min': 0, 'max':0.3,'gamma':1.5}
            geemap.ee_export_image(pre_img.clip(roi).visualize(**viz), filename=filename, scale=10, file_per_band=False,crs='EPSG:3005')
        elif (dattype == 'L8') | (dattype == 'L9'): 
            viz = {'bands': ['SR_B6', 'SR_B5', 'SR_B4'], 'min': 0, 'max':0.3,'gamma':1.5}
            geemap.ee_export_image(pre_img.clip(roi).visualize(**viz), filename=filename, scale=30, file_per_band=False,crs='EPSG:3005')
        elif (dattype == 'L5') | (dattype == 'L7'):
            viz = {'bands': ['SR_B5','SR_B4','SR_B3'], 'min': 0, 'max':0.3,'gamma':1.5}
            geemap.ee_export_image(pre_img.clip(roi).visualize(**viz), filename=filename, scale=30, file_per_band=False,crs='EPSG:3005')
        else:
            pass
            
        post_sw_8bit = os.path.join(outfolder,'post_swir_8bit')
        if not os.path.exists(post_sw_8bit):
                os.makedirs(post_sw_8bit)
        filename = os.path.join(post_sw_8bit, dattype + '_' + post_date + '_swir_post_8bit_' + str(i) + '.tif')
        post_sw_8bit_path = filename
        if dattype.startswith('S2'):
            viz = {'bands': ['B12', 'B8', 'B4'], 'min': 0, 'max':0.3,'gamma':1.5}
            geemap.ee_export_image(post_img.clip(roi).visualize(**viz), filename=filename, scale=10, file_per_band=False,crs='EPSG:3005')
        elif (dattype == 'L8') | (dattype == 'L9'): 
            viz = {'bands': ['SR_B6', 'SR_B5', 'SR_B4'], 'min': 0, 'max':0.3,'gamma':1.5}
            geemap.ee_export_image(post_img.clip(roi).visualize(**viz), filename=filename, scale=30, file_per_band=False,crs='EPSG:3005')
        elif (dattype == 'L5') | (dattype == 'L7'):
            viz = {'bands': ['SR_B5','SR_B4','SR_B3'],'min': 0, 'max':0.3,'gamma':1.5}
            geemap.ee_export_image(post_img.clip(roi).visualize(**viz), filename=filename, scale=30, file_per_band=False,crs='EPSG:3005')
        else:
            pass
    
    print(barc_folder)
    
    #mosaic all
    #BARC
    barc_list = getfiles(barc_folder,'.tif')
    outfilename = 'BARC_' + firenumber + '_' + pre_date + '_' + post_date + '_' + dattype + '.tif'
    out = os.path.join(barc_folder,outfilename)
    gdal.Warp(out,barc_list)
    for file in barc_list: os.remove(file) #delete tiles
    barc_filename = out #to return from the function
    print('Barc mosaic complete')
    
    # ## cloud masks
    #pre
    pre_cc_list = getfiles(pre_cloud_mask_folder,'.tif')
    outfilename = pre_date + '_cloudmsk.tif'
    out = os.path.join(pre_cloud_mask_folder,outfilename)
    gdal.Warp(out,pre_cc_list)
    for file in pre_cc_list: os.remove(file) #delete tiles
    
    #post
    post_cc_list = getfiles(post_cloud_mask_folder,'.tif')
    outfilename = post_date + '_cloudmsk.tif'
    out = os.path.join(post_cloud_mask_folder,outfilename)
    gdal.Warp(out,post_cc_list)
    for file in post_cc_list: os.remove(file) #delete tiles
    
    #combined
    comb_list = getfiles(combined_cloud_mask_folder,'.tif')
    outfilename = pre_date + '_' + post_date + '_comb_cloudmsk.tif'
    out = os.path.join(combined_cloud_mask_folder,outfilename)
    gdal.Warp(out,comb_list)
    for file in comb_list: os.remove(file) #delete tiles
    print('Cloud masks complete')
    
    #pre truecolour 
    pre_tc_list = getfiles(pre_tc_8bit,'.tif')
    outfilename = dattype + '_' + pre_date + '_truecolor_pre_8bit' + '.tif'
    out = os.path.join(pre_tc_8bit,outfilename)
    gdal.Warp(out,pre_tc_list)
    for file in pre_tc_list: os.remove(file) #delete tiles
    pre_tc_8bit_path = out #to return from the function
    print('Pre truecolor mosaic complete')
    
    #post truecolor
    post_tc_list = getfiles(post_tc_8bit,'.tif')
    outfilename = dattype + '_' + post_date + '_truecolor_post_8bit' + '.tif'
    out = os.path.join(post_tc_8bit,outfilename)
    gdal.Warp(out,post_tc_list)
    for file in post_tc_list: os.remove(file)
    post_tc_8bit_path = out #to return from the function
    print('Post truecolor mosaic complete')
    
    #pre swir
    pre_sw_list = getfiles(pre_sw_8bit,'.tif')
    outfilename = dattype + '_' + pre_date + '_swir_pre_8bit' + '.tif'
    out = os.path.join(pre_sw_8bit,outfilename)
    gdal.Warp(out,pre_sw_list)
    for file in pre_sw_list: os.remove(file) #delete tiles
    pre_sw_8bit_path = out #to return from the function
    print('Pre swir mosaic complete')
    
    #post swir
    post_sw_list = getfiles(post_sw_8bit,'.tif')
    outfilename = dattype + '_' + post_date + '_swir_post_8bit' + '.tif'
    out = os.path.join(post_sw_8bit,outfilename)
    gdal.Warp(out,post_sw_list)
    for file in post_sw_list: os.remove(file)
    post_sw_8bit_path = out #to return from the function
    print('Post swir mosaic complete')


    if opt['export_alt']:
        #export_alternates(altfolder,pre_mosaic_col,post_mosaic_col,dattype,grids)
        rlist = [pre_mosaic_col_export,post_mosaic_col_export]
    else:
        rlist = []
    
    if opt['export_data']:
        print('Export data selected, exporting intermediate products')
        ## Define tiling rules
        poly_area = fires_df[fires_df[opt['fn']] == firenumber].iloc[0][opt['areaha']]
        
        if poly_area < 10000:
            n = 2
        elif poly_area > 10000 and poly_area < 100000:
            n = 3
        elif poly_area > 100000 and poly_area < 400000:
            n = 4
        else: 
            n = 5 
        
        #export pre and post rgbs, watch out for pixel limits (50331648 bytes).
        footprint = poly.geometry().bounds().getInfo()
        grids = grid_footprint(footprint,n,n) #3,3 works for a fire that's ~90 000 ha large, if larger, increase the number of tiles
        
        if dattype.startswith('S2'):
            scale = 20
        else:
            scale = 30
        
        for i in range(0,len(grids)):
            roi = grids[i]
            ## Export dNBR_scaled_int
            dNBR_scaled_folder = os.path.join(outfolder,'dNBR_scaled')
            if not os.path.exists(dNBR_scaled_folder):
                    os.makedirs(dNBR_scaled_folder)
            name = 'dNBR_scaled_' + firenumber + '_' + pre_date + '_' + post_date + '_' + dattype + '_' + str(i) + '.tif'
            filename = os.path.join(dNBR_scaled_folder,name)
            geemap.ee_export_image(dNBR_scaled.clip(roi), filename=filename, scale=scale, file_per_band=False,crs='EPSG:3005')
            
            ## Export dNBR
            dNBR_folder = os.path.join(outfolder,'dNBR')
            if not os.path.exists(dNBR_folder):
                    os.makedirs(dNBR_folder)
            name = 'dNBR_' + firenumber + '_' + pre_date + '_' + post_date + '_' + dattype + '_' + str(i) + '.tif'
            filename = os.path.join(dNBR_folder,name)
            geemap.ee_export_image(dNBR.clip(roi), filename=filename, scale=scale,file_per_band=False,crs='EPSG:3005')

            
            ## Export pre-NBR
            pre_nbr_folder = os.path.join(outfolder,'pre_nbr')
            if not os.path.exists(pre_nbr_folder):
                    os.makedirs(pre_nbr_folder)
            name = 'NBR_' + firenumber + '_' + pre_date + '_' + dattype + '_' + str(i) + '.tif'
            filename = os.path.join(pre_nbr_folder,name)
            geemap.ee_export_image(pre_nbr.clip(roi), filename=filename, scale=scale,file_per_band=False,crs='EPSG:3005')
            

            ## Export post-NBR
            post_nbr_folder = os.path.join(outfolder,'post_nbr')
            if not os.path.exists(post_nbr_folder):
                    os.makedirs(post_nbr_folder)
            name = 'NBR_' + firenumber + '_' + post_date + '_' + dattype + '_' + str(i) + '.tif'
            filename = os.path.join(post_nbr_folder,name)
            geemap.ee_export_image(post_nbr.clip(roi), filename=filename, scale=scale,file_per_band=False,crs='EPSG:3005')
            
            
            ## Export pre, all bands (except 60m for S2)
            
            if dattype.startswith('S2'):
                pre_bands_10m = os.path.join(outfolder,'pre_bands_10m')
                if not os.path.exists(pre_bands_10m):
                        os.makedirs(pre_bands_10m)
                        
                pre_bands_20m = os.path.join(outfolder,'pre_bands_20m')
                if not os.path.exists(pre_bands_20m):
                        os.makedirs(pre_bands_20m)
            elif dattype.startswith('L'):
                pre_bands_30m = os.path.join(outfolder,'pre_bands_30m')
                if not os.path.exists(pre_bands_30m):
                        os.makedirs(pre_bands_30m)
            else:
                pass

            
            if dattype.startswith('S2'):
                filename = os.path.join(pre_bands_10m, dattype + '_' + pre_date + '_B2-B3-B4-B8_pre_' + str(i) + '.tif')
                geemap.ee_export_image(pre_img.clip(roi).select(['B2', 'B3', 'B4','B8']), filename=filename, scale=10, file_per_band=False,crs='EPSG:3005')
                filename = os.path.join(pre_bands_20m, dattype + '_' + pre_date + '_B5-B6-B7-B8A-B11-B12_pre_' + str(i) + '.tif')
                geemap.ee_export_image(pre_img.clip(roi).select(['B5','B6','B7','B8A','B11','B12']), filename=filename, scale=20, file_per_band=False,crs='EPSG:3005')
            elif (dattype == 'L8') | (dattype == 'L9'): 
                #TODO: fix this
                filename = os.path.join(pre_bands_30m, dattype + '_' + pre_date + '_B1-B2-B3-B4-B5-B6-B7_pre_' + str(i) + '.tif')
                geemap.ee_export_image(pre_img.clip(roi).select(['SR_B4', 'SR_B3', 'SR_B2']), filename=filename, scale=30, file_per_band=False,crs='EPSG:3005')
            elif (dattype == 'L5') | (dattype == 'L7'):
                #TODO: fix this
                filename = os.path.join(pre_bands_30m, dattype + '_' + pre_date + '_B1-B2-B3-B4-B5-B7_pre_' + str(i) + '.tif')
                geemap.ee_export_image(pre_img.clip(roi).select(['SR_B3','SR_B2','SR_B1']), filename=filename, scale=30, file_per_band=False,crs='EPSG:3005')
            else:
                pass
            
            ## Export post, all bands (except 60m for S2)
            if dattype.startswith('S2'):
                post_bands_10m = os.path.join(outfolder,'post_bands_10m')
                if not os.path.exists(post_bands_10m):
                        os.makedirs(post_bands_10m)
                        
                post_bands_20m = os.path.join(outfolder,'post_bands_20m')
                if not os.path.exists(post_bands_20m):
                        os.makedirs(post_bands_20m)
            elif dattype.startswith('L'):
                post_bands_30m = os.path.join(outfolder,'post_bands_30m')
                if not os.path.exists(post_bands_30m):
                        os.makedirs(post_bands_30m)
            else:
                pass

            if dattype.startswith('S2'):
                filename = os.path.join(post_bands_10m, dattype + '_' + post_date + '_B2-B3-B4-B8_post_' + str(i) + '.tif')
                geemap.ee_export_image(post_img.clip(roi).select(['B2', 'B3', 'B4','B8']), filename=filename, scale=10, file_per_band=False,crs='EPSG:3005')
                filename = os.path.join(post_bands_20m, dattype + '_' + post_date + '_B5-B6-B7-B8A-B11-B12_post_' + str(i) + '.tif')
                geemap.ee_export_image(post_img.clip(roi).select(['B5','B6', 'B7','B8A','B11','B12']), filename=filename, scale=20, file_per_band=False,crs='EPSG:3005')
            elif (dattype == 'L8') | (dattype == 'L9'): 
                filename = os.path.join(post_bands_30m, dattype + '_' + post_date + '_B1-B2-B3-B4-B5-B6-B7_post_' + str(i) + '.tif')
                geemap.ee_export_image(post_img.clip(roi).select(['SR_B1','SR_B2','SR_B3','SR_B4','SR_B5','SR_B6','SR_B7']), filename=filename, scale=30, region=roi, file_per_band=False,crs='EPSG:3005')
            elif(dattype == 'L5') | (dattype == 'L7'):
                filename = os.path.join(post_bands_30m, dattype + '_' + post_date + '_B1-B2-B3-B4-B5-B7_post_' + str(i) + '.tif')
                geemap.ee_export_image(post_img.clip(roi).select(['SR_B1','SR_B2','SR_B3','SR_B4','SR_B5','SR_B7']), filename=filename, scale=30, region=roi, file_per_band=False,crs='EPSG:3005')
            else:
                pass
            
            
            # #pre, truecolor
            # pre_tc = os.path.join(outfolder,'pre_truecolor')
            # if not os.path.exists(pre_tc):
            #         os.makedirs(pre_tc)
            # filename = os.path.join(pre_tc, dattype + '_' + pre_date + '_truecolor_pre_' + str(i) + '.tif')
            # if dattype.startswith('S2'):
            #     geemap.ee_export_image(pre_img.clip(roi).select(['B4', 'B3', 'B2']), filename=filename, scale=10, file_per_band=False,crs='EPSG:3005')
            # elif (dattype == 'L8') | (dattype == 'L9'): 
            #     geemap.ee_export_image(pre_img.clip(roi).select(['SR_B4', 'SR_B3', 'SR_B2']), filename=filename, scale=30, file_per_band=False,crs='EPSG:3005')
            # elif (dattype == 'L5') | (dattype == 'L7'):
            #     geemap.ee_export_image(pre_img.clip(roi).select(['SR_B3','SR_B2','SR_B1']), filename=filename, scale=30, file_per_band=False,crs='EPSG:3005')
            # else:
            #     pass
        
            # #pre, swir
            # pre_swir = os.path.join(outfolder,'pre_swir')
            # if not os.path.exists(pre_swir):
            #         os.makedirs(pre_swir)
        
            # filename = os.path.join(pre_swir, dattype + '_' + pre_date + '_SWIR_pre_' + str(i) + '.tif')
            # if dattype.startswith('S2'):
            #     geemap.ee_export_image(pre_img.clip(roi).select(['B12','B8','B4']), filename=filename, scale=20, file_per_band=False,crs='EPSG:3005')
            # elif (dattype == 'L8') | (dattype == 'L9'): 
            #     geemap.ee_export_image(pre_img.clip(roi).select(['SR_B7','SR_B5','SR_B4']), filename=filename, scale=30, file_per_band=False,crs='EPSG:3005')
            # elif (dattype == 'L5') | (dattype == 'L7'):
            #     geemap.ee_export_image(pre_img.clip(roi).select(['SR_B7','SR_B4','SR_B3']), filename=filename, scale=30, file_per_band=False,crs='EPSG:3005')
            # else:
            #     pass
                
            # #post, truecolor
            # post_tc = os.path.join(outfolder,'post_truecolor')
            # if not os.path.exists(post_tc):
            #         os.makedirs(post_tc)
        
            # filename = os.path.join(post_tc, dattype + '_' + post_date + '_truecolor_post_' + str(i) + '.tif')
            # if dattype.startswith('S2'):
            #     geemap.ee_export_image(post_img.clip(roi).select(['B4', 'B3', 'B2']), filename=filename, scale=10, region=roi, file_per_band=False,crs='EPSG:3005')
            # elif (dattype == 'L8') | (dattype == 'L9'): 
            #     geemap.ee_export_image(post_img.clip(roi).select(['SR_B4', 'SR_B3', 'SR_B2']), filename=filename, scale=30, region=roi, file_per_band=False,crs='EPSG:3005')
            # elif(dattype == 'L5') | (dattype == 'L7'):
            #     geemap.ee_export_image(post_img.clip(roi).select(['SR_B3','SR_B2','SR_B1']), filename=filename, scale=30, region=roi, file_per_band=False,crs='EPSG:3005')
            # else:
            #     pass
                
            # #post, swir
            # post_swir = os.path.join(outfolder,'post_swir')
            # if not os.path.exists(post_swir):
            #         os.makedirs(post_swir)
            # filename = os.path.join(post_swir, dattype + '_' + post_date + '_SWIR_post_' + str(i) + '.tif')
            # if dattype.startswith('S2'):
            #     geemap.ee_export_image(post_img.clip(roi).select(['B12','B8','B4']), filename=filename, scale=20, region=roi, file_per_band=False,crs='EPSG:3005')
            # elif (dattype == 'L8') | (dattype == 'L9'):
            #     geemap.ee_export_image(post_img.clip(roi).select(['SR_B7','SR_B5','SR_B4']), filename=filename, scale=30, file_per_band=False,crs='EPSG:3005')
            # elif (dattype == 'L5') | (dattype == 'L7'):
            #     geemap.ee_export_image(post_img.clip(roi).select(['SR_B7','SR_B4','SR_B3']), filename=filename, scale=30, file_per_band=False,crs='EPSG:3005')
            # else:
            #     pass
        
        #mosaic data
        #dNBR
        filelist = getfiles(dNBR_folder,'.tif')
        outfilename = 'dNBR_' + firenumber + '_' + pre_date + '_' + post_date + '_' + dattype + '.tif'
        out = os.path.join(dNBR_folder,outfilename)
        gdal.Warp(out,filelist)
        for file in filelist: os.remove(file) #delete tiles
        print('dNBR mosaic complete')
        
        #dNBR scaled
        filelist = getfiles(dNBR_scaled_folder,'.tif')
        outfilename = 'dNBR_scaled_' + firenumber + '_' + pre_date + '_' + post_date + '_' + dattype + '.tif'
        out = os.path.join(dNBR_scaled_folder,outfilename)
        gdal.Warp(out,filelist)
        for file in filelist: os.remove(file) #delete tiles
        print('dNBR scaled mosaic complete')
        
        #pre NBR
        filelist = getfiles(pre_nbr_folder,'.tif')
        outfilename = 'NBR_' + firenumber + '_' + pre_date + '_' + dattype + '.tif'
        out = os.path.join(pre_nbr_folder,outfilename)
        gdal.Warp(out,filelist)
        for file in filelist: os.remove(file) #delete tiles
        print('pre-fire NBR mosaic complete')
        
        #post NBR
        filelist = getfiles(post_nbr_folder,'.tif')
        outfilename = 'NBR_' + firenumber + '_' + post_date + '_' + dattype + '.tif'
        out = os.path.join(post_nbr_folder,outfilename)
        gdal.Warp(out,filelist)
        for file in filelist: os.remove(file) #delete tiles
        print('post-fire NBR mosaic complete')
        
        if dattype.startswith('S2'):
            #pre 10m bands
            filelist = getfiles(pre_bands_10m,'.tif')
            outfilename = 'B2-B3-B4-B8_10m_' + firenumber + '_' + pre_date + '_' + dattype + '.tif'
            out = os.path.join(pre_bands_10m,outfilename)
            gdal.Warp(out,filelist)
            for file in filelist: os.remove(file) #delete tiles
            print('pre-fire 10m bands mosaic complete')
            
            #pre 20m bands
            filelist = getfiles(pre_bands_20m,'.tif')
            outfilename = 'B5-B6-B7-B8A-B11-B12_20m_' + firenumber + '_' + pre_date + '_' + dattype + '.tif'
            out = os.path.join(pre_bands_20m,outfilename)
            gdal.Warp(out,filelist)
            for file in filelist: os.remove(file) #delete tiles
            print('pre-fire 20m bands mosaic complete')
            
            #post 10m bands
            filelist = getfiles(post_bands_10m,'.tif')
            outfilename = 'B2-B3-B4-B8_10m_' + firenumber + '_' + post_date + '_' + dattype + '.tif'
            out = os.path.join(post_bands_10m,outfilename)
            gdal.Warp(out,filelist)
            for file in filelist: os.remove(file) #delete tiles
            print('post-fire 10m bands mosaic complete')
            
            #post 20m bands
            filelist = getfiles(post_bands_20m,'.tif')
            outfilename = 'B5-B6-B7-B8A-B11-B12_20m_' + firenumber + '_' + post_date + '_' + dattype + '.tif'
            out = os.path.join(post_bands_20m,outfilename)
            gdal.Warp(out,filelist)
            for file in filelist: os.remove(file) #delete tiles
            print('post-fire 20m bands mosaic complete')
        
        elif (dattype == 'L8') | (dattype == 'L9'): 
            #pre 30m bands
            filelist = getfiles(pre_bands_30m,'.tif')
            outfilename = 'B1-B2-B3-B4-B5-B6-B7_30m_' + firenumber + '_' + pre_date + '_' + dattype + '.tif'
            out = os.path.join(pre_bands_30m,outfilename)
            gdal.Warp(out,filelist)
            for file in filelist: os.remove(file) #delete tiles
            print('pre-fire 30m bands mosaic complete')
            
            #pre 30m bands
            filelist = getfiles(post_bands_30m,'.tif')
            outfilename = 'B1-B2-B3-B4-B5-B6-B7_30m_' + firenumber + '_' + post_date + '_' + dattype + '.tif'
            out = os.path.join(post_bands_30m,outfilename)
            gdal.Warp(out,filelist)
            for file in filelist: os.remove(file) #delete tiles
            print('post-fire 30m bands mosaic complete')
        
        elif (dattype == 'L5') | (dattype == 'L7'): 
            #pre 30m bands
            filelist = getfiles(pre_bands_30m,'.tif')
            outfilename = 'B1-B2-B3-B4-B5-B7_30m_' + firenumber + '_' + pre_date + '_' + dattype + '.tif'
            out = os.path.join(pre_bands_30m,outfilename)
            gdal.Warp(out,filelist)
            for file in filelist: os.remove(file) #delete tiles
            print('pre-fire 30m bands mosaic complete')
            
            #pre 30m bands
            filelist = getfiles(post_bands_30m,'.tif')
            outfilename = 'B1-B2-B3-B4-B5-B7_30m_' + firenumber + '_' + post_date + '_' + dattype + '.tif'
            out = os.path.join(post_bands_30m,outfilename)
            gdal.Warp(out,filelist)
            for file in filelist: os.remove(file) #delete tiles
            print('post-fire 30m bands mosaic complete')
        
        else:
            pass
            
    #add missing parameters
    searchd['pre_mosaic_date'] = pre_mosaic_date
    searchd['post_mosaic_date'] = post_mosaic_date
    
    #Add scene ids with the same pre-date
    searchd['pre_scenes'] = pre_scenes_info
    
    #Add scene ids with the same post-date
    searchd['post_scenes'] = post_scenes_info
    
    #Add fire area
    searchd['fire_area_ha'] = poly_area
    
    #write search parameters to the folder as a text file
    params = os.path.join(outfolder,'search_params.txt')
    with open(params, 'w') as f: 
        for key, value in searchd.items(): 
            f.write('%s:%s\n' % (key, value))
    
    #write search parameters to the folder as json for use later
    output_json = os.path.join(outfolder,'search_params.json')
    with open(output_json, 'w') as json_file:
        json.dump(searchd, json_file, indent=4)
    
    print(firenumber + ' complete')
    return(barc_filename,pre_sw_8bit_path,post_sw_8bit_path,pre_tc_8bit_path,post_tc_8bit_path,rlist)

