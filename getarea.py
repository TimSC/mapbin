import sys, os, math, struct, pickle, bz2
from pycontainers import compressedfile, qsfs, hashtable
import slippy
import xml.etree.ElementTree as ET

class OsmObjectStore(object):
	def __init__(self, fina="dat"):

		self.mainData = compressedfile.CompressedFile(fina+"/data", readOnly = True)
		self.ns = hashtable.HashTableFile(compressedfile.CompressedFile(fina+"/datanodestart.hash", readOnly = True), readOnly = True)
		self.ne = hashtable.HashTableFile(compressedfile.CompressedFile(fina+"/datanodeend.hash", readOnly = True), readOnly = True)
		self.ws = hashtable.HashTableFile(compressedfile.CompressedFile(fina+"/datawaystart.hash", readOnly = True), readOnly = True)
		self.we = hashtable.HashTableFile(compressedfile.CompressedFile(fina+"/datawayend.hash", readOnly = True), readOnly = True)
		self.rs = hashtable.HashTableFile(compressedfile.CompressedFile(fina+"/datarelationstart.hash", readOnly = True), readOnly = True)
		self.re = hashtable.HashTableFile(compressedfile.CompressedFile(fina+"/datarelationend.hash", readOnly = True), readOnly = True)

	def Get(self, objType, objId, objVer):
		startPos = None
		endPos = None
		if objType in ["n", "node"]:
			startPos = self.ns[objId][objVer]
			endPos = self.ne[objId][objVer]

		if objType in ["w", "way"]:
			startPos = self.ws[objId][objVer]
			endPos = self.we[objId][objVer]

		if objType in ["r", "relation"]:
			startPos = self.rs[objId][objVer]
			endPos = self.re[objId][objVer]

		if startPos is None or endPos is None:
			return None

		self.mainData.seek(startPos)
		rawStr = self.mainData.read(endPos - startPos)
		return rawStr.decode('utf-8')

def GetNodesInCustomArea(spatialIndex, queryArea, osmObjectStore, versionStore, tolerateMissing):

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
	tileHits = 0
	tileCount = 0
	for tilex in xr:
		for tiley in yr:
			tileFina = "/{0}/{1}/{2}.dat".format(zoomLevel, tilex, tiley)
			tileCount += 1
			if not spatialIndex.exists(tileFina):
				continue
			tileHits += 1
			print "Query tile", tilex, tiley
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

	if not tolerateMissing and tileHits != tileCount:
		raise RuntimeError("Missing tiles detected")

	print "Candidate nodes", len(candidateNodes)
	print "Checking for latest versions"

	#Check these are the latest known version of the node
	currentNodes = {}
	countMissingNodes = 0
	for nodeId in candidateNodes:
		try:
			latestVer = versionStore.GetVersion("node", nodeId)
			foundVer = candidateNodes[nodeId]
			#print nodeId, latestVer, foundVer
			if latestVer == foundVer:
				currentNodes[nodeId] = foundVer
		except:
			#print "Missing node", nodeId
			countMissingNodes += 1

	print "Missing nodes:", countMissingNodes

	print "Num candidate nodes", len(currentNodes)

	#Filter to find those in bounding box
	print "Filtering nodes based on area"
	
	nodeInfo = {}
	for nodeId in currentNodes:
		objStr = osmObjectStore.Get("node", nodeId, currentNodes[nodeId])
		#print nodeId, "'"+objStr+"'"
		#print len(objStr)
		try:
			nodeXmlTree = ET.fromstring(objStr.encode("utf-8"))
		except ET.ParseError as err:
			print "Error getting", nodeId
			print err
			print objStr
			raise err

		lat = float(nodeXmlTree.attrib['lat'])
		lon = float(nodeXmlTree.attrib['lon'])
		
		if lat < queryArea[1] or lat > queryArea[3]:
			continue
		if lon < queryArea[0] or lon > queryArea[2]:
			continue

		nodeInfo[nodeId] = objStr

	#print spatialIndex.listdir("/11/1022")

	print "Num nodes in area", len(nodeInfo)
	
	return nodeInfo

