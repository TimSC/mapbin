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
			self.projectState["input"] = "/home/tim/dev/pagesfile/northern_mariana_islands.osm.bz2"
		self.running = False
		self.parser = None

		self.mainLayout = QtGui.QVBoxLayout()

		self.startButton = QtGui.QPushButton("Start")
		self.startButton.pressed.connect(self.StartPressed)
		self.mainLayout.addWidget(self.startButton)

		self.pauseButton = QtGui.QPushButton("Pause")
		self.pauseButton.pressed.connect(self.PausePressed)
		self.mainLayout.addWidget(self.pauseButton)

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
		pickle.dump(self.projectState, open(self.statusFina, "wt"))

	def StartPressed(self):
		print "StartPressed"

		if self.parser is None:
			self.outfi = compressedfile.CompressedFile(self.workingFolder+"/data")
			self.tagIndex = indexdata.TagIndex(self.workingFolder+"/data")
			self.parser = xmlprocessing.RewriteXml(self.outfi)
			self.parser.TagLimitCallback = self.tagIndex.TagLimitCallback
			self.parser.StartIncremental(bz2.BZ2File(self.projectState["input"]))

		self.running = True

	def PausePressed(self):
		print "PausePressed"
		self.running = False

	def IdleEvent(self):
		if self.running:
			ret = self.parser.DoIncremental()
			if ret == 1:
				self.running = False
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
	


