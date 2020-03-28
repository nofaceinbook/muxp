# -*- coding: utf-8 -*-
#******************************************************************************
#
# muxp.py
#        
muxp_VERSION = "0.1.1 exp"
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
from os import path, replace, mkdir
from shutil import copy2
from tkinter import *
from tkinter.filedialog import askopenfilename, askdirectory
from glob import glob #### NEEDED LATER TO SEARCH FOR DSF FILE ALSO IN Custom Scenery Folder
from sys import argv
from time import time #currently needed to include creation time in dsf file


def displayHelp(win):
    helpwin = Toplevel(win)
    Label(helpwin, anchor=W, justify=LEFT, text=
          "This program updates the mesh of X-Plane based on a configuration\n"
          "given in a text file (*.muxp). \n"
          "Via the config butten you set your X-Plane base folder and the folder\n"
          "where the updated dsf files are stored. Make sure that this folder\n"
          "has in the scenery_packs.ini file higher priority as other dsf mesh files\n"
          "in order to make changes visible.\n\n"
          "MORE INFORMATION, source code and contact info are\n"
          "available at GitHub: https://github.com/nofaceinbook/muxp/\n\n"
          "Hope the tool helps you.    (c) 2020 by schmax (Max Schmidt)\n\n"
          "IMPORTANT: This tool is in an early development stage.\n"
          "                         Everything you are doing, you do on your own risk!"
          ).grid(row=0, pady=10, padx=10)

