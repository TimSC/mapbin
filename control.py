#!/usr/bin/python
 
import sys, os, pickle, time, bz2
import indexdata, xmlprocessing, indexchildren
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

		if self.projectState["dat-done"] is not None:
			print "Data index already done"
			return

		if self.parser is None:
			if "dat-created" not in self.projectState:
				self.projectState["dat-created"] = False

			if not self.projectState["dat-created"]:
				self.outfi = compressedfile.CompressedFile(self.workingFolder+"/data", createFile=True)
				self.tagIndex = indexdata.TagIndex(self.workingFolder+"/data", createFile=True)
				self.parser = xmlprocessing.RewriteXml(self.outfi)
				self.parser.TagLimitCallback = self.tagIndex.TagLimitCallback
				self.parser.StartIncremental(bz2.BZ2File(self.projectState["input"]))
			else:
				self.outfi = compressedfile.CompressedFile(self.workingFolder+"/data", createFile=False)
				self.tagIndex = indexdata.TagIndex(self.workingFolder+"/data", createFile=False)

				self.parser = xmlprocessing.RewriteXml(self.outfi)
				self.parser.TagLimitCallback = self.tagIndex.TagLimitCallback

				self.tagIndex.objNumStart = self.projectState["dat-progress"]
				self.parser.outFi.objNumStart = self.projectState["dat-progress"]
				self.parser.StartIncremental(bz2.BZ2File(self.projectState["input"]))

			self.projectState["dat-created"] = True

		self.running = True		

	def Pause(self):
		print "PausePressed"
		if not self.running:
			return
		self.running = False

		objCount1 = self.tagIndex.objs
		objCount2 = self.parser.outFi.objs

		print "Tag index obj count", objCount1
		print "Dat rewrite obj count", objCount2

		self.projectState["dat-progress"] = self.tagIndex.objs

		if objCount1 != objCount2:
			print "Warning: object count mismatch"

		self.tagIndex.flush()
		self.parser.outFi.flush()

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

# ************ Children index class ****************

class ChildrenImport(object):
	def __init__(self, projectState, workingFolder):
		self.projectState = projectState
		self.workingFolder = workingFolder
		self.running = False
		self.parser = None
		self.tagIndex = None

	def __del__(self):
		self.Pause()

		self.parser = None
		self.outfi = None
		self.tagIndex = None

	def Start(self):
		print "StartPressed"
		print self.projectState

		if "ch-done" not in self.projectState:
			self.projectState["ch-done"] = None

		if self.projectState["ch-done"] is not None:
			print "Children index already done"
			return

		if self.parser is None:
			if "ch-created" not in self.projectState:
				self.projectState["ch-created"] = False

			if not self.projectState["ch-created"]:
				self.tagIndex = indexchildren.TagIndex(self.workingFolder+"/ch", createFile=True)
				self.parser = xmlprocessing.ReadXml()
				self.parser.TagLimitCallback = self.tagIndex.TagLimitCallback
				self.parser.StartIncremental(bz2.BZ2File(self.projectState["input"]))
			else:
				self.tagIndex = indexchildren.TagIndex(self.workingFolder+"/ch", createFile=False)

				self.parser = xmlprocessing.ReadXml()
				self.parser.TagLimitCallback = self.tagIndex.TagLimitCallback

				self.tagIndex.objNumStart = self.projectState["ch-progress"]
				self.parser.StartIncremental(bz2.BZ2File(self.projectState["input"]))

			self.projectState["ch-created"] = True

		self.running = True

	def Pause(self):
		print "PausePressed"
		if not self.running:
			return
		self.running = False

		objCount1 = self.tagIndex.objs

		print "Tag index obj count", objCount1

		self.projectState["ch-progress"] = self.tagIndex.objs

		self.tagIndex.flush()

	def Clear(self):
		if self.running:
			print "Error: Cannot clear while running"
			return
		print "Clearing existing children index"

		self.projectState["ch-created"] = False
		self.projectState["ch-progress"] = 0
		self.projectState["ch-done"] = None

		self.parser = None
		self.outfi = None
		self.tagIndex = None

	def Update(self):
		if self.running:
			try:
				ret = self.parser.DoIncremental()
			except Exception as err:
				print "ch import failed", err
				self.running = False
				ret = 0
			if ret == 1:
				print "Stopping ch import, all done"
				self.running = False
				self.projectState["ch-progress"] = self.tagIndex.objs
				self.projectState["ch-done"] = self.tagIndex.objs
				self.tagIndex.flush()

# ************ Main GUI *******************

class MainWindow(QtGui.QMainWindow):
	def __init__(self):
		super(MainWindow, self).__init__() 

		self.workingFolder = "dat"

		if not os.path.exists(self.workingFolder):
			os.mkdir(self.workingFolder)

		self.statusFina = self.workingFolder+"/project.dat"
		if not os.path.exists(self.statusFina):
			self.projectState = {}
		else:
			self.projectState = pickle.load(open(self.statusFina, "rt"))

		if "input" not in self.projectState:
			self.projectState["input"] = "/home/tim/dev/pagesfile/northern_mariana_islands.osm.bz2"
			#self.projectState["input"] = "/media/noraid/tim/earth-20130805062422.osm.bz2"
			#self.projectState["input"] = "/media/noraid/tim/united_kingdom.osm.bz2"

		self.dataImport = DataImport(self.projectState, self.workingFolder)
		self.childrenImport = ChildrenImport(self.projectState, self.workingFolder)

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
		pass

	def SpPausePressed(self):
		pass

	def SpClearPressed(self):
		pass

	def VerStartPressed(self):
		pass

	def VerPausePressed(self):
		pass

	def VerClearPressed(self):
		pass

	def IdleEvent(self):
		self.dataImport.Update()
		self.childrenImport.Update()
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
	


