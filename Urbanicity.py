Python 3.6.4 (v3.6.4:d48eceb, Dec 19 2017, 06:54:40) [MSC v.1900 64 bit (AMD64)] on win32
Type "copyright", "credits" or "license()" for more information.
>>> 
import arcpy
from arcpy import env
from arcpy.sa import *
import os
import numpy

Workspace = "D:\\PeterWhitman_Data\\Projects\\Urbanicity" #Identify workspace
StudyArea = Workspace + "\\BC_Boundary.shp" #Read study area boundary file
out_coord_system = arcpy.SpatialReference('NAD 1983 BC Environment Albers')

arcpy.env.workspace = Workspace
dataList = arcpy.ListFiles("*Project.tif")
for i in dataList:
	filename = os.path.splitext(i)[0]
	outExtractByMask = arcpy.sa.ExtractByMask(i, StudyArea)
	ClipName = Workspace + "\\Clipped" + filename + ".tif"
	outExtractByMask.save(ClipName)

ClippedPopDen_Project = Workspace + "\\ClippedPopDen_Project.tif"
ClippedAccessibility_Project = Workspace + "\\ClippedAccessibility_Project.tif"
ClippedBuiltUp_Project = Workspace + "\\ClippedBuiltUp_Project.tif"

MaxValue_PopDen_Project = arcpy.GetRasterProperties_management(ClippedPopDen_Project, "MAXIMUM")
PopDen_Reclass = arcpy.sa.Reclassify(ClippedPopDen_Project, "Value", RemapRange([[0, 0.99999, 10],[1, 74.9, 20],[75, 374.9, 30], [375, MaxValue_PopDen_Project, 40]]), "NODATA")
PopDen_Reclass.save(Workspace + "\\PopDen_Reclass.tif")

BuiltUp_Reclass = arcpy.sa.Reclassify(ClippedBuiltUp_Project, "Value", RemapRange([[0, 0.5, 0],[0.51, 1, 1]]), "NODATA")
BuiltUp_Reclass.save(Workspace + "\\BuiltUp_Reclass.tif")

outCon = arcpy.sa.Con(Raster(ClippedAccessibility_Project) > -1, ClippedAccessibility_Project)
outCon.save(Workspace + "\\ClippedAccess_NoData.tif")
ClippedAccessibility_Project = Workspace + "\\ClippedAccess_NoData.tif"

ClipAccess_Project = Workspace + "\\ClipAccess_Project.tif"
arcpy.CopyRaster_management(ClippedAccessibility_Project, ClipAccess_Project, "16_BIT_UNSIGNED")

MaxValue_Access_Project = arcpy.GetRasterProperties_management(ClipAccess_Project, "MAXIMUM")
MaxAccess = int(float(MaxValue_Access_Project.getOutput(0)))

a = arcpy.RasterToNumPyArray(ClipAccess_Project)
b = numpy.array(a)
c = b[b>-1] 
n_98 = numpy.percentile(c, 0.2)
n_97 = numpy.percentile(c, 0.2) + 1

Access_Reclass = arcpy.sa.Reclassify(ClipAccess_Project, "Value", RemapRange([[0, n_98, 1], [n_97, MaxAccess, "NODATA"]]), "NODATA")
Access_Reclass.save(Workspace + "\\Access_Reclass.tif")

#Set Urban Cluster and Urban Center Threshold:
UrbanCenter_Thresh = 49,999
UrbanCluster_Thresh = 4,999 

#Combine the built up and population density raster datasets
BuiltUp_Reclass = Workspace + "\\BuiltUp_Reclass.tif"
PopDen_Reclass = Workspace + "\\PopDen_Reclass.tif"
BuiltUp_PopDen = Workspace + "\\BuiltUp_PopDen.tif"
Combined = Raster(BuiltUp_Reclass) + Raster(PopDen_Reclass)
Combined.save(BuiltUp_PopDen)

#Identify urban centers
OutRaster = arcpy.sa.ExtractByAttributes(BuiltUp_PopDen, "Value > 39 OR Value = 21 OR Value = 31")
outRegionGrp = RegionGroup(OutRaster, "FOUR", "CROSS", "NO_LINK")