def GetNodesInSlippyTile(spatialIndex, queryArea, osmObjectStore, versionStore, tolerateMissing):
	zoomLevel = queryArea[0]

	#Determine which data tiles to check for query
	xr = range(queryArea[1], queryArea[1]+1)
	yr = range(queryArea[2], queryArea[2]+1)

	print "Getting nodes from tile ranges", xr, yr
	nodeEntry = struct.Struct(">QI")

	#Get candidate nodes from spatial index
	candidateNodes = {}
	tileHits = 0
	tileCount = 0
	for tilex in xr:
		for tiley in yr:
			tileFina = "/{0}/{1}/{2}.dat".format(zoomLevel, tilex, tiley)
			tileCount += 1
			if not spatialIndex.exists(tileFina):
				continue
			tileHits += 1
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

	if not tolerateMissing and tileHits != tileCount:
		raise RuntimeError("Missing tiles detected")

	print "Checking for latest versions"

	#Check these are the latest known version of the node
	currentNodes = {}
	for nodeId in candidateNodes:
		try:
			latestVer = versionStore.GetVersion("node", nodeId)
			foundVer = candidateNodes[nodeId]
			#print nodeId, latestVer, foundVer
			if latestVer == foundVer:
				currentNodes[nodeId] = foundVer
		except:
			print "Missing node", nodeId

	print "Num candidate nodes", len(currentNodes)

	#Filter to find those in bounding box
	print "Get node data"
	
	nodeInfo = {}
	for nodeId in currentNodes:
		objStr = osmObjectStore.Get("node", nodeId, currentNodes[nodeId])
		nodeInfo[nodeId] = objStr

	#print spatialIndex.listdir("/11/1022")

	print "Num nodes in area", len(nodeInfo)
	
	return nodeInfo

class VersionStore(object):
	def __init__(self, path="dat"):
		self.nodeVersions = hashtable.HashTableFile(compressedfile.CompressedFile(path+"/ver.vnode", readOnly = True), readOnly = True)
		self.wayVersions = hashtable.HashTableFile(compressedfile.CompressedFile(path+"/ver.vway", readOnly = True), readOnly = True)
		self.relationVersions = hashtable.HashTableFile(compressedfile.CompressedFile(path+"/ver.vrelation", readOnly = True), readOnly = True)

	def GetVersion(self, objType, objId):
		if objType in ["n", "node"]:
			return self.nodeVersions[objId]
		if objType in ["w", "way"]:
			return self.wayVersions[objId]
		if objType in ["r", "relation"]:
			return self.relationVersions[objId]

		raise RuntimeError("Unknown object type")

class ParentsStore(object):
	def __init__(self, path="dat"):
		self.nodeParents = hashtable.HashTableFile(compressedfile.CompressedFile(path+"/ch.node", readOnly = True), readOnly = True)
		self.wayParents = hashtable.HashTableFile(compressedfile.CompressedFile(path+"/ch.way", readOnly = True), readOnly = True)
		self.relationParents = hashtable.HashTableFile(compressedfile.CompressedFile(path+"/ch.relation", readOnly = True), readOnly = True)

	def GetParents(self, objType, objId):

		typeStore = None
		if objType in ["n", "node"]:
			typeStore = self.nodeParents
		if objType in ["w", "way"]:
			typeStore = self.wayParents
		if objType in ["r", "relation"]:
			typeStore = self.relationParents

		if typeStore is None:
			raise RuntimeError("Unknown object type:"+str(objType))

		if objId in typeStore:
			out = {}
			parents = typeStore[objId]
			#print parents
			for objVer in parents:
				for t, oid in parents[objVer]:
					#print t, oid
					if t not in out:
						out[t] = {}
					outOfType = out[t]
					if oid not in outOfType:
						outOfType[oid] = set()
					outOfObj = outOfType[oid]
					outOfObj.add(objVer)

			return out
		else:
			#print nodeId, "is an orphan"
			return []

