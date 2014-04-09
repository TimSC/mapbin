import sys, os, math, struct
from pycontainers import compressedfile, qsfs, hashtable
import slippy
import xml.etree.ElementTree as ET

class OsmObjectStore(object):
	def __init__(self, fina="ukdump"):

		self.mainData = compressedfile.CompressedFile(fina, readOnly = True)
		self.ns = hashtable.HashTableFile(compressedfile.CompressedFile(fina+"nodestart.hash", readOnly = True), readOnly = True)
		self.ne = hashtable.HashTableFile(compressedfile.CompressedFile(fina+"nodeend.hash", readOnly = True), readOnly = True)
		self.ws = hashtable.HashTableFile(compressedfile.CompressedFile(fina+"nodestart.hash", readOnly = True), readOnly = True)
		self.we = hashtable.HashTableFile(compressedfile.CompressedFile(fina+"nodeend.hash", readOnly = True), readOnly = True)
		self.rs = hashtable.HashTableFile(compressedfile.CompressedFile(fina+"nodestart.hash", readOnly = True), readOnly = True)
		self.re = hashtable.HashTableFile(compressedfile.CompressedFile(fina+"nodeend.hash", readOnly = True), readOnly = True)

	def Get(self, objType, objId, objVer):
		startPos = None
		endPos = None
		if objType == "node":
			startPos = self.ns[objId][objVer]
			endPos = self.ne[objId][objVer]

		if objType == "way":
			startPos = self.ws[objId][objVer]
			endPos = self.we[objId][objVer]

		if objType == "relation":
			startPos = self.rs[objId][objVer]
			endPos = self.re[objId][objVer]

		if startPos is None or endPos is None:
			return None

		self.mainData.seek(startPos)
		return self.mainData.read(endPos - startPos)

if __name__=="__main__":
	
	spatialIndex = qsfs.Qsfs(compressedfile.CompressedFile("uk.spatial"))

	queryArea = [-0.5142975,51.2413932,-0.4645157,51.2738368] #left,bottom,right,top
	zoomLevel = 11

	#Determine which data tiles to check for query
	tl = slippy.deg2numf(queryArea[3], queryArea[0], zoomLevel)
	br = slippy.deg2numf(queryArea[1], queryArea[2], zoomLevel)

	xr = range(int(math.floor(tl[0])), int(math.ceil(br[0])))
	yr = range(int(math.floor(tl[1])), int(math.ceil(br[1])))

	print "Getting nodes from tile ranges", xr, yr
	nodeEntry = struct.Struct(">QI")

	#Get candidate nodes from spatial index
	candidateNodes = {}
	for tilex in xr:
		for tiley in yr:
			tileFina = "/{0}/{1}/{2}.dat".format(zoomLevel, tilex, tiley)
			if not spatialIndex.exists(tileFina):
				continue
			print tilex, tiley
			fi = spatialIndex.open(tileFina)
			numNodeEntries = len(fi) / nodeEntry.size
			for nodeNum in range(numNodeEntries):
				fi.seek(nodeNum * nodeEntry.size)
				nodeId, nodeVer = nodeEntry.unpack(fi.read(nodeEntry.size))
				if nodeId not in candidateNodes:
					candidateNodes[nodeId] = nodeVer
				else:
					#Retain latest version
					if nodeVer > candidateNodes[nodeId]:
						candidateNodes[nodeId] = nodeVer

	#Check these are the latest known version of the node
	nodeVersions = hashtable.HashTableFile(compressedfile.CompressedFile("uk.vnode"), readOnly = True)
	currentNodes = {}
	for nodeId in candidateNodes:
		try:
			latestVer = nodeVersions[nodeId]
			foundVer = candidateNodes[nodeId]
			#print nodeId, latestVer, foundVer
			if latestVer == foundVer:
				currentNodes[nodeId] = foundVer
		except:
			print "Missing node", nodeId

	print "Num candidate nodes", len(currentNodes)

	#Filter to find those in bounding box
	osmObjectStore = OsmObjectStore("ukdump")	
	for nodeId in currentNodes:
		objStr = osmObjectStore.Get("node", nodeId, currentNodes[nodeId])
		print nodeId, "'"+objStr+"'"
		print len(objStr)
		nodeXmlTree = ET.fromstring("<?xml version='1.0' encoding='UTF-8'?>\n"+objStr)
		nodeXmlRoot = nodeXmlTree.getroot()
		print nodeXmlRoot.attrib

	#print spatialIndex.listdir("/11/1022")

	print "Close spatial index"
	del spatialIndex

	print "Close node versions"
	del nodeVersions
	
	

	print "All done"

