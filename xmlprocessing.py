import xml.parsers.expat as expat
from xml.sax.saxutils import escape, quoteattr

class ExpatParse(object):
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
		self.outFi = outFi
		self.pos = 0
		self.parseOnly = 0

		if self.outFi is not None:
			wr = "<?xml version='1.0' encoding='UTF-8'?>\n"
			self.outFi.write(wr)
			self.pos += len(wr)
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
		self.tagStarts.append(self.pos)

		if not self.parseOnly:
			strFrag = []
			strFrag.append(unicode("<"+name))
			for k in attrs:
				strFrag.append(" "+k +"="+quoteattr(escape(unicode(attrs[k]))))		
			strFrag.append(">")
			openTag = "".join(strFrag)

			self.pos += len(openTag)
			if self.outFi is not None:
				self.outFi.write(openTag.encode("utf-8"))

	def HandleEndElement(self, name): 

		if not self.parseOnly:
			closeTag = "</"+name+">\n"
			self.pos += len(closeTag)
		
			if self.outFi is not None:
				self.outFi.write(closeTag.encode("utf-8"))

		if self.TagLimitCallback is not None:
			self.TagLimitCallback(name, self.depth, self.attr[-1], self.tagStarts[-1], self.pos)

		self.depth -= 1
		self.tags.pop()
		self.attr.pop()
		self.tagStarts.pop()