class CurrentParentStore(object):
	def __init__(self, versionStore, parentsStore):
		self.versionStore = versionStore
		self.parentsStore = parentsStore

	def GetCurrentParents(self, objType, objId):
		out = []
		allParents = self.parentsStore.GetParents(objType, objId)
		for t in allParents:
			objOfType = allParents[t]
			for oid in objOfType:
				foundVers = objOfType[oid]
				maxVer = max(foundVers)

				currentVer = self.versionStore.GetVersion(t, oid)
				if maxVer == currentVer:
					out.append((t, oid, currentVer))

		return out
		
def GetDataForObjs(objsOfInterest, versionStore, osmObjectStore):
	for objType in objsOfInterest:
		objOfType = objsOfInterest[objType]
		for objId in objOfType:
			if objOfType[objId] is not None:
				continue

			try:
				currentVer = versionStore.GetVersion(objType, objId)

				objXml = osmObjectStore.Get(objType, objId, currentVer)
				objOfType[objId] = objXml
			except IndexError as err: 
				print "Missing", objType, objId, err

class GetArea(object):
	def __init__(self, path="dat"):
		self.spatialIndex = qsfs.Qsfs(compressedfile.CompressedFile(path+"/sp", readOnly = True))
		self.osmObjectStore = OsmObjectStore(path)
		self.versionStore = VersionStore(path)
		self.parentsStore = ParentsStore(path)
		self.currentParentStore = CurrentParentStore(self.versionStore, self.parentsStore)

	def __del__(self):
		del self.currentParentStore

		print "Close spatial index"
		del self.spatialIndex

		print "Close object storage"
		del self.osmObjectStore

		print "Close version index"
		del self.versionStore

		print "Close parent index"
		del self.parentsStore

		print "All done"

	def GetArea(self, queryArea, out, tolerateMissing = True):
		
		nodesOfInterest = GetNodesInCustomArea(self.spatialIndex, queryArea, self.osmObjectStore, self.versionStore, tolerateMissing)
		self.NodesToCompleteData(nodesOfInterest, queryArea, out)

	def GetTile(self, tilex, tiley, zoom, out, tolerateMissing = True):
		tileNum = (zoom, tilex, tiley)
		nw = slippy.num2deg(tilex, tiley, zoom)
		se = slippy.num2deg(tilex+1, tiley+1, zoom)
		queryArea = [nw[1], nw[0], se[1], se[0]]
		nodesOfInterest = GetNodesInSlippyTile(self.spatialIndex, tileNum, self.osmObjectStore, self.versionStore, tolerateMissing)
		self.NodesToCompleteData(nodesOfInterest, queryArea, out)

	def NodesToCompleteData(self, nodesOfInterest, queryArea, out):

		#Get parents of objects
		print "Get parents of objects"

		newObjsOfInterest = {'n':{}}
		veryNewObjsOfInterest = {}
		objsOfInterest = {'n':{}}
		nnoi = newObjsOfInterest['n']
		for nodeId in nodesOfInterest:
			nnoi[nodeId] = nodesOfInterest[nodeId]

		done = False
		while not done:
			#Aquire parents of new objects
			for objType in newObjsOfInterest:
				objOfType = newObjsOfInterest[objType]

				for objId in objOfType:
					objXml = objOfType[objId]
					objCurrentParents = self.currentParentStore.GetCurrentParents(objType, objId)
					#print objType, objId, objCurrentParents
					for t, i, v in objCurrentParents:
						if t not in veryNewObjsOfInterest:
							veryNewObjsOfInterest[t] = {}
						oot = veryNewObjsOfInterest[t]
						oot[i] = None

			#Merge new objects into existing objects
			for objType in newObjsOfInterest:
				if objType not in objsOfInterest:
					objsOfInterest[objType] = {}
				fromOot = newObjsOfInterest[objType]
				toOot = objsOfInterest[objType]
				for objId in fromOot:
					toOot[objId] = fromOot[objId]

			#Reset temporary object stores
			newObjsOfInterest = veryNewObjsOfInterest
			veryNewObjsOfInterest = {}

			#Count pending objects
			count = 0
			for objType in newObjsOfInterest:
				count += len(newObjsOfInterest[objType])
			if count == 0:
				done = True

		for objType in objsOfInterest:
			print "count", objType, len(objsOfInterest[objType])

		print "Get data for objects"
		GetDataForObjs(objsOfInterest, self.versionStore, self.osmObjectStore)

		print "Complete ways"
		if 'n' not in objsOfInterest:
			objsOfInterest['n'] = {}
		if 'w' in objsOfInterest:
			ways = objsOfInterest['w']
			nodes = objsOfInterest['n']
			for objId in ways:
				#print objId
				wayXmlTree = ET.fromstring(ways[objId].encode('utf-8'))

				for ch in wayXmlTree:
					if ch.tag != "nd": continue
					nid = int(ch.attrib['ref'])
					if nid not in nodes:
						nodes[nid] = None

		for objType in objsOfInterest:
			print "count", objType, len(objsOfInterest[objType])

		print "Get data for objects 2"
		GetDataForObjs(objsOfInterest, self.versionStore, self.osmObjectStore)

		print "Output result"
		out.write("<?xml version='1.0' encoding='UTF-8'?>\n")
		out.write("<osm version='0.6' generator='py'>\n")
		out.write("<bounds minlat='{1}' minlon='{0}' maxlat='{3}' maxlon='{2}'/>\n".format(*queryArea))

		if 'n' in objsOfInterest:
			objs = objsOfInterest['n']
			for objId in objs:
				obj = objs[objId]
				if obj is None: continue
				out.write(obj.encode("utf-8"))
		if 'w' in objsOfInterest:
			objs = objsOfInterest['w']
			for objId in objs:
				obj = objs[objId]
				if obj is None: continue
				out.write(obj.encode("utf-8"))
		if 'r' in objsOfInterest:
			objs = objsOfInterest['r']
			for objId in objs:
				obj = objs[objId]
				if obj is None: continue
				out.write(obj.encode("utf-8"))

		out.write("</osm>\n")
		out.close()