def displayNote(win, note):
    notewin = Toplevel(win)
    notewin.attributes("-topmost", True)
    Label(notewin, anchor=W, justify=LEFT, text=note).grid(row=0, pady=10, padx=10)

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
        self.configversion = None
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
            displayNote(self.window, "Configuration file 'muxp.config' not found (check muxp.log) or\nyou are starting muxp the first time.\n\n" +
                                     "When you start muxp the first time you need to set X-Plane folder and \na folder for the updated dsf files.\n" +
                                     "This folder needs to be your 'Custom Scenery' folder of X-Plane.\nYou can also choose to generate a new folder 'zmuxp mesh updates'.\n" +
                                     "Only mesh whith lower priority as this file in 'scenery_packs.ini'\ncan be seen after update.\n\n" +
                                     "IMPORTANT: This tool is in an early development stage.\n                       All you are doing you do on your own risk!")
            self.ConfigMenu()
        else:
            if muxpfile != None: #if muxpfile was given          
                error = self.runMuxp(muxpfile) #directly run muxpfile if it was given as argument
        if muxpfile == None or error: #program that was run directly, terminates directly in case of no errors
            mainloop()


    def getConfig(self, runfile):
        """
        Gets configuration from muxp.config from same directory as runfile.
        Opens ConfigMenu if file is not present and creates file.
        """
        filename = self.runfile[:self.runfile.rfind('.')]+'.config'
        log.info("Searching Config File: {}".format(filename))
        c, err = readMuxpFile(filename, LogName) ## config file self has same syntax as muxpfile
        log.info("   Config read: {}".format(c))
        if c==None:
            log.error("{}".format(err))
            return -1 #error value
        if 'muxpconfigversion' not in c:
            log.error("Version in muxp config file missing!")
            return -2 #error value
        try:
            self.configversion = int(c['muxpconfigversion'])
        except ValueError:
            log.error("Config file version is not of type int")
            return -2
        if self.configversion != 1:
            log.error("Config file has wrong version ({} instead of 1)".format(c['muxpconfigversion']))
            return -2 #error value
        if "xpfolder" not in c or "muxpfolder" not in c:
            log.error("Config file has no value for xpfolder or muxpfolder.")
            return -3 #error value
        self.xpfolder = c["xpfolder"]
        self.muxpfolder = c["muxpfolder"]
        if "kmlExport" in c:
            try:
                self.kmlExport = int(c['kmlExport'])
            except ValueError:
                log.error("kmlExport is not of type int")
                return -4            
        else:
            kmlExport = 0 #default value
        ### Now check if path to X-Plane and Muxp file are existing
        if not path.exists(self.xpfolder+"/Custom Scenery"):
            log.error("The following seems not to be the right path to X-Plane folder (Custom Scenery not found): {}".format(self.xpfolder))
            return -5
        if not path.exists(self.muxpfolder):
            log.error("The following seems not to be the right path to muxp-folder with updated dsf-files: {}".format(self.muxpfolder))
            return -5
        return 0 #no error

        
    def showProgress(self, percentage):
        if self.current_action == 'read':
            self.muxp_status_label.config(text = "read dsf-file ({} percent)".format(percentage))
        elif self.current_action == 'write':
            self.muxp_status_label.config(text = "write updated dsf-file ({} percent)".format(percentage))
        self.window.update()

        
    def select_muxpfile(self, entry, filename=None): #if file is set it is directly displayed
        if filename == None:
            filename = askopenfilename()
        entry.delete(0, END)
        entry.insert(0, filename)
        self.muxp_start.config(state="normal")
        self.muxpfile_select.config(state="disabled")


    def create_muxpfolder(self, xpfolder, info_label, muxpfolder_entry):
        muxp_scenery = "Custom Scenery/zMUXP_mesh_updates"
        inifile = xpfolder + "/Custom Scenery/scenery_packs.ini"
        inicopy = xpfolder + "/Custom Scenery/scenery_packs.beforeMUXP"
        new_infile = []
        log.info("CREATE MUXP-FOLDER: {}".format(xpfolder + "/" + muxp_scenery))
        if not path.exists(xpfolder + "/Custom Scenery"):
            log.error("X-Plane folder not existing or not correct: {}".format(xpfolder))
            info_label.config(text = "Set correct XP-Folder first")
            return -1
        if path.exists(xpfolder + "/" + muxp_scenery): #muxp folder already exists
            log.error("This muxp folder for mesh updates exists already!")
            info_label.config(text = "folder already exists")
            muxpfolder_entry.delete(0, END)
            muxpfolder_entry.insert(0, xpfolder + "/" + muxp_scenery)
            return -1
        else: #create the muxp folder
            mkdir(xpfolder + "/" + muxp_scenery)
        if not path.exists(inifile):
            log.error("scenery_packs.ini missing in: {}".format(xpfolder + "/Custom Scenery"))
            info_label.config(text = "scenery_packs.ini missing in Custom Scenery")
            return -2        
        if not path.exists(xpfolder + inicopy): #Copy current scenery ini if not backed up already
            copy2(inifile ,inicopy)
            log.info("Backup of current scenery_packs.ini saved to: {}".format(inicopy))
        with open(inifile, encoding="utf8", errors="ignore") as f:
            folder_inserted = False
            for line in f:
                if line.startswith("SCENERY_PACK") and not folder_inserted:
                    scenery = line[line.find(" ")+1:]
                    if scenery > "Custom Scenery/zMUXP mesh updates":
                        log.info("   Include muxp-folder for updated dsf-files in scenery_packs.ini before: {}".format(scenery))
                        new_infile.append("SCENERY_PACK Custom Scenery/zMUXP mesh updates\n")
                        folder_inserted = True
                new_infile.append(line)
            if not folder_inserted:
                new_infile.append("SCENERY_PACK Custom Scenery/zMUXP mesh updates\n")
                log.info("   Added muxpfolder for updated dsf-files at end of scenery_packs.ini.")
        with open(inifile, "w", encoding="utf8", errors="ignore") as f:
            for line in new_infile:
                f.write(line)
        info_label.config(text = "folder created & scenery_packs.ini updated")
        muxpfolder_entry.delete(0, END)
        muxpfolder_entry.insert(0, xpfolder + "/" + muxp_scenery)
        return 0 #no error
       

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
        xpfolder_entry = Entry(configwin, width=70)
        xpfolder_entry.grid(row=1, column=1, columnspan=2, sticky=W)
        xpfolder_entry.insert(0, self.xpfolder)
        xpfolder_select = Button(configwin, text='Select', command=lambda: select_file(xpfolder_entry))
        xpfolder_select.grid(row=1, column=3, sticky=W, pady=4, padx=10)
        muxpfolder_label = Label(configwin, text="Folder to updated dsf:")
        muxpfolder_label.grid(row=2, column=0, pady=4, sticky=E)
        muxpfolder_entry = Entry(configwin, width=70)
        muxpfolder_entry.grid(row=2, column=1, columnspan=2, sticky=W)
        muxpfolder_entry.insert(0, self.muxpfolder)
        muxpfolder_select = Button(configwin, text='Select', command=lambda: select_file(muxpfolder_entry))
        muxpfolder_select.grid(row=2, column=3, sticky=W, pady=4, padx=10)
        muxp_create_label = Label(configwin, text="creates folder & updates scenery-pack.ini")
        muxp_create_label.grid(row=3, column=2, sticky=W)
        muxpfolder_create = Button(configwin, text="Create folder for updated dsf", command=lambda: self.create_muxpfolder(xpfolder_entry.get(), muxp_create_label, muxpfolder_entry))
        muxpfolder_create.grid(row=3, column=1, sticky=W, pady=4, padx=10)
        kmlExportType = IntVar() # 1 if kml should be exported, 0 if not
        kmlExportType.set(self.kmlExport)
        kmlExportCB = Checkbutton(configwin, text="Export to kml ", variable=kmlExportType)
        kmlExportCB.grid(row=4, column=0, sticky=E, pady=4)
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
            self.muxp_status_label.config(text="muxp-file ERROR")
            self.info_label.config(text="MUXP-file {} not found.".format(filename))
            log.error("MUXP-file {} not found.".format(filename))
            return -1
        error, resultinfo = validate_muxp(update, LogName) ### tbd: check if all relevant values are in and transform all values
        log.info("Command Dictionary: {}".format(update))
        if error: #positive values mean that processing can still be performed
            displayNote(self.window, resultinfo + "\nCheck muxp.log for details.")
        if error < 0: #In case of real erros, processing Muxp has to be stopped
            self.muxp_status_label.config(text="muxp-file validation ERROR")
            self.info_label.config(text="Validation Error Code {}. Refer muxp.log for details.".format(error))
            return -2
        log.info("muxpfile id: {} version: {} for area:{} with {} commands read.".format(update["id"], update["version"], update["area"], len(update["commands"])))
        log.info("This muxp version only changes default XP mesh....")
        #################### tbd: check for other dsf file as hd-mesh etc. in Custom scenery and use the dsf that is loaded to XPlane #################
        self.muxp_start.config(state="disabled")
        filename = self.xpfolder +  "/Global Scenery/X-Plane 11 Global Scenery/Earth nav data/" + get10grid(update["tile"][:3]) + get10grid(update["tile"][3:]) + "/" + update["tile"] +".dsf"
        log.info("Loading dsf file {}".format(filename))
        self.current_action = "read"
        self.dsf.read(filename)
        a = muxpArea(self.dsf, LogName)
        a.extractMeshArea(*update["area"])
        
        areabound = [(update["area"][2],update["area"][0]), (update["area"][2],update["area"][1]), (update["area"][3],update["area"][1]),
                     (update["area"][3],update["area"][0]), (update["area"][2],update["area"][0]) ]
        
        if self.kmlExport:
            ######## TBD: incl. road segments in kml and allow to show different polygons, points with different color settings ##########
            ######## TBD: incl. parameter which aspects like raster, roads etc. should be shown ##################
            kml_filename = self.runfile[:self.runfile.rfind('\\')+1] + update["tile"] + "_dsf"
            log.info("Writing kml file before change to: {}".format(kml_filename + "_beforeMUXP.kml"))
            kmlExport2(self.dsf, [areabound], a.atrias, kml_filename + "_beforeMUXP")


        for c_index, c in enumerate(update["commands"]): #now go through all commands to update
            
            ### show currently processed command (incl. name if given) in GUI
            if "name" in c:
                command_name = c["name"]
            self.muxp_status_label.config(text = "Processing {}  {}".format(c["command"], command_name))
            self.window.update()
            log.info("--------------------------------------------------------------------")
            log.info("PROCESSING COMMAND: {}".format(c))
            
            if c["command"] == "update_network_levels":
                ###### tbd: put details below to separate file like mux.area.py #################
                ###### tbd: support creation of road segments incl. insertion of addtional vertices #################
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
                            for elevp in c["road_coords_drapped"]:
                                if distance(self.dsf.V32[p[0]][p[1]][:2], elevp[:2]) < min_dist: #new minimum found
                                    min_dist = distance((self.dsf.V32[p[0]][p[1]][:2]), elevp[:2])
                                    self.dsf.V32[p[0]][p[1]][2] = elevp[2] # update elevation for network vertex
                            log.info("    Updated vertex pool {} id {} to: {}".format(p[0], p[1], self.dsf.V32[p[0]][p[1]]))
                ##### TBD: kml-export with roads ###
                
            if c["command"] == "cut_polygon":
                ###### tbd: support further values like terrain and accuracy ####################
                polysouter, polysinner, borderv = a.CutPoly(c["coordinates"], c["elevation"]) 
                log.info("Outer Polys returned from cut: {}".format(polysouter))
                log.info("Inner Polys returned from cut: {}".format(polysinner))
                log.info("Border returned from cut: {}".format(borderv))
                shown_polys = polysouter
                for pol in shown_polys:
                    pol.append(pol[0])  #polys are returned without last vertex beeing same as first
                shown_polys.append(c["coordinates"]) 
                if self.kmlExport:
                    kmlExport2(self.dsf, shown_polys, a.atrias, kml_filename + "_cmd_{}".format(c_index))
                    
        a.createDSFVertices()
        a.insertMeshArea()
        if "muxp/HashDSFbaseFile" not in self.dsf.Properties: #store the file hash of the base dsf file 
            self.dsf.Properties["muxp/HashDSFbaseFile"] = str(self.dsf.FileHash)
        this_muxp_property = "muxp/" + update["id"] + "/"
        self.dsf.Properties[this_muxp_property + "version"] = update["version"]
        self.dsf.Properties[this_muxp_property + "author"] = update["author"]
        self.dsf.Properties[this_muxp_property + "area"] = "{} {} {} {}".format(update["area"][0], update["area"][1], update["area"][2], update["area"][3])
        self.dsf.Properties[this_muxp_property + "time"] = str(int(time()))
        log.info(self.dsf.Properties)
        self.current_action = "write"
        #Check that all required folders for writing updated dsf do exist and create if missing
        if not path.exists(self.muxpfolder):
            log.error("muxpfolder for saving dsf updates does not exisit: {}".format(self.muxpfolder))
            self.muxp_status_label.config(text="muxp-folder ERROR")
            self.info_label.config(text="muxpfolder {} not existing.".format(self.muxpfolder))
            return -70 #error
        if not path.exists(self.muxpfolder + "/Earth nav data"):
            mkdir(self.muxpfolder + "/Earth nav data")
            log.info("Created 'Earth nav data' folder in: {}".format(self.muxpfolder))
        writefolder = self.muxpfolder + "/Earth nav data/" + get10grid(update["tile"][:3]) + get10grid(update["tile"][3:])
        if not path.exists(writefolder):
            mkdir(writefolder)
            log.info("Created new 10grid folder in muxpfolder: {}".format(writefolder))
        self.dsf.write(writefolder +  "/" + update["tile"] +".dsf")
        #self.current_action = "read"  #---> Reading can be used for testing
        #self.dsf.read(writefolder +  "/" + update["tile"] +".dsf") #---> Reading can be used for testing
        return 0 #processed muxp without error

    
########### MAIN #############
log = defineLog('muxp', 'INFO', 'INFO') #no log on console for EXE version --> set first INFO to None
log.info("Started muxp Version: {}".format(muxp_VERSION))
runfile = argv[0]
if len(argv) > 1:
    muxpfile = argv[1]
else:
    muxpfile = None
main = muxpGUI(runfile, muxpfile)

