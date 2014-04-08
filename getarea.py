import sys, os, math
from pycontainers import compressedfile, qsfs
import slippy

if __name__=="__main__":
	
	spatialIndex = qsfs.Qsfs(compressedfile.CompressedFile("uk.spatial"))

	queryArea = [-0.5142975,51.2413932,-0.4645157,51.2738368] #left,bottom,right,top
	zoomLevel = 11

	#Determine which data tiles to check for query
	tl = slippy.deg2numf(queryArea[3], queryArea[0], zoomLevel)
	br = slippy.deg2numf(queryArea[1], queryArea[2], zoomLevel)

	xr = range(int(math.floor(tl[0])), int(math.ceil(br[0])))
	yr = range(int(math.floor(tl[1])), int(math.ceil(br[1])))

	print tl, br
	
	print xr, yr

	print spatialIndex.listdir("/11/1022")


	
