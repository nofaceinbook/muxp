# -*- coding: utf-8 -*-
#******************************************************************************
#
# muxp.py
#        
muxp_VERSION = "0.1.0 exp"
# ---------------------------------------------------------
# Python Tool: Mesh Updater X-Plane (muxp)
#
# For more details refert to GitHub: https://github.com/nofaceinbook/betterflat
#
# WARNING: This code is still under development and may still have some errors.
#
# Copyright (C) 2020 by schmax (Max Schmidt)
#
# This code is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR 
# A PARTICULAR PURPOSE.  See the GNU General Public License for more details.  
#
# A copy of the GNU General Public License is available at:
#   <http://www.gnu.org/licenses/>. 
#
#******************************************************************************


from logging import StreamHandler, FileHandler, getLogger, Formatter
from muxp_math import *
from muxp_area import *
from muxp_file import *
from muxp_KMLexport import *
from xplnedsf2 import *
from os import path, replace
from shutil import copy2
from tkinter import *
from tkinter.filedialog import askopenfilename, askdirectory
from glob import glob #### NEEDED LATER TO SEARCH FOR DSF FILE ALSO IN Custom Scenery Folder
from sys import argv, exit  ### exit only for TESTING ###


def displayHelp(win):
    helpwin = Toplevel(win)
    Label(helpwin, anchor=W, justify=LEFT, text=
          "This program updates the mesh of X-Plane based on a configuration\n"
          "given in a text file (*.muxp). \n"
          "Via the config butten you set your X-Plane base folder and the folder\n"
          "where the updated dsf files are stored. Make sure that this folder\n"
          "has in the scenery.ini file higher priority as other dsf mesh files\n"
          "in order to make changes visible.\n\n"
          "MORE INFORMATION, source code and contact info are\n"
          "available at GitHub: https://github.com/nofaceinbook/muxp/\n\n"
          "Hope the tool helps you.    (c) 2020 by schmax (Max Schmidt)"   
          ).grid(row=0, pady=10, padx=10)


def defineLog(logname, logLevelStream='INFO', logLevelFile='INFO', mode='w+'):
    #
    # defines log-Handler, if Level is set to None no File/Stream handler will be created
    # The file for the stream is written to logname.log
    # Global variable LogName is defined to be used e.g. to create sub-loggers
    # Returns the created logger log to be used
    #
    global LogName
    LogName = logname
    directory = path.dirname(path.abspath(__file__))
    logfile = path.join(directory, logname + '.log')
    log = getLogger(logname)
    log.handlers = []  # Spyder/IPython currently does not remove existing loggers, this does the job
    if logLevelStream == 'DEBUG' or logLevelFile == 'DEBUG':
        log.setLevel('DEBUG') #so maximum level is DEBUG; needed to see with getEffectiveLevel if DEBUG is enabled or not  
    else:
        log.setLevel('INFO') #set maximum level if not DEBUG before restriction by handlers below
    formatter = Formatter('%(name)s-%(levelname)s: %(message)s')
    if logLevelStream:
        stream_handler = StreamHandler()
        stream_handler.setLevel(logLevelStream)
        stream_handler.setFormatter(formatter)
        log.addHandler(stream_handler)
    if logLevelFile:
        file_handler = FileHandler(logfile, mode)
        file_handler.setLevel(logLevelFile)
        file_handler.setFormatter(formatter)
        log.addHandler(file_handler)
    return log
   

