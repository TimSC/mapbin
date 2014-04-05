
import bz2, sys, os, time, math, struct
import xmlprocessing
from pycontainers import compressedfile, qsfs

#UK dump size nodes=33017987 ways=4040979 relations=80851

def deg2num(lat_deg, lon_deg, zoom):
	lat_rad = math.radians(lat_deg)
	n = 2.0 ** zoom
	xtile = int((lon_deg + 180.0) / 360.0 * n)
	ytile = int((1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi) / 2.0 * n)
	return (xtile, ytile)

class TileStorage(object):
	def __init__(self, outFileSystem):
		self.outFileSystem = outFileSystem
		self.minZoom = 11
		self.maxZoom = 11
		#self.entry = struct.Struct(">ffQI")
		self.entry = struct.Struct(">QI")
		for i in range(self.maxZoom+1):
			self.outFileSystem.mkdir("/"+str(i))

		self.handleCache = {}
		self.handleAccessTime = {}

	def Add(self, lat, lon, objId, version):
		self.RecusiveZoomAdd(self.minZoom, lat, lon, objId, version)

	def Open(self, currentZoom, tilex, tiley):
		datFilename = "/{0}/{1}/{2}.dat".format(currentZoom, tilex, tiley)
		if datFilename in self.handleCache:
			self.handleAccessTime[datFilename] = time.time()
			return self.handleCache[datFilename]

		try:
			fi = self.outFileSystem.open(datFilename, "a+")
		except:
			folderName = "/{0}/{1}".format(currentZoom, tilex)
			if not self.outFileSystem.exists(folderName):
				self.outFileSystem.mkdir(folderName)
			fi = self.outFileSystem.open(datFilename, "a+")
			
		self.handleCache[datFilename] = fi
		self.handleAccessTime[datFilename] = time.time()

		#Discard old handles
		if len(self.handleCache) > 100000:
			sortableList = zip(self.handleAccessTime.values(), self.handleAccessTime.keys())
			sortableList.sort()

			cutPoint = len(sortableList) / 10
			for ti, fina in sortableList[:cutPoint]:
				del self.handleAccessTime[fina]
				del self.handleCache[fina]

		return fi
	
	def RecusiveZoomAdd(self, currentZoom, lat, lon, objId, version):
		
		tilex, tiley = deg2num(lat, lon, currentZoom)
		#print lat, lon, tilex, tiley

		#fullFile = "/{0}/{1}/{2}.full".format(currentZoom, tilex, tiley)
		#if self.outFileSystem.exists(fullFile) and currentZoom < self.maxZoom:
		#	self.RecusiveZoomAdd(currentZoom + 1, lat, lon, objId, version)
		#	return

		fi = self.Open(currentZoom, tilex, tiley)
		fi.write(self.entry.pack(objId, version))
		numEntries = len(fi) / self.entry.size
		#print lat, lon, currentZoom, numEntries
		#if numEntries >= 100 and currentZoom < self.maxZoom:
		#	self.outFileSystem.open(fullFile, "w")

class TagIndex(object):

	def __init__(self, outfi):
		self.nodes = 0
		self.ways = 0
		self.relations = 0
		self.objs = 0
		self.lastDisplayTime = time.time()
		self.lastDisplayCount = 0
		self.outfi = outfi

	def __del__(self):
		print "Flushing"

	def TagLimitCallback(self, name, depth, attr):
		if depth != 2:
			return

		if time.time() - self.lastDisplayTime > 1.:
			rate = (self.objs - self.lastDisplayCount) / (time.time() - self.lastDisplayTime)
			self.lastDisplayCount = self.objs
			self.lastDisplayTime = time.time()
			print self.nodes, self.ways, self.relations, self.objs, "("+str(rate)+" obj per sec)"

		self.objs += 1

		if name == "node":
			self.nodes += 1
			lat = float(attr['lat'])
			lon = float(attr['lon'])
			objId = int(attr['id'])
			version = int(attr['version'])
			self.outfi.Add(lat, lon, objId, version)

		if name == "way":
			self.ways += 1

		if name == "relation":
			self.relations += 1

if __name__ == "__main__":
	if len(sys.argv) < 2:
		print "Specify input file as argument"
		exit(1)

	if len(sys.argv) < 3:
		print "Specify output file as argument"
		exit(1)

	infi = bz2.BZ2File(sys.argv[1])
	try:
		os.unlink(sys.argv[2])
	except:
		pass

	outFileSystem = qsfs.Qsfs(compressedfile.CompressedFile(sys.argv[2]), initFs = 1, 
		deviceSize = 10000 * 1024 * 1024, 
		maxFileSize = 1 * 1024 * 1024,
		blockSize = 100 * 1024,
		maxFiles = 5000000)
	print outFileSystem.statvfs("/")

	tileStorage = TileStorage(outFileSystem)
	tagIndex = TagIndex(tileStorage)

	parser = xmlprocessing.ReadXml()
	parser.TagLimitCallback = tagIndex.TagLimitCallback
	parser.ParseFile(infi)

	#print len(tagIndex.nodeStartTable)	
	#print tagIndex.nodeStartTable.binsInUse
	#print tagIndex.nodeStartTable.hashMask

	print tagIndex.nodes, tagIndex.ways, tagIndex.relations, tagIndex.objs

	del tagIndex
	del parser

	print "All done"

