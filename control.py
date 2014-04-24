#!/usr/bin/python
 
import sys, os, pickle, time, bz2
import indexdata, xmlprocessing, indexchildren, indexspatial, indexversion
from pycontainers import compressedfile, hashtable
import PySide
import PySide.QtGui as QtGui
import PySide.QtCore as QtCore

# ************ Data import class ****************

class DataImport(object):
	def __init__(self, projectState, workingFolder):
		self.projectState = projectState
		self.workingFolder = workingFolder
		self.running = False
		self.parser = None

	def __del__(self):
		self.Pause()

		self.parser = None
		self.outfi = None
		self.tagIndex = None

	def Start(self):
		print "StartPressed"
		print self.projectState

		if "dat-done" not in self.projectState:
			self.projectState["dat-done"] = None

		if "dat-progress" not in self.projectState:
			self.projectState["dat-progress"] = None

		if self.projectState["dat-done"] is not None:
			print "Data index already done"
			return

		if self.parser is None:
			if "dat-created" not in self.projectState:
				self.projectState["dat-created"] = False

			if not self.projectState["dat-created"]:
				self.outfi = compressedfile.CompressedFile(self.workingFolder+"/data", createFile=True)
				self.tagIndex = indexdata.TagIndex(self.workingFolder+"/data", createFile=True)
				self.parser = xmlprocessing.RewriteXml(self.outfi, self.tagIndex.TagLimitCallback, 
					self.tagIndex.CurrentObjectWantedCheck, self.tagIndex.CurrentPosFunc)
				self.parser.TagLimitCallback = self.tagIndex.TagLimitCallback
				self.parser.CurrentObjectWantedCheck = self.tagIndex.CurrentObjectWantedCheck
				self.parser.StartIncremental(bz2.BZ2File(self.projectState["input"]))
			else:
				self.outfi = compressedfile.CompressedFile(self.workingFolder+"/data", createFile=False)
				self.tagIndex = indexdata.TagIndex(self.workingFolder+"/data", createFile=False)

				self.parser = xmlprocessing.RewriteXml(self.outfi, self.tagIndex.TagLimitCallback, 
					self.tagIndex.CurrentObjectWantedCheck, self.tagIndex.CurrentPosFunc)

				self.tagIndex.objNumStart = self.projectState["dat-progress"]
				#self.tagIndex.objNumStartPos = self.projectState["dat-pos"]
				#self.parser.outFi.objNumStart = self.projectState["dat-progress"]
				self.parser.StartIncremental(bz2.BZ2File(self.projectState["input"]))

			self.projectState["dat-created"] = True

		self.running = True		

	def Pause(self):
		print "PausePressed"
		if not self.running:
			return
		self.running = False

		objCount1 = self.tagIndex.objs

		print "Tag index obj count", objCount1

		if self.tagIndex.objs > self.projectState["dat-progress"]:
			self.projectState["dat-progress"] = self.tagIndex.objs
			#self.projectState["dat-pos"] = self.tagIndex.pos

		print "Flushing index"
		self.tagIndex.flush()
		self.parser.outFi.flush()
		print "done"

	def Clear(self):
		if self.running:
			print "Error: Cannot clear while running"
			return
		print "Clearing existing data"

		self.projectState["dat-created"] = False
		self.projectState["dat-progress"] = 0
		self.projectState["dat-done"] = None

		self.parser = None
		self.outfi = None
		self.tagIndex = None

	def Update(self):
		if self.running:
			try:
				ret = self.parser.DoIncremental()
			except Exception as err:
				print "data import failed", err
				self.running = False
				ret = 0

			if ret == 1:
				print "Stopping dat import, all done"
				self.running = False
				self.projectState["dat-progress"] = self.tagIndex.objs
				self.projectState["dat-done"] = self.tagIndex.objs
				self.tagIndex.flush()
				self.parser.outFi.flush()

# ************ index class ****************