class muxpGUI:
    def __init__(self, rf, muxpfile=None):
        self.runfile = rf
        self.xpfolder = ""
        self.muxpfolder = ""
        self.kmlExport = 0

        self.window = Tk()
        self.window.title("Mesh Updater X-Plane (muxp version: {})".format(muxp_VERSION))
 
        self.current_action = "none"  #e.g. set to read or write when operating on dsf file     

        self.dsf = XPLNEDSF(LogName, self.showProgress)  # includes all information about the read dsf-file

        self.header = Label(self.window, text="WARNING - This is still a test version.")
        self.header.grid(row=0, column=0, columnspan=2)
        self.config_button = Button(self.window, text=' Config ', fg='black', command=lambda: self.ConfigMenu())
        self.config_button.grid(row=0, column=2, sticky=W, pady=4, padx=10)        
        self.help_button = Button(self.window, text=' Help ', fg='red', command=lambda: displayHelp(self.window))
        self.help_button.grid(row=0, column=3, sticky=W, pady=4, padx=10)

        self.muxpfile_label = Label(self.window, text="muxp File (*.muxp):")
        self.muxpfile_label.grid(row=1, column=0, sticky=W)
        self.muxpfile_entry = Entry(self.window, width=60)
        self.muxpfile_entry.grid(row=1, column=1, columnspan=2, sticky=W)
        self.muxpfile_select = Button(self.window, text='Select', command=lambda: self.select_muxpfile(self.muxpfile_entry))
        self.muxpfile_select.grid(row=1, column=3, sticky=W, pady=4, padx=10)
        
        self.muxp_start = Button(self.window, text='  Start muxp   ', state=DISABLED, command=lambda: self.runMuxp(self.muxpfile_entry.get()))
        self.muxp_start.grid(row=6, column=0, sticky=E, pady=4)
        self.muxp_status_label = Label(self.window, text="   this can take some minutes....")
        self.muxp_status_label.grid(row=6, column=1, sticky=W)
        self.info_label = Label(self.window, text=" ")
        self.info_label.grid(row=7, column=1, sticky=W, pady=8)
        self.muxp_create = Button(self.window, text='  Create muxp   ', state=DISABLED, command=lambda: self.create_muxp())
        self.muxp_create.grid(row=9, column=0, sticky=E, pady=4)
        self.muxp_undo = Button(self.window, text='  Undo muxp   ', state=DISABLED, command=lambda: self.undo_muxp())
        self.muxp_undo.grid(row=9, column=2, sticky=E, pady=4)        
        log.info("GUI is set up.")
        
        if muxpfile != None: #if muxpfile was given, select it in field
            self.select_muxpfile(self.muxpfile_entry, muxpfile)
        
        error = self.getConfig(runfile)
        if error: #in case of config error, config has to be defined
            self.ConfigMenu()
        else:
            if muxpfile != None: #if muxpfile was given          
                self.runMuxp(muxpfile) ## directly run muxpfile if it was given as argument
        mainloop()


    def getConfig(self, runfile):
        """
        Gets configuration from muxp.config from same directory as runfile.
        Opens ConfigMenu if file is not present and creates file.
        """
        filename = self.runfile[:self.runfile.rfind('.')]+'.config'
        log.info("Searching Config File: {}".format(filename))
        c, err = readMuxpFile(filename, LogName) ## config file self has same syntax as muxpfile
        if c==None:
            log.error("{}".format(err))
            return -1 #error value
        if c['muxpconfigversion'] != "1":
            log.error("Config file has wrong version ({} instead of 1)".format(c['muxpconfigversion']))
            return -1 #error value
        self.xpfolder = c["xpfolder"]
        self.muxpfolder = c["muxpfolder"]
        self.kmlExport = int(c["kmlExport"])
        return 0
        ##### tbd: check that keys are all exist, correct type and open config menu if not ####################
        #if values_read != 4:
        #    log.info("Config not found, not complete or wrong version. Open Config Window!")
        #    self.ConfigMenu()

        
    def showProgress(self, percentage):
        if self.current_action == 'read':
            self.muxp_status_label.config(text = "read {} percent".format(percentage))
        elif self.current_action == 'write':
            self.muxp_status_label.config(text = "written {} percent".format(percentage))
        self.window.update()

        
    def select_muxpfile(self, entry, filename=None): #if file is set it is directly displayed
        if filename == None:
            filename = askopenfilename()
        entry.delete(0, END)
        entry.insert(0, filename)
        self.muxp_start.config(state="normal")
        self.muxpfile_select.config(state="disabled")

        
    def ConfigMenu(self):
        def select_file(entry): #if file is set it is directly displayed
            file = askdirectory()
            entry.delete(0, END)
            entry.insert(0, file)
        configwin = Toplevel(self.window)
        configwin.attributes("-topmost", True)
        toplabel = Label(configwin, anchor=W, justify=LEFT, text="Settings for muxp").grid(row=0, column=0, columnspan=2, pady=10, padx=10)
        xpfolder_label = Label(configwin, text="X-Plane base folder:")
        xpfolder_label.grid(row=1, column=0, pady=4, sticky=E)
        xpfolder_entry = Entry(configwin, width=60)
        xpfolder_entry.grid(row=1, column=1, sticky=W)
        xpfolder_entry.insert(0, self.xpfolder)
        xpfolder_select = Button(configwin, text='Select', command=lambda: select_file(xpfolder_entry))
        xpfolder_select.grid(row=1, column=3, sticky=W, pady=4, padx=10)
        muxpfolder_label = Label(configwin, text="Folder to updated dsf:")
        muxpfolder_label.grid(row=2, column=0, pady=4, sticky=E)
        muxpfolder_entry = Entry(configwin, width=60)
        muxpfolder_entry.grid(row=2, column=1, sticky=W)
        muxpfolder_entry.insert(0, self.muxpfolder)
        muxpfolder_select = Button(configwin, text='Select', command=lambda: select_file(muxpfolder_entry))
        muxpfolder_select.grid(row=2, column=3, sticky=W, pady=4, padx=10)
        kmlExportType = IntVar() # 1 if kml should be exported, 0 if not
        kmlExportType.set(self.kmlExport)
        kmlExportCB = Checkbutton(configwin, text="Export to kml ", variable=kmlExportType)
        kmlExportCB.grid(row=3, column=0, sticky=E, pady=4)
        save_button = Button(configwin, text='  Save  ', command=lambda: self.safeConfig(xpfolder_entry.get(), muxpfolder_entry.get(), kmlExportType.get()))
        save_button.grid(row=10, column=0, pady=4)

        
    def safeConfig(self, xf, mf, ke):
        self.xpfolder = xf
        self.muxpfolder = mf
        self.kmlExport = ke
        log.info("Saving config {}, {}, {}".format(xf, mf, ke))
        filename = self.runfile[:self.runfile.rfind('.')]+'.config'
        with open(filename, "w", encoding="utf8", errors="ignore") as f:
            f.write("muxpconfigversion:  1\n")
            f.write("xpfolder:  {}\n".format(self.xpfolder))
            f.write("muxpfolder:  {}\n".format(self.muxpfolder))
            f.write("kmlExport:  {}\n".format(self.kmlExport))


    def runMuxp(self, filename):
        """
        Updates the mesh based on the muxp file.
        """
        update, error = readMuxpFile(filename, LogName)
        if update == None:
            log.error("muxpfile does not exist!")
            ### tbd: show error in GUI ####
            return
        error = validate_muxp(update) ### tbd: check if all relevant values are in and transform all values
        log.info("Command Dictionary: {}".format(update))
        if error != None:
            log.error(error) ### tbd: show error in GUI ###
        log.info("muxpfile id: {} version: {} for area:{} with {} commands read.".format(update["id"], update["version"], update["area"], len(update["commands"])))
        log.info("This muxp version only changes default XP mesh....")
        ### tbd: check for other dsf file as hd-mesh etc. in Custom scenery and use the dsf that is loaded to XPlane
        self.muxp_start.config(state="disabled")
        filename = self.xpfolder +  "/Global Scenery/X-Plane 11 Global Scenery/Earth nav data/" + get10grid(update["tile"][:3]) + get10grid(update["tile"][3:]) + "/" + update["tile"] +".dsf"
        writefilename = self.muxpfolder + "/Earth nav data/" + get10grid(update["tile"][:3]) + get10grid(update["tile"][3:]) + "/" + update["tile"] +".dsf"
        log.info("Loading dsf file {}".format(filename))
        self.current_action = "read"
        self.dsf.read(filename)
        a = muxpArea(self.dsf, LogName)
        a.extractMeshArea(*update["area"])
        #### tbd: support multiple area definitons in one muxp file in order to get not too large areas
        
        areabound = [(update["area"][2],update["area"][0]), (update["area"][2],update["area"][1]), (update["area"][3],update["area"][1]), (update["area"][3],update["area"][0]), (update["area"][2],update["area"][0]) ]
        if self.kmlExport:
            kml_filename = self.runfile[:self.runfile.rfind('\\')+1] + update["tile"] + "_dsf"
            log.info("Writing kml file before change to: {}".format(kml_filename + "_beforeMUXP.kml"))
            kmlExport2(self.dsf, [areabound], a.atrias, kml_filename + "_beforeMUXP")

        ##### tbd: update status in window to "updating mesh"
        for c in update["commands"]: #now go through all commands to update
        #### TBD: Log command details and show processing in window status field with name of command
        ############# WARNING: Commands use x, y and Area: y, x coordinates ---> should be unique !!!! --> usy y, x as in apt.dat #####
            log.info("PROCESSING COMMAND: {}".format(c))
            if c["command"] == "update_network_elevation":
                log.info("Updateing network elevation in polygon: {}".format( c["coordinates"]))
                for chain in self.dsf.getChains():
                    points_in_chain = []
                    for v in chain:
                        if PointInPoly((self.dsf.V32[v[0]][v[1]][0], self.dsf.V32[v[0]][v[1]][1]), c["coordinates"]):
                            log.info(v)
                            points_in_chain.append(v) #keep all vertices of current chain that are in polygon
                    if len(points_in_chain) > 1: #only consider chains that have at least two points in polygon
                        log.info("Network chain in Poly {}".format(chain))
                        for p in points_in_chain:
                            log.info("    Is currently in chain as {} id {} to: {}".format(p[0], p[1], self.dsf.V32[p[0]][p[1]]))
                            min_dist = 9999999 #set to max value to find minimum
                            for elevp in c["3d_coordinates"]:
                                if distance(self.dsf.V32[p[0]][p[1]][:2], elevp[:2]) < min_dist: #new minimum found
                                    min_dist = distance((self.dsf.V32[p[0]][p[1]][:2]), elevp[:2])
                                    self.dsf.V32[p[0]][p[1]][2] = elevp[2] # update elevation for network vertex
                            log.info("    Updated vertex pool {} id {} to: {}".format(p[0], p[1], self.dsf.V32[p[0]][p[1]]))
                
            if c["command"] == "cut_polygon":
                #poly = []
                #for coords in c["coordinates"]: ### Also create coords array directly when checking muxp-fil ############
                #    poly.append(coords)
                #c["coordinates"].append(c["coordinates"][0]) #close poly  #### TBD: COORDINATES MUST BE CLOSED IN MUXP-FILE --> done ####
                if not "elevation" in c:  #### TBD: in muxp validation ####
                    c["elevation"] = None
                ### tbd: consider other values as terrain of command
                polysouter, polysinner, borderv = a.CutPoly(c["coordinates"], c["elevation"]) 
                log.info("Outer Polys returned from cut: {}".format(polysouter))
                log.info("Border returned from cut: {}".format(borderv))
                new_polys = polysouter
                for pol in new_polys:
                    pol.append(pol[0])  #polys are returned without last vertex beeing same as first
                new_polys.append(c["coordinates"])
                if self.kmlExport:
                    kmlExport2(self.dsf, new_polys, a.atrias, kml_filename + "_afterMUXP")
        a.createDSFVertices()
        a.insertMeshArea()
        self.current_action = "write"
        self.dsf.write(writefilename)
        self.dsf.read(writefilename) #---> Reading can be used for testing
        exit(0) ###################### TBD: END HERE ONLY if program was called with muxp file as argument #################################

    
########### MAIN #############
log = defineLog('muxp', 'INFO', 'INFO') #no log on console for EXE version --> set first INFO to None
log.info("Started muxp Version: {}".format(muxp_VERSION))
runfile = argv[0]
if len(argv) > 1:
    muxpfile = argv[1]
else:
    muxpfile = None
main = muxpGUI(runfile, muxpfile)

