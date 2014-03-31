
import bz2, sys, os, time
import xmlprocessing
from pycontainers import quadtree

#UK dump size nodes=33017987 ways=4040979 relations=80851

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
			print lat, lon, objId, version

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
	outfi = quadtree.QuadTree(sys.argv[2])

	tagIndex = TagIndex(outfi)

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

