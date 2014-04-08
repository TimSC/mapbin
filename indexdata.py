
import bz2, sys, os, time
import xmlprocessing
from pycontainers import compressedfile, hashtable

#UK dump size nodes=33017987 ways=4040979 relations=80851

def StoreFactoryCreate(fina, maskBits = 26, maxCachedPages = 50):
	try:
		os.unlink(fina)
	except:
		pass

	compfile = compressedfile.CompressedFile(fina)
	compfile.maxCachePages = maxCachedPages
	table = hashtable.HashTableFile(compfile, maskBits, 1, 1, 1, 10000)
	return table, compfile

def StoreFactoryRead(fina, maxCachedPages = 50):

	compfile = compressedfile.CompressedFile(fina)
	compfile.maxCachePages = maxCachedPages
	table = hashtable.HashTableFile(compfile, None, 0, 1, 1, 10000)
	return table, compfile

class TagIndex(object):

	def __init__(self, outFina):
		self.nodes = 0
		self.ways = 0
		self.relations = 0
		self.objs = 0
		self.lastDisplayTime = time.time()
		self.lastDisplayCount = 0
		self.outFina = outFina

		print "Create node tables"
		self.nodeStartTable, self.nodeStartFile = StoreFactoryCreate(self.outFina+"nodestart.hash", 26, 5000)
		self.nodeEndTable, self.nodeEndFile = StoreFactoryCreate(self.outFina+"nodeend.hash", 26, 5000)

		print "Create way tables"
		self.wayStartTable, self.wayStartFile = StoreFactoryCreate(self.outFina+"waystart.hash", 23, 500)
		self.wayEndTable, self.wayEndFile = StoreFactoryCreate(self.outFina+"wayend.hash", 23, 500)

		print "Create relation tables"
		self.relationStartTable, self.relationStartFile = StoreFactoryCreate(self.outFina+"relationstart.hash", 17, 500)
		self.relationEndTable, self.relationEndFile = StoreFactoryCreate(self.outFina+"relationend.hash", 17, 500)

		self.nodeStartTable.verbose = 0
		self.nodeEndTable.verbose = 0

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

	def __del__(self):
		print "Flushing"
		del self.nodeStartTable
		del self.nodeEndTable

		del self.wayStartTable
		del self.wayEndTable

		del self.relationStartTable
		del self.relationEndTable

	def TagLimitCallback(self, name, depth, attr, start, end):
		if depth != 2:
			return

		if time.time() - self.lastDisplayTime > 1.:
			rate = (self.objs - self.lastDisplayCount) / (time.time() - self.lastDisplayTime)
			self.lastDisplayCount = self.objs
			self.lastDisplayTime = time.time()
			print self.nodes, self.ways, self.relations, self.objs, "("+str(rate)+" obj per sec)"
		
			if 1:
				print "page reads", self.nodeStartFile.cacheReads, self.nodeStartFile.diskReads
				print "page writes", self.nodeStartFile.cacheWrites, self.nodeStartFile.diskWrites

		self.objs += 1

		if name == "node":
			objId = int(attr['id'])
			objVersion = int(attr['version'])

			if objId in self.nodeStartTable:
				tmpStart = self.nodeStartTable[objId]
			else:
				tmpStart = {}
			if objId in self.nodeEndTable:
				tmpEnd = self.nodeEndTable[objId]
			else:
				tmpEnd = {}

			tmpStart[objVersion] = start
			tmpEnd[objVersion] = end

			self.nodeStartTable[objId] = tmpStart
			self.nodeEndTable[objId] = tmpEnd

			self.nodes += 1

		if name == "way":
			objId = int(attr['id'])
			objVersion = int(attr['version'])

			if objId in self.wayStartTable:
				tmpStart = self.wayStartTable[objId]
			else:
				tmpStart = {}
			if objId in self.wayEndTable:
				tmpEnd = self.wayEndTable[objId]
			else:
				tmpEnd = {}

			tmpStart[objVersion] = start
			tmpEnd[objVersion] = end

			self.wayStartTable[objId] = tmpStart
			self.wayEndTable[objId] = tmpEnd

			self.ways += 1

		if name == "relation":
			objId = int(attr['id'])
			objVersion = int(attr['version'])

			if objId in self.relationStartTable:
				tmpStart = self.relationStartTable[objId]
			else:
				tmpStart = {}
			if objId in self.relationEndTable:
				tmpEnd = self.relationEndTable[objId]
			else:
				tmpEnd = {}

			tmpStart[objVersion] = start
			tmpEnd[objVersion] = end

			self.relationStartTable[objId] = tmpStart
			self.relationEndTable[objId] = tmpEnd

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
	outfi = compressedfile.CompressedFile(sys.argv[2])

	tagIndex = TagIndex(sys.argv[2])

	parser = xmlprocessing.RewriteXml(outfi)
	parser.TagLimitCallback = tagIndex.TagLimitCallback
	parser.ParseFile(infi)

	#print len(tagIndex.nodeStartTable)	
	#print tagIndex.nodeStartTable.binsInUse
	#print tagIndex.nodeStartTable.hashMask

	print tagIndex.nodes, tagIndex.ways, tagIndex.relations, tagIndex.objs

	del tagIndex
	del parser

	print "All done"
