
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
	def Add(self, lat, lon, objId, version):
		startZoom = 0
		
		filename = "zero"
		self.fi = self.outFileSystem.open(filename, "a")
		self.fi.write(struct.pack(">ffQI", lat, lon, objId, version))
		

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
		deviceSize = 100 * 1024 * 1024, 
		maxFileSize = 1 * 1024 * 1024,
		blockSize = 1024 * 1024)
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