def MultiTileSave(getArea, queryArea, zoom):

	tl = slippy.deg2num(queryArea[3], queryArea[0], 11)
	br = slippy.deg2num(queryArea[1], queryArea[2], 11)

	for tilex in range(tl[0], br[0]+2):
		if not os.path.exists(str(tilex)):
			os.mkdir(str(tilex))
		for tiley in range(tl[1], br[1]+2):
			fina = "{0}/{1}.osm.bz2".format(tilex, tiley)
			try:
				getArea.GetTile(tilex, tiley, zoom, bz2.BZ2File(fina, "w"), False)
			except RuntimeError as err:
				print err
				os.unlink(fina)

if __name__=="__main__":
	
	getArea = GetArea()
	#getArea.GetArea([-0.5142975,51.2413932,-0.4645157,51.2738368], bz2.BZ2File("out.osm.bz2", "w")) #left,bottom,right,top
	#getArea.GetTile(1021, 683, 11, bz2.BZ2File("out.osm.bz2", "w"))

	#northern_mariana_islands
	getArea.GetArea([145.6409693,15.0891509,145.8704831,15.297759], bz2.BZ2File("out.osm.bz2", "w")) #left,bottom,right,top
	#getArea.GetTile(1852, 936, 11, bz2.BZ2File("out.osm.bz2", "w"))

	#MultiTileSave(getArea, [-9.4042969,49.3823728,2.7246094,62.8751884], 11)
	
