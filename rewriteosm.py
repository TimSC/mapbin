
import bz2, sys, os, time
import rewritexml
from pycontainers import compressedfile, hashtable

#UK dump size nodes=33017987 ways=4040979 relations=80851

def StoreFactoryCreate(fina, maskBits = 26, maxCachedPages = 50):
	try:
		os.unlink(fina)
	except:
		pass

	compfile = compressedfile.CompressedFile(fina)
	compfile.maxCachePages = maxCachedPages
	nodeStartTable = hashtable.HashTableFile(compfile, maskBits, 1)
	return nodeStartTable

def StoreFactoryRead(fina, maxCachedPages = 50):

	compfile = compressedfile.CompressedFile(fina)
	compfile.maxCachePages = maxCachedPages
	nodeStartTable = hashtable.HashTableFile(compfile, maskBits, 0)
	return nodeStartTable

class TagIndex(object):

	def __init__(self):
		self.nodes = 0
		self.ways = 0
		self.relations = 0
		self.objs = 0
		self.lastDisplayTime = time.time()
		self.lastDisplayCount = 0

		print "Create node tables"
		self.nodeStartTable = StoreFactoryCreate("nodestart.hash", 26, 500)
		self.nodeEndTable = StoreFactoryCreate("nodeend.hash", 26, 500)

		print "Create way tables"
		self.wayStartTable = StoreFactoryCreate("waystart.hash", 23)
		self.wayEndTable = StoreFactoryCreate("wayend.hash", 23)

		print "Create relation tables"
		self.relationStartTable = StoreFactoryCreate("relationstart.hash", 17)
		self.relationEndTable = StoreFactoryCreate("relationend.hash", 17)

		self.nodeStartTable.verbose = 0
		self.nodeEndTable.verbose = 0
		self.nodeStartTable.modulusIntHash = 1
		self.nodeEndTable.modulusIntHash = 1

		self.wayStartTable.modulusIntHash = 1
		self.wayEndTable.modulusIntHash = 1

		self.relationStartTable.modulusIntHash = 1
		self.relationEndTable.modulusIntHash = 1

		if 0:
			print "Clear node hashes"
			self.nodeStartTable.clear()
			self.nodeEndTable.clear()

			print "Clear way hashes"
			self.wayStartTable.clear()
			self.wayEndTable.clear()

			print "Clear relation hashes"
			self.relationStartTable.clear()
			self.relationEndTable.clear()

		#self.nodeStartTable.allocate_mask_size(21)
		#self.nodeEndTable.allocate_mask_size(21)

	def TagLimitCallback(self, name, depth, attr, start, end):
		if depth != 2:
			return

		if self.objs % 1000 == 0:
			rate = (self.objs - self.lastDisplayCount) / (time.time() - self.lastDisplayTime)
			self.lastDisplayCount = self.objs
			self.lastDisplayTime = time.time()
			print self.nodes, self.ways, self.relations, self.objs, "("+str(rate)+" obj per sec)"

		self.objs += 1

		if name == "node":
			self.nodes += 1
			self.nodeStartTable[int(attr['id'])] = int(start)
			self.nodeEndTable[int(attr['id'])] = int(end)

		if name == "way":
			self.ways += 1
			self.wayStartTable[int(attr['id'])] = int(start)
			self.wayEndTable[int(attr['id'])] = int(end)

		if name == "relation":
			self.relations += 1
			self.relationStartTable[int(attr['id'])] = int(start)
			self.relationEndTable[int(attr['id'])] = int(end)

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
	outfi = compressedfile.CompressedFile(sys.argv[2])

	tagIndex = TagIndex()

	parser = rewritexml.ExpatParse(outfi)
	parser.TagLimitCallback = tagIndex.TagLimitCallback
	parser.ParseFile(infi)

	#print len(tagIndex.nodeStartTable)	
	#print tagIndex.nodeStartTable.binsInUse
	#print tagIndex.nodeStartTable.hashMask

	print tagIndex.nodes, tagIndex.ways, tagIndex.relations, tagIndex.objs

