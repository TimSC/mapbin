
import bz2, sys, os, time, math, struct
import xmlprocessing, slippy
from pycontainers import compressedfile, qsfs

#UK dump size nodes=33017987 ways=4040979 relations=80851

def StoreFactoryCreate(fina):
	try:
		os.unlink(sys.argv[2])
	except:
		pass

	outFileSystem = qsfs.Qsfs(compressedfile.CompressedFile(fina, createFile=True), initFs = 1, 
		deviceSize = 1024 * 1024 * 1024 * 1024, #1Tb
		maxFileSize = 200 * 1024 * 1024,
		blockSize = 1024 * 1024,
		maxFiles = 5000000)
	print outFileSystem.statvfs("/")

	tileStorage = TileStorage(outFileSystem)
	return tileStorage, outFileSystem

def StoreFactoryOpen(fina):

	outFileSystem = qsfs.Qsfs(compressedfile.CompressedFile(fina, createFile=False), initFs = 0)
	print outFileSystem.statvfs("/")

	tileStorage = TileStorage(outFileSystem)
	return tileStorage, outFileSystem

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
		
		tilex, tiley = slippy.deg2num(lat, lon, currentZoom)
		#print lat, lon, tilex, tiley

		#fullFile = "/{0}/{1}/{2}.full".format(currentZoom, tilex, tiley)
		#if self.outFileSystem.exists(fullFile) and currentZoom < self.maxZoom:
		#	self.RecusiveZoomAdd(currentZoom + 1, lat, lon, objId, version)
		#	return

		fi = self.Open(currentZoom, tilex, tiley)
		objIdInt = int(objId)
		if objIdInt == 0:
			print "Warning: adding a zero objId"
		fi.write(self.entry.pack(objIdInt, version))
		numEntries = len(fi) / self.entry.size
		#print lat, lon, currentZoom, numEntries
		#if numEntries >= 100 and currentZoom < self.maxZoom:
		#	self.outFileSystem.open(fullFile, "w")

	def flush(self):
		self.outFileSystem.flush()

class TagIndex(object):

	def __init__(self, fina, createFile=True):
		self.nodes = 0
		self.ways = 0
		self.relations = 0
		self.objs = 0
		self.lastDisplayTime = time.time()
		self.lastDisplayCount = 0

		self.objNumStart = None
		self.objNumEnd = None

		if createFile:
			self.outfi, self.outFileSystem = StoreFactoryCreate(fina)
		else:
			self.outfi, self.outFileSystem = StoreFactoryOpen(fina)

	def __del__(self):
		print "Flushing"
		self.flush()

	def flush(self):
		self.outfi.flush()
		self.outFileSystem.flush()

	def TagLimitCallback(self, name, depth, attr, childTags, childMembers):
		if depth != 2:
			return

		if time.time() - self.lastDisplayTime > 1.:
			rate = (self.objs - self.lastDisplayCount) / (time.time() - self.lastDisplayTime)
			self.lastDisplayCount = self.objs
			self.lastDisplayTime = time.time()
			print self.nodes, self.ways, self.relations, self.objs, "("+str(rate)+" obj per sec)"


		doInsert = True
		if self.objNumStart is not None and self.objNumStart > self.objs:
			doInsert = False
		if self.objNumEnd is not None and self.objNumEnd < self.objs:
			doInsert = False

		if name == "node":
			self.nodes += 1
			if doInsert:
				lat = float(attr['lat'])
				lon = float(attr['lon'])
				objId = int(attr['id'])
				version = int(attr['version'])
				self.outfi.Add(lat, lon, objId, version)

		if name == "way":
			self.ways += 1

		if name == "relation":
			self.relations += 1

		self.objs += 1


if __name__ == "__main__":
	if len(sys.argv) < 2:
		print "Specify input file as argument"
		exit(1)

	if len(sys.argv) < 3:
		print "Specify output file as argument"
		exit(1)

	infi = bz2.BZ2File(sys.argv[1])
	tagIndex = TagIndex(sys.argv[2]+"/sp")

	parser = xmlprocessing.ReadXml()
	parser.TagLimitCallback = tagIndex.TagLimitCallback
	parser.ParseFile(infi)

	#print len(tagIndex.nodeStartTable)	
	#print tagIndex.nodeStartTable.binsInUse
	#print tagIndex.nodeStartTable.hashMask

	print tagIndex.nodes, tagIndex.ways, tagIndex.relations, tagIndex.objs

	tagIndex.flush()
	del tagIndex
	del parser
	print "All done"

