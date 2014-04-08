import sys, bz2, time, os
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

class TagIndex(object):

	def __init__(self, nodeParentStore, wayParentStore, relationParentStore):
		self.nodes = 0
		self.ways = 0
		self.relations = 0
		self.objs = 0
		self.lastDisplayTime = time.time()
		self.lastDisplayCount = 0
		self.nodeParentStore = nodeParentStore
		self.wayParentStore = wayParentStore
		self.relationParentStore = relationParentStore

	def __del__(self):
		print "Flushing"

	def TagLimitCallback(self, name, depth, attr, childTags, childMembers):
		if depth != 2:
			return

		if time.time() - self.lastDisplayTime > 1.:
			rate = (self.objs - self.lastDisplayCount) / (time.time() - self.lastDisplayTime)
			self.lastDisplayCount = self.objs
			self.lastDisplayTime = time.time()
			print self.nodes, self.ways, self.relations, self.objs, "("+str(rate)+" obj per sec)"

		self.objs += 1

		if name == "node":
			objId = int(attr['id'])
			version = int(attr['version'])

			if objId in self.nodeParentStore:
				if version > self.nodeParentStore[objId]:
					self.nodeParentStore[objId] = version
			else:
				self.nodeParentStore[objId] = version

			self.nodes += 1

		if name == "way":

			objId = int(attr['id'])
			version = int(attr['version'])

			if objId in self.wayParentStore:
				if version > self.wayParentStore[objId]:
					self.wayParentStore[objId] = version
			else:
				self.wayParentStore[objId] = version
				
			self.ways += 1

		if name == "relation":

			objId = int(attr['id'])
			version = int(attr['version'])

			if objId in self.relationParentStore:
				if version > self.relationParentStore[objId]:
					self.relationParentStore[objId] = version
			else:
				self.relationParentStore[objId] = version

			self.relations += 1

if __name__ == "__main__":
	if len(sys.argv) < 2:
		print "Specify input file as argument"
		exit(1)

	if len(sys.argv) < 3:
		print "Specify output file as argument"
		exit(1)

	infi = bz2.BZ2File(sys.argv[1])

	nodeVerStore, compFiN = StoreFactoryCreate(sys.argv[2]+".vnode", 26, 5000)
	wayVerStore, compFiW = StoreFactoryCreate(sys.argv[2]+".vway", 26, 5000)
	relationVerStore, compFiR = StoreFactoryCreate(sys.argv[2]+".vrelation", 26, 5000)

	tagIndex = TagIndex(nodeVerStore, wayVerStore, relationVerStore)

	parser = xmlprocessing.ReadXml()
	parser.TagLimitCallback = tagIndex.TagLimitCallback
	parser.ParseFile(infi)

	print tagIndex.nodes, tagIndex.ways, tagIndex.relations, tagIndex.objs

	del tagIndex
	del parser

	print "All done"

