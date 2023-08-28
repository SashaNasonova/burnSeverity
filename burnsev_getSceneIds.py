# -*- coding: utf-8 -*-
"""
Created on Tue Dec 13 14:03:07 2022

@author: snasonov
"""
import os 
from pathlib import Path
import pandas as pd

#fires folder
def getfiles(d,ext):
    paths = []
    for file in os.listdir(d):
        if file.endswith(ext):
            paths.append(os.path.join(d, file))
    return(paths) 

f = r'C:\Data\Burn_Severity\same_year_2023\interim\output\S2'
fires = os.listdir(f)
print(fires)

barc_final = r'C:\Data\Burn_Severity\same_year_2023\interim\filtered' #get values from these file names because they are consistent, fix in the future
barcs = os.listdir(barc_final)

#new dict for sceneIds

d = dict.fromkeys(fires)

df = pd.DataFrame(data=None,columns=['barc_tif','PRE_FIRE_IMAGE','POST_FIRE_IMAGE'])

for fire in list(d.keys()):
    fire_folder = os.path.join(f,fire) 
    
    barc = [s for s in barcs if all(sf in s for sf in [fire])][0]
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
    
    #reformat date for S2 (yymmdd) for landsat it's (yyyy-mm-dd)
    if sensor == 'S2':
        pre_date_f = pre_date
        post_date_f = post_date
    else:
        pre_date_f = pre_date[0:4] + '-' + pre_date[4:6] + '-' + pre_date[6:8]
        post_date_f = post_date[0:4] + '-' + post_date[4:6] + '-' + post_date[6:8]
    
    #open pre_sceneMetadata.csv
    pre_df = pd.read_csv(os.path.join(f,fire,'pre_sceneMetadata.csv'))
    post_df = pd.read_csv(os.path.join(f,fire,'post_sceneMetadata.csv'))
    pre_df['date'] = pre_df['date'].astype(str)
    post_df['date'] = post_df['date'].astype(str)
    
    #subset dataframes by date
    pre_df_sub = pre_df.loc[pre_df['date']==pre_date_f]
    post_df_sub = post_df.loc[post_df['date']==post_date_f]
    
    #get PRODUCT_ID for S2 or LANDSAT_SCENE_ID for L8/L9
    if sensor == 'S2':
        pre_scenes = pre_df_sub['PRODUCT_ID'].tolist()
        post_scenes = post_df_sub['PRODUCT_ID'].tolist()
    else:
        pre_scenes = pre_df_sub['LANDSAT_SCENE_ID'].tolist()
        post_scenes = post_df_sub['LANDSAT_SCENE_ID'].tolist()
    
    #populate dictionary
    d[fire]={}
    d[fire]['barc'] = name
    d[fire]['pre_scenes'] = pre_scenes
    d[fire]['post_scenes'] = post_scenes
    
    #convert list to a comma separated string
    pre_scenes_str = ','.join(pre_scenes)
    post_scenes_str = ','.join(post_scenes)
    d[fire]['pre_scenes_str'] = pre_scenes_str
    d[fire]['post_scenes_str'] = post_scenes_str
    
    #append to barc_tif, pre_scenes_str and post_scenes_str to df
    df_list = [name,pre_scenes_str,post_scenes_str]
    df.loc[len(df)] = df_list

#write df to csv
df.to_csv(os.path.join(f,'sceneIds.csv'))
    
    #print(pre_scenes)
    #print(post_scenes)
    
    # if len(pre_scenes) == 0 | len(post_scenes)==0:
    #     print(fire + ' failed')
        
    
    
    
    
