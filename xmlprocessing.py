import xml.parsers.expat as expat
from xml.sax.saxutils import escape, quoteattr

class ReadXml(object):
	def __init__(self):
		self.parser = expat.ParserCreate()
		self.parser.CharacterDataHandler = self.HandleCharData
		self.parser.StartElementHandler = self.HandleStartElement
		self.parser.EndElementHandler = self.HandleEndElement
		self.depth = 0
		self.maxDepth = 0
		self.tags = []
		self.attr = []
		self.childTags = {}
		self.childMembers = []
		self.TagLimitCallback = None

	def ParseFile(self, fi):
		fi.seek(0)
		self.fiTmp = fi
		self.parser.ParseFile(fi)

	def HandleCharData(self, data):
		pass

	def HandleStartElement(self, name, attrs):
		self.depth += 1
		self.maxDepth = self.depth
		self.tags.append(name)
		self.attr.append(attrs)

		if self.depth == 3:
			if name == "tag":
				self.childTags[attrs['k']] = attrs['v']
			if name == "nd":
				self.childMembers.append(("node", int(attrs['ref']), None))
			if name == "member":
				self.childMembers.append((attrs['type'], int(attrs['ref']), attrs['role']))

	def HandleEndElement(self, name): 

		if self.TagLimitCallback is not None:
			self.TagLimitCallback(name, self.depth, self.attr[-1], self.childTags, self.childMembers)

		if self.depth <= 2:
			self.childTags = {}
			self.childMembers = []

		self.depth -= 1
		self.tags.pop()
		self.attr.pop()

class OutFileControl(object):
	def __init__(self, outFi):
		self.outFi = outFi
		self.objs = 0
		self.startObjNum = None
		self.endObjNum = None

	def flush(self):
		self.outFi.flush()

	def write(self, dat):
		if self.startObjNum is not None:
			if self.obj < self.startObjNum: return
		if self.endObjNum is not None:
			if self.obj > self.endObjNum: return
 
		self.outFi.write(dat)

	def depthlimit(self, depth):
		if depth == 2:
			self.objs += 1

class RewriteXml(object):
	def __init__(self, outFi):
		self.parser = expat.ParserCreate()
		self.parser.CharacterDataHandler = self.HandleCharData
		self.parser.StartElementHandler = self.HandleStartElement
		self.parser.EndElementHandler = self.HandleEndElement
		self.depth = 0
		self.maxDepth = 0
		self.tags = []
		self.attr = []
		self.tagStarts = []
		if isinstance(outFi, OutFileControl):
			self.outFi = outFi
		else:
			self.outFi = OutFileControl(outFi)
		self.pos = 0
		self.parseOnly = 0
		self.incremental = None

		if self.outFi is not None:
			wr = "<?xml version='1.0' encoding='UTF-8'?>\n"
			self.outFi.write(wr)
			self.pos += len(wr)
		self.TagLimitCallback = None

	def ParseFile(self, fi):
		fi.seek(0)
		self.fiTmp = fi
		self.parser.ParseFile(fi)

	def StartIncremental(self, fi):
		if self.incremental is not None:
			raise RuntimeError("Incremental decode already start")
		fi.seek(0)
		self.incremental = fi

	def DoIncremental(self):
		if self.incremental is None:
			raise RuntimeError("Incremental not started")
		buff = self.incremental.read(1000000)
		if len(buff) > 0:
			self.parser.Parse(buff, 0)
			return 0 #Not done
		else:
			self.parser.Parse(buff, 1)
			self.incremental = None
			return 1 #All done

	def HandleCharData(self, data):
		pass

	def HandleStartElement(self, name, attrs):
		self.depth += 1
		self.maxDepth = self.depth
		self.tags.append(name)
		self.attr.append(attrs)
		self.tagStarts.append(self.pos)

		if not self.parseOnly:
			strFrag = []
			strFrag.append(unicode("<"+name))
			for k in attrs:
				strFrag.append(" "+k +"="+quoteattr(escape(unicode(attrs[k]))))		
			strFrag.append(">")
			openTag = "".join(strFrag)

			encodedOpenTag = openTag.encode("utf-8")
			self.pos += len(encodedOpenTag)
			if self.outFi is not None:
				self.outFi.write(encodedOpenTag)

	def HandleEndElement(self, name): 

		if not self.parseOnly:
			closeTag = "</"+name+">\n"
			closeTagEncoded = closeTag.encode("utf-8")

			self.pos += len(closeTagEncoded)
		
			if self.outFi is not None:
				self.outFi.write(closeTagEncoded)

		if self.TagLimitCallback is not None:
			self.TagLimitCallback(name, self.depth, self.attr[-1], self.tagStarts[-1], self.pos)

		self.outFi.depthlimit(self.depth)

		self.depth -= 1
		self.tags.pop()
		self.attr.pop()
		self.tagStarts.pop()