class MultiImport(object):
	def __init__(self, projectState, workingFolder, prefix, descriptiveName, ParserFactory, IndexFactory, indexArgs):
		self.projectState = projectState
		self.workingFolder = workingFolder
		self.running = False
		self.parser = None
		self.tagIndex = None

		self.createdKey = prefix+"-created"
		self.progressKey = prefix+"-progress"
		self.doneKey = prefix+"-done"
		self.prefix = prefix
		self.descriptiveName = descriptiveName
		self.ParserFactory = ParserFactory
		self.IndexFactory = IndexFactory
		self.indexArgs = indexArgs
		self.xmlBuffSize = 1000000

	def __del__(self):
		self.Pause()

		self.parser = None
		self.outfi = None
		self.tagIndex = None

	def Start(self):
		print "StartPressed"
		print self.projectState

		if self.doneKey not in self.projectState:
			self.projectState[self.doneKey] = None
		if self.progressKey not in self.projectState:
			self.projectState[self.progressKey] = None

		if self.projectState[self.doneKey] is not None:
			print self.descriptiveName,"already done"
			return

		if self.parser is None:
			if self.createdKey not in self.projectState:
				self.projectState[self.createdKey] = False

			if not self.projectState[self.createdKey]:
				self.tagIndex = self.IndexFactory(*self.indexArgs, createFile=True)
				self.parser = self.ParserFactory()
				self.parser.TagLimitCallback = self.tagIndex.TagLimitCallback
				self.parser.StartIncremental(bz2.BZ2File(self.projectState["input"]))

				self.projectState[self.createdKey] = True
			else:
				self.tagIndex = self.IndexFactory(*self.indexArgs, createFile=False)

				self.parser = self.ParserFactory()
				self.parser.TagLimitCallback = self.tagIndex.TagLimitCallback

				self.tagIndex.objNumStart = self.projectState[self.progressKey]
				self.parser.StartIncremental(bz2.BZ2File(self.projectState["input"]))

		self.running = True

	def Pause(self):
		print "PausePressed"
		if not self.running:
			return
		self.running = False

		objCount1 = self.tagIndex.objs

		print "Tag index obj count", objCount1

		if self.tagIndex.objs > self.projectState[self.progressKey]:
			self.projectState[self.progressKey] = self.tagIndex.objs

		print "Flushing index"
		self.tagIndex.flush()
		print "done"

	def Clear(self):
		if self.running:
			print "Error: Cannot clear while running"
			return
		print "Clearing existing", self.descriptiveName

		self.projectState[self.createdKey] = False
		self.projectState[self.progressKey] = 0
		self.projectState[self.doneKey] = None

		self.parser = None
		self.outfi = None
		self.tagIndex = None

	def Update(self):
		if self.running:
			try:
				ret = self.parser.DoIncremental(self.xmlBuffSize)
			except Exception as err:
				print self.descriptiveName, "import failed", err
				self.running = False
				ret = 0
			if ret == 1:
				print "Stopping",self.descriptiveName,"import, all done"
				self.running = False
				self.projectState[self.progressKey] = self.tagIndex.objs
				self.projectState[self.doneKey] = self.tagIndex.objs
				self.tagIndex.flush()

# ************ Main GUI *******************

