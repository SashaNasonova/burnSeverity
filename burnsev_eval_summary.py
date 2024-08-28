# -*- coding: utf-8 -*-
"""
Created on Tue Aug 13 10:47:45 2024

@author: snasonov
"""
import os
import pandas as pd

def getfiles(d,ext):
    paths = []
    for file in os.listdir(d):
        if file.endswith(ext):
            paths.append(os.path.join(d, file))
    return(paths) 

def summary(root=None,filename=None):
    
    d = {'date': 'image acqusition date',
        'percent_coverage':'percent of the fire perimeter that has been imaged (%)',
        'percent_cc': 'percent cloud cover within the fire perimeter (%)',
        'mean_aot': 'mean aerosol optical thickness within the fire perimeter (unitless, typical range of values 0 - 0.6)',
        'percent_cc_scene':'cloud cover from scene metadata (%)',
        'sensor':'imaging platform (s2 = sentinel-2, l8 = landsat-8, l9 = landsat-9)'}
    
    d_df = pd.DataFrame.from_dict(d,orient='index',columns=['Description'])
    data_dictionary = {'data_dictionary':d_df} 
    
    sensors = os.listdir(os.path.join(root,'output'))
    firelist = os.listdir(os.path.join(root,'output',sensors[0]))
    
    all_outputs = {}
    for f in firelist:
        dfs = []
        
        s2_file = os.path.join(root,'output','s2',f,filename)
        if os.path.exists(s2_file):    
            s2 = pd.DataFrame(pd.read_csv(s2_file))
            s2['sensor'] = 's2'
            dfs.append(s2)
        
        l8_file = os.path.join(root,'output','l8',f,filename)
        if os.path.exists(l8_file):    
            l8 = pd.DataFrame(pd.read_csv(l8_file))
            l8['sensor'] = 'l8'
            dfs.append(l8)
        
        l9_file = os.path.join(root,'output','l9',f,filename)
        if os.path.exists(l9_file):    
            l9 = pd.DataFrame(pd.read_csv(l9_file))
            l9['sensor'] = 'l9'
            dfs.append(l9)
        
        outdf = pd.concat(dfs)
        outdf = outdf.rename(columns={'Unnamed: 0':'date'})
        outdf = outdf.sort_values(by='date')
        outdf = outdf.drop(columns=['sum','count','sum_cc','count_cc'])
        
        all_outputs[f] = outdf
    
    # Write to spreadsheet  
    outfilename = os.path.join(root,filename[:-4]+'_eval.xlsx')
    with pd.ExcelWriter(outfilename, engine='xlsxwriter') as writer:
        d_df.to_excel(writer, sheet_name='data_dictionary', index=True)
        for sheet_name, df in all_outputs.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)

root = r'E:\burnSeverity\interim_2024\for_Don'
filename = 'post_mosaicMetadata.csv'
summary(root,filename)