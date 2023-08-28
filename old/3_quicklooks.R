library(raster)
library(grid)
library(RStoolbox)
library(rgdal)
library(ggplot2)

finaldir <- 'C:/Data/Burn_Severity/ElephantHill/outputs/L8'
qadir <- 'C:/Data/Burn_Severity/ElephantHill/qa'

if (!dir.exists(qadir)) {dir.create(qadir)}
if (!dir.exists(file.path(qadir,'pre'))) {dir.create(file.path(qadir,'pre'))}
if (!dir.exists(file.path(qadir,'post'))) {dir.create(file.path(qadir,'post'))}
if (!dir.exists(file.path(qadir,'barc'))) {dir.create(file.path(qadir,'barc'))}

#read shapefile
s <- "C:/Data/Burn_Severity/ElephantHill/vectors/WHSE_LAND_AND_NATURAL_RESOURCE.PROT_HISTORICAL_FIRE_POLYS_SP_ElephantHill.shp"
dfs <- readOGR(s)

#get all folders 
dirs = list.dirs(finaldir,full.names = F, recursive = F)

dirs = c("K20637_V3")

for (f in dirs){
print(f)
###get fire vector
dfs_sub <- dfs[dfs$FIRE_NUMBE %in% f, ]

###read in pre_mosaic
d <-'pre_truecolor'
fl <- 'pre'
mosaic <- list.files(path = file.path(finaldir,f,d), pattern='_mosaic.tif$') #$ means end of the string
b <- raster::stack(file.path(finaldir,f,d,mosaic))
p <- ggRGB(img=b,r=1,g=2,b=3,stretch="lin",quantiles=c(0.1,0.98)) +
  geom_polygon(aes(x=long,y=lat,group=group),colour='red',fill=NA,dfs_sub)+theme_void()

qa_name <- paste0(f,'.png')
#export pre truecolor mosaic quicklook
qa <- file.path(qadir,fl)
qlname = file.path(qa,qa_name)
ggsave(qlname,width=10,height=13,units='cm')

# ###read in post mosaic 
d <-'post_truecolor'
fl <- 'post'
mosaic <- list.files(path = file.path(finaldir,f,d), pattern='_mosaic.tif$') #$ means end of the string
b <- raster::stack(file.path(finaldir,f,d,mosaic))
p <- ggRGB(img=b,r=1,g=2,b=3,stretch="lin",quantiles=c(0.1,0.98)) +
  geom_polygon(aes(x=long,y=lat,group=group),colour='red',fill=NA,dfs_sub)+theme_void()

qa_name <- paste0(f,'.png')
#export post truecolor mosaic quicklook
qa <- file.path(qadir,fl)
qlname = file.path(qa,qa_name)
ggsave(qlname,width=10,height=13,units='cm')
# 
# ###read in barc 
fl <- 'barc'
barc_mosaic <- list.files(path = file.path(finaldir,f), pattern='^BARC.*tif$') #$ means end of the string
barc <- raster::brick(file.path(finaldir,f,barc_mosaic))
names(barc) <- fl
p <-  ggRGB(img=b,r=1,g=2,b=3,stretch="lin",quantiles=c(0.1,0.98)) +
  geom_raster(data=barc,aes(x=x,y=y,fill=as.factor(barc))) +
  scale_fill_manual(values = c("0"="black","1"="grey","2"="yellow","3"="orange","4"="red"),na.value=NA) +
  geom_polygon(aes(x=long,y=lat,group=group),colour='red',fill=NA,dfs_sub)+theme_void()+ theme(legend.position="none")

qa_name <- paste0(f,'.png')
#export barc quicklook
qa <- file.path(qadir,fl)
qlname = file.path(qa,qa_name)
ggsave(qlname,width=10,height=13,units='cm')
}