class MainWindow(QtGui.QMainWindow):
	def __init__(self):
		super(MainWindow, self).__init__() 

		self.workingFolder = "dat"
		if len(sys.argv) > 1:
			self.workingFolder = sys.argv[1]

		if not os.path.exists(self.workingFolder):
			os.mkdir(self.workingFolder)

		self.statusFina = self.workingFolder+"/project.dat"
		if not os.path.exists(self.statusFina):
			self.projectState = {}
		else:
			self.projectState = pickle.load(open(self.statusFina, "rt"))

		if "input" not in self.projectState and len(sys.argv) > 2:
			self.projectState["input"] = sys.argv[2]

		if "input" not in self.projectState:
			self.projectState["input"] = "/home/tim/dev/pagesfile/northern_mariana_islands.osm.bz2"
			#self.projectState["input"] = "/media/noraid/tim/earth-20130805062422.osm.bz2"
			#self.projectState["input"] = "/media/noraid/tim/united_kingdom.osm.bz2"

		self.dataImport = DataImport(self.projectState, self.workingFolder)
		self.childrenImport = MultiImport(self.projectState, self.workingFolder, 
			"ch", "children index", xmlprocessing.ReadXml, indexchildren.TagIndex,
			[self.workingFolder+"/ch"])
		self.childrenImport.xmlBuffSize = 100000
		self.spatialImport = MultiImport(self.projectState, self.workingFolder, 
			"sp", "spatial index", xmlprocessing.ReadXml, indexspatial.TagIndex,
			[self.workingFolder+"/sp"])
		self.versionImport = MultiImport(self.projectState, self.workingFolder, 
			"ver", "version index", xmlprocessing.ReadXml, indexversion.TagIndex,
			[self.workingFolder+"/ver"])

		self.mainLayout = QtGui.QVBoxLayout()

		# Data frame
		self.dataImportFrame = QtGui.QFrame()
		self.dataImportFrame.setFrameShape(QtGui.QFrame.StyledPanel)
		self.dataImportLayout = QtGui.QHBoxLayout(self.dataImportFrame)
		self.mainLayout.addWidget(self.dataImportFrame)

		# ******* Data import ********
		self.dataImportLabel = QtGui.QLabel("Data")
		self.dataImportLayout.addWidget(self.dataImportLabel)

		self.dataStartButton = QtGui.QPushButton("Start")
		self.dataStartButton.pressed.connect(self.DataStartPressed)
		self.dataImportLayout.addWidget(self.dataStartButton)

		self.dataPauseButton = QtGui.QPushButton("Pause")
		self.dataPauseButton.pressed.connect(self.DataPausePressed)
		self.dataImportLayout.addWidget(self.dataPauseButton)

		self.dataClearButton = QtGui.QPushButton("Clear")
		self.dataClearButton.pressed.connect(self.DataClearPressed)
		self.dataImportLayout.addWidget(self.dataClearButton)

		# Chilren index frame
		self.chImportFrame = QtGui.QFrame()
		self.chImportFrame.setFrameShape(QtGui.QFrame.StyledPanel)
		self.chImportLayout = QtGui.QHBoxLayout(self.chImportFrame)
		self.mainLayout.addWidget(self.chImportFrame)

		# ********* Children index *********
		self.chImportLabel = QtGui.QLabel("Children index")
		self.chImportLayout.addWidget(self.chImportLabel)

		self.chStartButton = QtGui.QPushButton("Start")
		self.chStartButton.pressed.connect(self.ChStartPressed)
		self.chImportLayout.addWidget(self.chStartButton)

		self.chPauseButton = QtGui.QPushButton("Pause")
		self.chPauseButton.pressed.connect(self.ChPausePressed)
		self.chImportLayout.addWidget(self.chPauseButton)

		self.chClearButton = QtGui.QPushButton("Clear")
		self.chClearButton.pressed.connect(self.ChClearPressed)
		self.chImportLayout.addWidget(self.chClearButton)

		# Spatial index frame
		self.spImportFrame = QtGui.QFrame()
		self.spImportFrame.setFrameShape(QtGui.QFrame.StyledPanel)
		self.spImportLayout = QtGui.QHBoxLayout(self.spImportFrame)
		self.mainLayout.addWidget(self.spImportFrame)

		# ********* Spatial index **********
		self.spImportLabel = QtGui.QLabel("Spatial index")
		self.spImportLayout.addWidget(self.spImportLabel)

		self.spStartButton = QtGui.QPushButton("Start")
		self.spStartButton.pressed.connect(self.SpStartPressed)
		self.spImportLayout.addWidget(self.spStartButton)

		self.spPauseButton = QtGui.QPushButton("Pause")
		self.spPauseButton.pressed.connect(self.SpPausePressed)
		self.spImportLayout.addWidget(self.spPauseButton)

		self.spClearButton = QtGui.QPushButton("Clear")
		self.spClearButton.pressed.connect(self.SpClearPressed)
		self.spImportLayout.addWidget(self.spClearButton)

		# Version index frame
		self.verImportFrame = QtGui.QFrame()
		self.verImportFrame.setFrameShape(QtGui.QFrame.StyledPanel)
		self.verImportLayout = QtGui.QHBoxLayout(self.verImportFrame)
		self.mainLayout.addWidget(self.verImportFrame)

		# ******** Version index ******
		self.verImportLabel = QtGui.QLabel("Version index")
		self.verImportLayout.addWidget(self.verImportLabel)

		self.verStartButton = QtGui.QPushButton("Start")
		self.verStartButton.pressed.connect(self.VerStartPressed)
		self.verImportLayout.addWidget(self.verStartButton)

		self.verPauseButton = QtGui.QPushButton("Pause")
		self.verPauseButton.pressed.connect(self.VerPausePressed)
		self.verImportLayout.addWidget(self.verPauseButton)

		self.verClearButton = QtGui.QPushButton("Clear")
		self.verClearButton.pressed.connect(self.VerClearPressed)
		self.verImportLayout.addWidget(self.verClearButton)

		centralWidget = QtGui.QWidget()
		centralWidget.setLayout(self.mainLayout)
		self.setCentralWidget(centralWidget)

		self.timer = QtCore.QTimer()
		self.timer.timeout.connect(self.IdleEvent)
		self.timer.start(10)

		self.show()

	def __del__(self):
		pass

	def closeEvent(self, event):
		print "Write current state"
		print self.projectState
		pickle.dump(self.projectState, open(self.statusFina, "wt"))

	def DataStartPressed(self):
		self.dataImport.Start()

	def DataPausePressed(self):
		self.dataImport.Pause()

	def DataClearPressed(self):
		self.dataImport.Clear()

	def ChStartPressed(self):
		self.childrenImport.Start()

	def ChPausePressed(self):
		self.childrenImport.Pause()

	def ChClearPressed(self):
		self.childrenImport.Clear()

	def SpStartPressed(self):
		self.spatialImport.Start()

	def SpPausePressed(self):
		self.spatialImport.Pause()

	def SpClearPressed(self):
		self.spatialImport.Clear()

	def VerStartPressed(self):
		self.versionImport.Start()

	def VerPausePressed(self):
		self.versionImport.Pause()

	def VerClearPressed(self):
		self.versionImport.Clear()

	def IdleEvent(self):
		self.dataImport.Update()
		self.childrenImport.Update()
		self.spatialImport.Update()
		self.versionImport.Update()
		time.sleep(0.01)


if __name__ == "__main__":

	# Create the application object
	app = QtGui.QApplication(sys.argv)
	
	#wid = QtGui.QWidget()
	#wid.resize(250, 150)
	#wid.setWindowTitle('Simple')
	#wid.show()
	mainWindow = MainWindow()

	app.exec_()
	


