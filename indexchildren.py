import sys, bz2, time, os
import xmlprocessing
from pycontainers import compressedfile, hashtable

#UK dump size nodes=33017987 ways=4040979 relations=80851

def StoreFactoryCreate(fina, maskBits = 26, maxCachedPages = 50):
	try:
		if os.path.exists(fina):
			print "Delete old", fina
			os.unlink(fina)
			print "done"
	except:
		pass

	compfile = compressedfile.CompressedFile(fina, createFile = True)
	compfile.maxCachePages = maxCachedPages
	table = hashtable.HashTableFile(compfile, maskBits, 1, 1, 1, 10000, createFile = True)
	return table, compfile

def StoreFactoryRead(fina, maxCachedPages = 50):
	compfile = compressedfile.CompressedFile(fina, createFile = False)
	compfile.maxCachePages = maxCachedPages
	table = hashtable.HashTableFile(compfile, createFile = False)
	return table, compfile	

class TagIndex(object):

	def __init__(self, prefix, createFile = True):
		self.nodes = 0
		self.ways = 0
		self.relations = 0
		self.objs = 0
		self.lastDisplayTime = time.time()
		self.lastDisplayCount = 0
		self.childCount = 0

		self.objNumStart = None
		self.objNumEnd = None

		if createFile:
			self.nodeParentStore, self.compFiN = StoreFactoryCreate(prefix+".node", 32, 500)
			self.wayParentStore, self.compFiW = StoreFactoryCreate(prefix+".way", 28, 100)
			self.relationParentStore, self.compFiR = StoreFactoryCreate(prefix+".relation", 22, 100)
		else:
			self.nodeParentStore, self.compFiN = StoreFactoryRead(prefix+".node", 500)
			self.wayParentStore, self.compFiW = StoreFactoryRead(prefix+".way", 100)
			self.relationParentStore, self.compFiR = StoreFactoryRead(prefix+".relation", 100)

	def __del__(self):
		print "Flushing"
		self.flush()
		self.nodeParentStore, self.compFiN = None, None
		self.wayParentStore, self.compFiW = None, None
		self.relationParentStore, self.compFiR = None, None

	def AddParent(self, childType, childRef, parentType, parentRef, parentVer):
		#print childType, childRef, parentType, parentRef

		if childType == "node":
			if childRef not in self.nodeParentStore:
				tmp = {}
			else:
				tmp = self.nodeParentStore[childRef]
			if parentVer not in tmp:
				tmp[parentVer] = []
			tmp[parentVer].append([parentType[0], parentRef])
			self.nodeParentStore[childRef] = tmp
			
		if childType == "way":
			if childRef not in self.wayParentStore:
				tmp = {}
			else:
				tmp = self.wayParentStore[childRef]
			if parentVer not in tmp:
				tmp[parentVer] = []
			tmp[parentVer].append([parentType[0], parentRef])
			self.wayParentStore[childRef] = tmp

		if childType == "relation":
			if childRef not in self.relationParentStore:
				tmp = {}
			else:
				tmp = self.relationParentStore[childRef]
			if parentVer not in tmp:
				tmp[parentVer] = []
			tmp[parentVer].append([parentType[0], parentRef])
			self.relationParentStore[childRef] = tmp

	def TagLimitCallback(self, name, depth, attr, childTags, childMembers):
		if depth != 2:
			return

		doInsert = True
		if self.objNumStart is not None and self.objNumStart > self.objs:
			doInsert = False
		if self.objNumEnd is not None and self.objNumEnd < self.objs:
			doInsert = False

		if time.time() - self.lastDisplayTime > 1.:
			elapseTime = (time.time() - self.lastDisplayTime)
			rate = (self.objs - self.lastDisplayCount) / elapseTime
			self.lastDisplayCount = self.objs
			self.lastDisplayTime = time.time()
			print self.nodes, self.ways, self.relations, self.objs, "("+str(rate)+" obj per sec)"
			print self.childCount, float(self.childCount) / elapseTime
			self.childCount = 0

		if self.objs % 100000 == 0:
			print "Flushing"
			self.nodeParentStore.flush()
			self.wayParentStore.flush()
			self.relationParentStore.flush()

		if name == "node":
			self.nodes += 1

		if name == "way":
			if doInsert:
				#print name, childTags, childMembers
				objId = int(attr['id'])
				version = int(attr['version'])
				for chType, chRef, chRole in childMembers:
					self.AddParent(chType, chRef, name, objId, version)
					self.childCount += 1
				
			self.ways += 1

		if name == "relation":
			if doInsert:
				#print name, childTags, childMembers				
				objId = int(attr['id'])
				version = int(attr['version'])
				for chType, chRef, chRole in childMembers:
					self.AddParent(chType, chRef, name, objId, version)
					self.childCount += 1

			self.relations += 1

		self.objs += 1

	def flush(self):
		self.nodeParentStore.flush()
		self.wayParentStore.flush()
		self.relationParentStore.flush()
		self.compFiN.flush()
		self.compFiW.flush()
		self.compFiR.flush()

if __name__ == "__main__":
	if len(sys.argv) < 2:
		print "Specify input file as argument"
		exit(1)

	if len(sys.argv) < 3:
		print "Specify output file as argument"
		exit(1)

	infi = bz2.BZ2File(sys.argv[1])

	tagIndex = TagIndex(sys.argv[2]+"/ch", True)

	parser = xmlprocessing.ReadXml()
	parser.TagLimitCallback = tagIndex.TagLimitCallback
	parser.ParseFile(infi)

	print tagIndex.nodes, tagIndex.ways, tagIndex.relations, tagIndex.objs

	del tagIndex
	del parser

	print "All done"

