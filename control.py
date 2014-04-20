#!/usr/bin/python
 
import sys, os, pickle, time, bz2
import indexdata, xmlprocessing
from pycontainers import compressedfile, hashtable
import PySide
import PySide.QtGui as QtGui
import PySide.QtCore as QtCore

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
			#self.projectState["input"] = "/home/tim/dev/pagesfile/northern_mariana_islands.osm.bz2"
			#self.projectState["input"] = "/media/noraid/tim/earth-20130805062422.osm.bz2"
			self.projectState["input"] = "/media/noraid/tim/united_kingdom.osm.bz2"
		self.running = False
		self.parser = None

		self.mainLayout = QtGui.QVBoxLayout()

		self.startButton = QtGui.QPushButton("Start")
		self.startButton.pressed.connect(self.StartPressed)
		self.mainLayout.addWidget(self.startButton)

		self.pauseButton = QtGui.QPushButton("Pause")
		self.pauseButton.pressed.connect(self.PausePressed)
		self.mainLayout.addWidget(self.pauseButton)

		self.clearButton = QtGui.QPushButton("Clear")
		self.clearButton.pressed.connect(self.ClearPressed)
		self.mainLayout.addWidget(self.clearButton)

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

	def StartPressed(self):
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

	def PausePressed(self):
		print "PausePressed"
		self.running = False

		objCount1 = self.tagIndex.objs
		objCount2 = self.parser.outFi.objs

		print "Tag index obj count", objCount1
		print "Dat rewrite obj count", objCount2

		self.projectState["dat-progress"] = self.tagIndex.objs

		if objCount1 != objCount2:
			print "Warning: object count mismatch"

	def ClearPressed(self):
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

	def IdleEvent(self):
		if self.running:
			ret = self.parser.DoIncremental()
			if ret == 1:
				print "Stopping dat import, all done"
				self.running = False
				self.projectState["dat-progress"] = self.tagIndex.objs
				self.projectState["dat-done"] = self.tagIndex.objs

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
	


