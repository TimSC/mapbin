import sys, bz2, time, os
import xmlprocessing
from pycontainers import compressedfile, hashtable

#UK dump size nodes=33017987 ways=4040979 relations=80851

def StoreFactoryCreate(fina, maskBits = 26, maxCachedPages = 50):
	try:
		os.unlink(fina)
	except:
		pass

	compfile = compressedfile.CompressedFile(fina, createFile = True)
	compfile.maxCachePages = maxCachedPages
	table = hashtable.HashTableFile(compfile, maskBits, 1, 1, 1, 10000, createFile = True)
	return table, compfile

def StoreFactoryOpen(fina, maskBits = 26, maxCachedPages = 50):
	compfile = compressedfile.CompressedFile(fina, createFile = False)
	compfile.maxCachePages = maxCachedPages
	table = hashtable.HashTableFile(compfile, None, 0, 1, 1, 10000, createFile = False)
	return table, compfile

class TagIndex(object):

	def __init__(self, prefix, createFile = True):
		self.nodes = 0
		self.ways = 0
		self.relations = 0
		self.objs = 0
		self.lastDisplayTime = time.time()
		self.lastDisplayCount = 0

		self.objNumStart = None
		self.objNumEnd = None

		self.prefix = prefix
		if createFile:
			self.nodeParentStore, self.compFiN = StoreFactoryCreate(self.prefix+".vnode", 32, 500)
			self.wayParentStore, self.compFiW = StoreFactoryCreate(self.prefix+".vway", 28, 50)
			self.relationParentStore, self.compFiR = StoreFactoryCreate(self.prefix+".vrelation", 22, 50)
		else:
			self.nodeParentStore, self.compFiN = StoreFactoryOpen(self.prefix+".vnode", 32, 500)
			self.wayParentStore, self.compFiW = StoreFactoryOpen(self.prefix+".vway", 28, 50)
			self.relationParentStore, self.compFiR = StoreFactoryOpen(self.prefix+".vrelation", 22, 50)

	def __del__(self):
		self.flush()
		self.nodeParentStore, self.compFiN = None, None
		self.wayParentStore, self.compFiW = None, None
		self.relationParentStore, self.compFiR = None, None

	def flush(self):
		self.nodeParentStore.flush()
		self.wayParentStore.flush()
		self.relationParentStore.flush()
		self.compFiN.flush()
		self.compFiW.flush()
		self.compFiR.flush()

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
			if doInsert:
				objId = int(attr['id'])
				version = int(attr['version'])

				if objId in self.nodeParentStore:
					if version > self.nodeParentStore[objId]:
						self.nodeParentStore[objId] = version
				else:
					self.nodeParentStore[objId] = version

			self.nodes += 1

		if name == "way":
			if doInsert:
				objId = int(attr['id'])
				version = int(attr['version'])

				if objId in self.wayParentStore:
					if version > self.wayParentStore[objId]:
						self.wayParentStore[objId] = version
				else:
					self.wayParentStore[objId] = version
				
			self.ways += 1

		if name == "relation":
			if doInsert:
				objId = int(attr['id'])
				version = int(attr['version'])

				if objId in self.relationParentStore:
					if version > self.relationParentStore[objId]:
						self.relationParentStore[objId] = version
				else:
					self.relationParentStore[objId] = version

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

	tagIndex = TagIndex(sys.argv[2])

	parser = xmlprocessing.ReadXml()
	parser.TagLimitCallback = tagIndex.TagLimitCallback
	parser.ParseFile(infi)

	print tagIndex.nodes, tagIndex.ways, tagIndex.relations, tagIndex.objs

	del tagIndex
	del parser

	print "All done"

