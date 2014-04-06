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

	def AddParent(self, childType, childRef, parentType, parentRef):
		#print childType, childRef, parentType, parentRef

		if childType == "node":
			if childRef not in self.nodeParentStore:
				tmp = []
			else:
				tmp = self.nodeParentStore[childRef]
			tmp.append([parentType[0], parentRef])
			self.nodeParentStore[childRef] = tmp
			
		if childType == "way":
			if childRef not in self.wayParentStore:
				tmp = []
			else:
				tmp = self.wayParentStore[childRef]
			tmp.append([parentType[0], parentRef])
			self.wayParentStore[childRef] = tmp

		if childType == "relation":
			if childRef not in self.relationParentStore:
				tmp = []
			else:
				tmp = self.relationParentStore[childRef]
			tmp.append([parentType[0], parentRef])
			self.relationParentStore[childRef] = tmp

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
			self.nodes += 1

		if name == "way":
			#print name, childTags, childMembers
			objId = int(attr['id'])
			for chType, chRef, chRole in childMembers:
				self.AddParent(chType, chRef, name, objId)
				
			self.ways += 1

		if name == "relation":
			#print name, childTags, childMembers
			self.relations += 1
			objId = int(attr['id'])
			for chType, chRef, chRole in childMembers:
				self.AddParent(chType, chRef, name, objId)

if __name__ == "__main__":
	if len(sys.argv) < 2:
		print "Specify input file as argument"
		exit(1)

	if len(sys.argv) < 3:
		print "Specify output file as argument"
		exit(1)

	infi = bz2.BZ2File(sys.argv[1])

	nodeParentStore, compFiN = StoreFactoryCreate(sys.argv[2]+".node", 26, 5000)
	wayParentStore, compFiW = StoreFactoryCreate(sys.argv[2]+".way", 26, 5000)
	relationParentStore, compFiR = StoreFactoryCreate(sys.argv[2]+".relation", 26, 5000)

	tagIndex = TagIndex(nodeParentStore, wayParentStore, relationParentStore)

	parser = xmlprocessing.ReadXml()
	parser.TagLimitCallback = tagIndex.TagLimitCallback
	parser.ParseFile(infi)
	
	

	print tagIndex.nodes, tagIndex.ways, tagIndex.relations, tagIndex.objs

	del tagIndex
	del parser

	print "All done"

