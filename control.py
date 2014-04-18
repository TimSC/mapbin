#!/usr/bin/python
 
import sys, os, pickle
 
import PySide
import PySide.QtGui as QtGui

if __name__ == "__main__":

	workingFolder = "dat"

	if not os.path.exists(workingFolder):
		os.mkdir(workingFolder)

	statusFina = workingFolder+"/project.dat"
	if not os.path.exists(statusFina):
		projectState = {}
	else:
		projectState = pickle.load(open(statusFina, "rt"))

	if "input" not in projectState:
		projectState["input"] = "/home/tim/dev/pagesfile/northern_mariana_islands.osm.bz2"

	# Create the application object
	app = QtGui.QApplication(sys.argv)
	
	wid = QtGui.QWidget()
	wid.resize(250, 150)
	wid.setWindowTitle('Simple')
	wid.show()

	app.exec_()
	

	pickle.dump(projectState, open(statusFina, "wt"))


