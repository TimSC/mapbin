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
		self.incremental = None

	def ParseFile(self, fi):
		fi.seek(0)
		self.fiTmp = fi
		self.parser.ParseFile(fi)

	def StartIncremental(self, fi):
		if self.incremental is not None:
			raise RuntimeError("Incremental decode already start")
		fi.seek(0)
		self.incremental = fi

	def DoIncremental(self, buffSize = 1000000):
		if self.incremental is None:
			raise RuntimeError("Incremental not started")
		buff = self.incremental.read(buffSize)
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

class RewriteXml(object):
	def __init__(self, outFi, TagLimitCallback = None, CurrentObjectWantedCheck = None, CurrentPosFunc = None):
		self.parser = expat.ParserCreate()
		self.parser.CharacterDataHandler = self.HandleCharData
		self.parser.StartElementHandler = self.HandleStartElement
		self.parser.EndElementHandler = self.HandleEndElement
		self.depth = 0
		self.maxDepth = 0
		self.tags = []
		self.attr = []
		self.outFi = outFi
		self.parseOnly = 0
		self.incremental = None

		self.TagLimitCallback = TagLimitCallback
		self.CurrentObjectWantedCheck = CurrentObjectWantedCheck
		self.CurrentPosFunc = CurrentPosFunc
		self.startPos = None

		currentObjWanted = True
		if self.CurrentObjectWantedCheck is not None:
			currentObjWanted = self.CurrentObjectWantedCheck()

		if self.outFi is not None and currentObjWanted:
			wr = "<?xml version='1.0' encoding='UTF-8'?>\n"
			self.outFi.write(wr)
			if self.CurrentPosFunc is not None:
				self.CurrentPosFunc(len(wr))

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

		currentObjWanted = True
		if self.CurrentObjectWantedCheck is not None:
			currentObjWanted = self.CurrentObjectWantedCheck()

		if self.depth == 2 and currentObjWanted:
			if self.outFi is not None:
				self.startPos = self.outFi.tell()
			else:
				self.startPos = None

		if not self.parseOnly and currentObjWanted:
			strFrag = []
			strFrag.append(unicode("<"+name))
			for k in attrs:
				strFrag.append(" "+k +"="+quoteattr(escape(unicode(attrs[k]))))		
			strFrag.append(">")
			openTag = "".join(strFrag)

			encodedOpenTag = openTag.encode("utf-8")
			#self.tagLenAccum += len(encodedOpenTag)
			if self.outFi is not None:
				self.outFi.write(encodedOpenTag)

	def HandleEndElement(self, name): 

		currentObjWanted = True
		if self.CurrentObjectWantedCheck is not None:
			currentObjWanted = self.CurrentObjectWantedCheck()

		if not self.parseOnly and currentObjWanted:
			closeTag = "</"+name+">\n"
			closeTagEncoded = closeTag.encode("utf-8")

			#self.tagLenAccum += len(closeTagEncoded)
		
			if self.outFi is not None:
				self.outFi.write(closeTagEncoded)

		if self.TagLimitCallback is not None and self.depth==2:
			posNow = None
			if self.depth == 2 and currentObjWanted:
				if self.outFi is not None:
					posNow = self.outFi.tell()

			self.TagLimitCallback(name, self.depth, self.attr[-1], self.startPos, posNow)
			self.startPos = None

		self.depth -= 1
		self.tags.pop()
		self.attr.pop()