PotentialCenterRegions = Workspace + "\\PotentialCenterRegions.shp"
arcpy.RasterToPolygon_conversion(outRegionGrp, PotentialCenterRegions, "NO_SIMPLIFY", "VALUE")
Centers_NoIslands = Workspace + "\\Centers_NoIslands.shp"
arcpy.EliminatePolygonPart_management(PotentialCenterRegions, Centers_NoIslands, "AREA", 10000000, "", "CONTAINED_ONLY")

PopDen = Workspace + "\\ClippedPopDen_Project.tif"
CenterZonalStatistics = arcpy.sa.ZonalStatistics(Centers_NoIslands, "gridcode", PopDen, "SUM")
UrbanCenter = arcpy.sa.ExtractByAttributes(CenterZonalStatistics, "Value > 49999")
UrbanCenter.save(Workspace + "\\UrbanCenters.tif")

UrbanCenter = Workspace + "\\UrbanCenters.tif"
MaxValue_Center = arcpy.GetRasterProperties_management(UrbanCenter, "MAXIMUM")
MaxCenter = int(float(MaxValue_Center.getOutput(0)))
UrbanCenter_Reclass = arcpy.sa.Reclassify(UrbanCenter, "Value", RemapRange([[1, MaxCenter, 5]]))
UrbanCenter_Reclass.save(Workspace + "\\UrbanCenter_Reclassed.tif")
UrbanCenter_Reclass = Workspace + "\\UrbanCenter_Reclassed.tif"
outSetNull = SetNull(~(IsNull(UrbanCenter_Reclass)), BuiltUp_PopDen)

#Identify areas with zero population
NoPopulation = arcpy.sa.ExtractByAttributes(outSetNull, "Value < 12")
outSetNull2 = SetNull(~(IsNull(NoPopulation)), outSetNull)
NoPopulation_Reclass = arcpy.sa.Reclassify(NoPopulation, "Value", RemapRange([[10, 11, 1]]))
NoPopulation_Reclass.save(Workspace + "\\NoPopulation_Reclassed.tif")

#Identify urban clusters
OutRaster2 = arcpy.sa.ExtractByAttributes(outSetNull2, "Value > 29")
ClusterRegions = RegionGroup(OutRaster2, "EIGHT", "CROSS", "NO_LINK")

PopDen = Workspace + "\\ClippedPopDen_Project.tif"
ClusterZonalStatistics = arcpy.sa.ZonalStatistics(ClusterRegions, "VALUE", PopDen, "SUM")
UrbanCluster = arcpy.sa.ExtractByAttributes(ClusterZonalStatistics, "Value > 4999")
UrbanCluster.save(Workspace + "\\UrbanClusters.tif")

UrbanCluster = Workspace + "\\UrbanClusters.tif"
MaxValue_Cluster = arcpy.GetRasterProperties_management(UrbanCluster, "MAXIMUM")
MaxCluster = int(float(MaxValue_Cluster.getOutput(0)))
UrbanCluster_Reclass = arcpy.sa.Reclassify(UrbanCluster, "Value", RemapRange([[1, MaxValue_Cluster, 4]]))
UrbanCluster_Reclass.save(Workspace + "\\UrbanCluster_Reclassed.tif")
outSetNull3 = SetNull(~(IsNull(UrbanCluster)), outSetNull2)

#Identify suburban areas
Access_Reclass = Workspace + "\\Access_Reclass.tif"
SuburbanAreas = SetNull(IsNull(Access_Reclass), outSetNull3)
SuburbanAreas_Reclass = arcpy.sa.Reclassify(SuburbanAreas, "Value", RemapRange([[1, 41, 3]]))
SuburbanAreas_Reclass.save(Workspace + "\\SuburbanAreas_Reclassed.tif")

#Identify rural areas
RuralAreas = SetNull(~(IsNull(SuburbanAreas_Reclass)), outSetNull3)
Rural_Reclass = arcpy.sa.Reclassify(RuralAreas, "Value", RemapRange([[1, 41, 2]]))
Rural_Reclass.save(Workspace + "\\Rural_Reclassed.tif")

#Mosaic each settlement type to new raster
t = arcpy.ListFiles("*Reclassed.tif")
arcpy.MosaicToNewRaster_management(t, Workspace, "Urbanicity.tif", out_coord_system, "16_BIT_UNSIGNED","250", "1")
