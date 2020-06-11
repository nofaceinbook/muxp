# -*- coding: utf-8 -*-
# ******************************************************************************
#
# muxp.py
#        
muxp_VERSION = "0.2.0 exp"
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
# ******************************************************************************

# New in 0.2.0: update_elevation_in_poly command
# New in 0.2.0: updated that in activatePack the scenery where packs is inserted in ini file is not lost
# New in 0.2.0: Allow additional configurations to be set and saved in .config
# New in 0.2.0: In activateSceneryPack creat also scenery_packs.beforeMUXP if not yet exists
# New in 0.2.0: If default scenery is set as source in .config than first checks muxpfolder if this tile exists to be updated

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
from sys import argv, exit #### exit just for testing !!!####


def displayHelp(win):
    helpwin = Toplevel(win)
    Label(helpwin, anchor=W, justify=LEFT, text=
          "This program updates the mesh of X-Plane based on a configuration\n"
          "given in a text file (*.muxp). \n"
          "Via the config button you set your X-Plane base folder and the folder\n"
          "where the updated default dsf files are stored.\n"
          "When updating meshes keep in mind that they are only visible when\n"
          "the according scenery pack in the scenery_packs.ini has higher\n"
          "priority than dsf mesh files in other scneery packs.\n\n"
          "MORE INFORMATION, source code and contact info are\n"
          "available at GitHub: https://github.com/nofaceinbook/muxp/\n\n"
          "Hope the tool helps you.    (c) 2020 by schmax (Max Schmidt)\n\n"
          "IMPORTANT: This tool is in an early development stage.\n"
          "                         Everything you are doing, you do it at your own risk!"
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
        self.dsf_sceneryPack = "" #Name of the scenery Pack of dsf file to be processed
        self.conflictStrategy = "" #Strategy how to handle conflict with already existing updates in dsf-file
        self.activatePack = 0 #set to 1/True if after writing of updated dsf file it shall be ensured that scenery is activated in scenery_Packs.ini

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
                                     "When you start muxp the first time you need to set X-Plane folder and \na folder for the updated default dsf files.\n" +
                                     "This folder needs to be inside your 'Custom Scenery' folder of X-Plane.\nYou can also choose to generate a new folder\n"
                                     "like 'zzzz_muxp_default_mesh_updates'.\n" +
                                     "Very low priority in 'scenery_packs.ini' is sufficient, as it is only \nused for replacing default scenery.\n\n" +
                                     "IMPORTANT: This tool is in an early development stage.\n                       All you are doing, you do it at your own risk!")
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
        self.xpfolder = c["xpfolder"].strip()
        if self.xpfolder.find("[INSIDE]") == 0:  # Allow to get X-Plane folder based on current folder where run/config file is in
            head, tail = path.split(path.abspath(path.dirname(runfile)))
            while len(tail) > 0:
                if tail == "Custom Scenery" or path.exists(path.join(head, 'X-Plane.exe')):
                    self.xpfolder = head
                    log.info("Set X-Plane folder to: {}".format(self.xpfolder))
                    break
                head, tail = path.split(head)
            if len(tail) == 0:
                log.error("Not inside X-Plane folder as stated in config file. X-Plane Folder not set! Current folder is: {}".format(path.abspath(path.dirname(runfile))))
                self.xpfolder = ""
                return -3
        self.muxpfolder = c["muxpfolder"].strip()
        if self.muxpfolder.find("[THIS_FOLDER]") == 0: 
            self.muxpfolder = path.abspath(path.dirname(runfile))
            log.info("Set MUXP folder to: {}".format(self.muxpfolder))
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
        if "dsfSourcePack" in c: #This path is relative from xpfolder
            self.dsf_sceneryPack = c["dsfSourcePack"].strip()
            if self.dsf_sceneryPack != "[ACTIVE]" and not path.exists(self.xpfolder + "/" + c["dsfSourcePack"]):
                log.error("DSF Source Package {} given in config file does not exist. It is ignored!".format(self.dsf_sceneryPack))
                self.dsf_sceneryPack = ""
            else:
                log.info("Scenery Source Package set to: {}".format(self.dsf_sceneryPack))
        if "conflictStrategy" in c:
            self.conflictStrategy = c["conflictStrategy"].strip()
            log.info("Conflict Strategy for multiple changes in same DSF file set to: {}".format(self.conflictStrategy))
        if "activatePack" in c:
            try:
                self.activatePack = int(c['activatePack'])
            except ValueError:
                log.error("activatePack is not of type int; value not updated")
            log.info("activatePack set to: {}".format(self.activatePack))        
        return 0 #no error

        
    def showProgress(self, percentage):
        if self.current_action == 'read':
            self.muxp_status_label.config(text="read dsf-file ({} percent)".format(percentage))
        elif self.current_action == 'write':
            self.muxp_status_label.config(text="write updated dsf-file ({} percent)".format(percentage))
        self.window.update()

    def select_muxpfile(self, entry, filename=None):
        # if file is set it is directly displayed
        if filename is None:
            filename = askopenfilename()
            if not filename:
                return

        entry.delete(0, END)
        entry.insert(0, filename)
        self.muxp_start.config(state="normal")
        self.muxpfile_select.config(state="disabled")


    def create_muxpfolder(self, xpfolder, info_label, muxpfolder_entry):
        muxp_scenery = "Custom Scenery/zzzz_MUXP_default_mesh_updates"
        inifile = xpfolder + "/Custom Scenery/scenery_packs.ini"
        inicopy = xpfolder + "/Custom Scenery/scenery_packs.beforeMUXP"
        new_infile = []
        log.info("CREATE MUXP-FOLDER: {}".format(xpfolder + "/" + muxp_scenery))
        if not path.exists(xpfolder + "/Custom Scenery"):
            log.error("X-Plane folder not existing or not correct: {}".format(xpfolder))
            info_label.config(text="Set correct XP-Folder first")
            return -1
        if path.exists(xpfolder + "/" + muxp_scenery): #muxp folder already exists
            log.error("This muxp folder for mesh updates exists already!")
            info_label.config(text="folder already exists")
            muxpfolder_entry.delete(0, END)
            muxpfolder_entry.insert(0, xpfolder + "/" + muxp_scenery)
            return -1
        else: #create the muxp folder
            mkdir(xpfolder + "/" + muxp_scenery)
        if not path.exists(inifile):
            log.error("scenery_packs.ini missing in: {}".format(xpfolder + "/Custom Scenery"))
            info_label.config(text="scenery_packs.ini missing in Custom Scenery")
            return -2        
        if not path.exists(inicopy): #Copy current scenery ini if not backed up already
            copy2(inifile ,inicopy)
            log.info("Backup of current scenery_packs.ini saved to: {}".format(inicopy))
        with open(inifile, encoding="utf8", errors="ignore") as f:
            folder_inserted = False
            for line in f:
                if line.startswith("SCENERY_PACK") and not folder_inserted:
                    scenery = line[line.find(" ")+1:]
                    #log.info("Compare {} with {}".format(scenery, muxp_scenery+'/'))
                    if scenery == muxp_scenery+'/\n': # '/\n' always in .ini at end of folder
                        log.info("   muxp-folder '{}' for updated dsf-files already in scenery_packs.ini".format(scenery))
                        folder_inserted = True
                    elif scenery > muxp_scenery:  
                        log.info("   Include muxp-folder for updated dsf-files in scenery_packs.ini before: {}".format(scenery))
                        new_infile.append("SCENERY_PACK {}/\n".format(muxp_scenery)) # '/' required in ini to be a correct path
                        folder_inserted = True
                new_infile.append(line)
            if not folder_inserted:
                new_infile.append("SCENERY_PACK {}/\n".format(muxp_scenery)) # '/' required in ini to be a correct path
                log.info("   Added muxpfolder for updated dsf-files at end of scenery_packs.ini.")
        with open(inifile, "w", encoding="utf8", errors="ignore") as f:
            for line in new_infile:
                f.write(line)
        info_label.config(text="folder created & scenery_packs.ini updated")
        muxpfolder_entry.delete(0, END)
        muxpfolder_entry.insert(0, xpfolder + "/" + muxp_scenery)
        return 0 #no error

    def activateSceneryPack(self, pack, before_packs):
        """
        Activates a scenery pack by inserting in scenery_packs.ini before other packs
        or at alphabetical order.
        """
        inifile = self.xpfolder + "/Custom Scenery/scenery_packs.ini"
        inibackup = self.xpfolder + "/Custom Scenery/scenery_packs.backupMUXP"
        inicopy = self.xpfolder + "/Custom Scenery/scenery_packs.beforeMUXP"
        new_infile = []
        if not path.exists(inifile):
            log.error("scenery_packs.ini missing in: {}".format(self.xpfolder + "/Custom Scenery"))
            return -1
        if not path.exists(inicopy): #Copy current scenery ini if not backed up already
            copy2(inifile ,inicopy)
            log.info("BASE-Backup of current scenery_packs.ini saved to: {}".format(inicopy))
        copy2(inifile ,inibackup) #In each activation make a backup
        log.info("Backup of current scenery_packs.ini saved to: {}".format(inibackup))
        with open(inifile, encoding="utf8", errors="ignore") as f:
            pack_activated = False
            for line in f:
                if line.startswith("SCENERY_PACK"):
                    scenery = line[line.find(" ")+1:]
                    if scenery == pack+'/\n': # '/\n' always in .ini at end of folder
                        if not pack_activated:
                            new_infile.append("SCENERY_PACK {}/\n".format(pack)) # '/' required in ini to be a correct path
                            log.info("Scenery pack '{}' for updated dsf-file was already in scenery_packs.ini. Set to an active pack.".format(scenery))
                            pack_activated = True
                        else: #older entry for pack still in ini, so remove this entry (not append it to new infile)
                            log.info("Previous entry for scenery pack '{}' removed from scenery_packs.ini.".format(scenery))
                    elif not pack_activated and (scenery > pack or scenery in before_packs):  
                        log.info("Include new scenery pack for updated dsf-files in scenery_packs.ini before: {}".format(scenery))
                        new_infile.append("SCENERY_PACK {}/\n".format(pack)) # '/' required in ini to be a correct path
                        new_infile.append(line) #als keep scenery pack, that was at that position
                        pack_activated = True
                    else:
                        new_infile.append(line) #just keep scenery pack
                else:
                    new_infile.append(line) #just keep line
            if not pack_activated:
                new_infile.append("SCENERY_PACK {}/\n".format(pack)) # '/' required in ini to be a correct path
                log.info("Added new scerny pack for at end of scenery_packs.ini.")
        with open(inifile, "w", encoding="utf8", errors="ignore") as f:
            for line in new_infile:
                f.write(line)
        return 0 #no error       

    def ConfigMenu(self):
        def select_file(entry): #if file is set it is directly displayed
            file = askdirectory()
            entry.delete(0, END)
            entry.insert(0, file)
        def select_pack(entry):
            save_current_self_dsf_sceneryPack = self.dsf_sceneryPack
            scenery_packs = findDSFmeshFiles(None, self.xpfolder, LogName) #None selects all packs that have mesh information regardless of tile
            self.SelectDSF(scenery_packs) #will set selected pack to self.dsf_sceneryPack
            entry.delete(0, END)
            entry.insert(0, self.dsf_sceneryPack)
            self.dsf_sceneryPack = save_current_self_dsf_sceneryPack #by this it is assured that self.dsf_sceneryPack is only changed after pressing Save
        configwin = Toplevel(self.window)
        configwin.attributes("-topmost", True)
        toplabel = Label(configwin, anchor=W, justify=LEFT, text="---  S E T T I N G S   F O R    M U X P  ---").grid(row=0, column=0, columnspan=2, pady=10, padx=10)
        xpfolder_label = Label(configwin, text="X-Plane base folder:")
        xpfolder_label.grid(row=1, column=0, pady=4, sticky=E)
        xpfolder_entry = Entry(configwin, width=70)
        xpfolder_entry.grid(row=1, column=1, columnspan=2, sticky=W)
        xpfolder_entry.insert(0, self.xpfolder)
        xpfolder_select = Button(configwin, text='Select', command=lambda: select_file(xpfolder_entry))
        xpfolder_select.grid(row=1, column=3, sticky=W, pady=4, padx=10)
        muxpfolder_label = Label(configwin, text="Folder to updated DEFAULT dsf:")
        muxpfolder_label.grid(row=2, column=0, pady=4, sticky=E)
        muxpfolder_entry = Entry(configwin, width=70)
        muxpfolder_entry.grid(row=2, column=1, columnspan=2, sticky=W)
        muxpfolder_entry.insert(0, self.muxpfolder)
        muxpfolder_select = Button(configwin, text='Select', command=lambda: select_file(muxpfolder_entry))
        muxpfolder_select.grid(row=2, column=3, sticky=W, pady=4, padx=10)
        muxp_create_label = Label(configwin, text="<-- updates scenery_packs.ini")
        muxp_create_label.grid(row=3, column=2, sticky=W)
        muxpfolder_create = Button(configwin, text="Create folder for updated dsf", command=lambda: self.create_muxpfolder(xpfolder_entry.get(), muxp_create_label, muxpfolder_entry))
        muxpfolder_create.grid(row=3, column=1, sticky=W, pady=4, padx=10)
        advanced_label = Label(configwin, text="______________________  ADVANCED SETTINGS   (Defaults are empty fields) _______________________")
        advanced_label.grid(row=4, column=0, columnspan=3, pady=10, sticky=E)
        kmlExportType = IntVar() # 1 if kml should be exported, 0 if not
        kmlExportType.set(self.kmlExport)
        kmlExportCB = Checkbutton(configwin, text="Export to kml ", variable=kmlExportType)
        kmlExportCB.grid(row=5, column=0, sticky=E, pady=4)
        activatePackType = IntVar() # 1 if pack should be directly activated, 0 if not
        activatePackType.set(self.activatePack)
        activatePackCB = Checkbutton(configwin, text="activate Pack ", variable=activatePackType)
        activatePackCB.grid(row=5, column=1, sticky=E, pady=4)
        activatePackInfo_label = Label(configwin, anchor=W, justify=LEFT, text="<-- updates scenery_packs.ini").grid(row=5, column=2)
        dsfsource_label = Label(configwin, text="Fixed source for dsf (optional):")
        dsfsource_label.grid(row=6, column=0, pady=4, sticky=E)
        dsfsource_entry = Entry(configwin, width=70)
        dsfsource_entry.grid(row=6, column=1, columnspan=2, sticky=W)
        dsfsource_entry.insert(0, self.dsf_sceneryPack)
        dsfsource_select = Button(configwin, text='Select', command=lambda: select_pack(dsfsource_entry))
        dsfsource_select.grid(row=6, column=3, sticky=W, pady=4, padx=10)
        dsfsource_info_label = Label(configwin, anchor=W, justify=LEFT, text="^ Option to use [ACTIVE].    SELECT searches all packs and takes a while!  ^").grid(row=7, column=1, columnspan=2, padx=10)
        conflict_label = Label(configwin, text="Conflict strategy (optional):")
        conflict_label.grid(row=8, column=0, pady=4, sticky=E)
        conflict_entry = Entry(configwin, width=70)
        conflict_entry.grid(row=8, column=1, columnspan=2, sticky=W)
        conflict_entry.insert(0, self.conflictStrategy)
        conflict_info_label = Label(configwin, anchor=W, justify=LEFT, text="^ Options are: IGNORE, CURRENT, ORIGINAL, BACKUP, CANCEL").grid(row=9, column=1, columnspan=2, padx=10)
        buttom_label = Label(configwin, anchor=W, justify=LEFT, text=" ").grid(row=10, column=1, columnspan=2, padx=10)
        save_button = Button(configwin, text='  SAVE  ', command=lambda: self.safeConfig(xpfolder_entry.get(), muxpfolder_entry.get(), kmlExportType.get(), activatePackType.get(), dsfsource_entry.get(), conflict_entry.get()))
        save_button.grid(row=11, column=1, pady=4)

        
    def safeConfig(self, xf, mf, ke, ap, ds, cs):
        self.xpfolder = xf
        self.muxpfolder = mf
        self.kmlExport = ke
        self.activatePack = ap
        self.dsf_sceneryPack = ds
        self.conflictStrategy = cs
        log.info("Saving config {}, {}, {}, {}, {}, {}".format(xf, mf, ke, ap, ds, cs))
        filename = self.runfile[:self.runfile.rfind('.')]+'.config'
        with open(filename, "w", encoding="utf8", errors="ignore") as f:
            f.write("muxpconfigversion:  1\n")
            f.write("xpfolder:  {}\n".format(self.xpfolder))
            f.write("muxpfolder:  {}\n".format(self.muxpfolder))
            f.write("kmlExport:  {}\n".format(self.kmlExport))
            f.write("activatePack:  {}\n".format(self.activatePack))
            f.write("dsfSourcePack: {}\n".format(self.dsf_sceneryPack))
            f.write("conflictStrategy: {}\n".format(self.conflictStrategy))


    def SelectDSF(self, scenery_packs):
        """
        Shows windows with all sceneries in scenery_packs dict
        and waits until usere has selected on scenery in listbox.
        Selected scenery is stored in self.dsf_sceneryPack (relative to xp_folder).
        """
        def done(scenlist, infolabel):
            ids = scenlist.curselection()
            if len(ids) == 0:
                infolabel.config(text="One scenery need to be selected!")
            else:
                selected_secenery = scenlist.get(ids)
                selected_secenery = selected_secenery[selected_secenery.find(":")+2:]
                self.dsf_sceneryPack = selected_secenery
        selectDSFwin = Toplevel(self.window)
        selectDSFwin.attributes("-topmost", True)
        topinfo = Label(selectDSFwin, text="Select DSF File to update:")
        topinfo.grid(row=0, column=0)
        listbox = Listbox(selectDSFwin, width=80)
        listbox.grid(row=1, column=0, columnspan=3)
        for item in scenery_packs.keys():
            listbox.insert(END, scenery_packs[item] + ": " + item )
        buttoninfo = Label(selectDSFwin, text="Important: When not selecting new or active dsf make sure that you re-arrange\n"
                                              "           scenery_packs.ini in order that update becomes visible in X-Plane!\n"
                                              "Press OK after selection.")
        buttoninfo.grid(row=2, column=0)
        okbutton = Button(selectDSFwin, text='  OK  ', command = lambda: done(listbox, buttoninfo)) 
        okbutton.grid(row=3, column=1)
        while self.dsf_sceneryPack == "": #wait until selection is done
            selectDSFwin.update()
        selectDSFwin.destroy()

        
    def handleMUXPconflicts(self, filename, update):
        """
        Checks if there are conflicts for the dsf file like overlapping
        areas and performing same update again on the dsf file.
        Offers to perform changes on orignial file or on backup.
        Returns the filename the user has finally decided to update.
        """
        def done(choice):
            self.conflictStrategy = choice

        filenames = [filename, filename+".muxp.backup", filename+".muxp.original"] #current dsf file, backup dsf file, original dsf file
        issues = ["None", "None", "None"] #assume no issues for files; issues are strings
        props = [None, None, None]
        muxes = ["", "", ""] #included muxp defintions are collected as strings
        #log.info("Conflict handling -- filename: {}   muxpfolder: {}".format(filename, self.muxpfolder))
        if filename.find(self.muxpfolder) == 0: #selected file is in muxpfolder
            filenames[2] = self.xpfolder + "/Global Scenery/X-Plane 11 Global Scenery" + filename[-35:] #then orignial dsf is in global scenery --> should just take the relevant bytes identical in Global Scenery #### TO BE TESTED #####
            log.info("Tile in muxpfolder was selected, so original file is default scenery: {}".format(filenames[2]))
        for i,f in enumerate(filenames): ### TBD: Define all file extensions AND directory names globally
            log.info("Evaluating conflicts for: {} {}".format(i, f))
            if path.exists(f):
                err, props[i] = getDSFproperties(f)
                if err:
                    log.error(props[i])
                    issues[i] = "dsf file error (check log)!"
                else:
                    for mdef in getMUXPdefs(props[i]):
                        muxes[i] += "     muxpID: {} version: {} area: {}\n".format(mdef[0], mdef[1], mdef[2])
                    if areaIntersectionInProps(update['area'], props[i]) != None:
                        issues[i] = "DSF file already updated in area of muxp file."
                    if updateAlreadyInProps(update['id'], props[i]) != None:
                        issues[i] = "DSF file already includes this update" ##overwrites issue intersection, as this is even worse
            else:
                issues[i] = "File does not exist!"
            log.info("    issue: {}  muxp-properties: {}".format(issues[i], muxes[i]))
            if i==0 and issues[0] == "None": return filename #in case of no issues of current file nothing to do, just stay with current file to be updated
        conflictwin = Toplevel(self.window)
        conflictwin.attributes("-topmost", True)
        topinfo = Label(conflictwin, anchor='w', justify=LEFT, text="The DSF file you want to update was already updated in a way that may conflict witht current update.\n"
                                                  "You should think of applying the update to un-muxed dsf file. How do you want to proceed?\n Update details  " +
                                                  "id: " + update["id"] + "  version: " + update["version"] + "  area: {} ".format(update["area"]))
        topinfo.grid(row=0, column=0, columnspan=3)
        scenerylabel = [None, None, None]
        scenerybutton = [None, None, None]
        Label(conflictwin, text="================================================================================").grid(column=0, row=1, columnspan=3)
        for i,dsftype in enumerate(["CURRENT", "BACKUP", "ORIGINAL"]):
            scenerylabel[i] = Label(conflictwin, anchor='w', justify=LEFT, text=dsftype+" DSF FILE:\n   filename: "+filenames[i]+"\n   issue: " + issues[i] + "\n   Included mesh updates:\n" + muxes[i])
            scenerylabel[i].grid(row=2*i+2, column=0, columnspan=2)
            scenerybutton[i] = Button(conflictwin, text=' Update ', command = lambda: done(dsftype)) #### TBD: Colors based on issue ####
            scenerybutton[i].grid(row=2*i+2, column=2)
            Label(conflictwin, text="================================================================================").grid(column=0, row=2*i+3, columnspan=3)
            if issues[i] == "File does not exist!":
                scenerybutton[i].config(state='disabled')
            elif issues[i].find("include") >= 0:
                scenerybutton[i].config(bg='red')
            elif issues[i].find("area") >= 0:
                scenerybutton[i].config(bg='yellow')
            else:
                scenerybutton[i].config(bg='green')

        buttoninfo = Label(conflictwin, text="Select which dsf file you want to update or press Cancel.\n"
                                             "Note: Original dsf will never be overwritten, but current is OVERWRITTEN with new version.\n"
                                             "      When selecting original dsf all previous mesh updates will be lost and would need to be applied again!")
        buttoninfo.grid(row=8, column=0, columnspan=3)
        cancelbutton = Button(conflictwin, text='  CANCEL  ', command = lambda: done("CANCEL")) 
        cancelbutton.grid(row=9, column=1)
        while self.conflictStrategy == "": #wait until selection is done
            conflictwin.update()
        conflictwin.destroy()
        if self.conflictStrategy == "CURRENT": return filenames[0]
        if self.conflictStrategy == "BACKUP": return filenames[1]
        if self.conflictStrategy == "ORIGINAL": return filenames[2]
        if self.conflictStrategy == "CANCEL": return None
        
  
    def runMuxp(self, filename):
        """
        Initiates updating the mesh based on the muxp file (filename).
        """
        ########## IN CASE OF .kml FILE CONVERT TO MUXP FIRST #########
        if filename.rfind(".kml") == len(filename) - 4:  # filename ends with '.kml'
            log.info("Converting kml file: {} to muxp-file.".format(filename))
            filename = kml2muxp(filename)  # converts kml file to a new muxp file (ending .muxp)
            log.info("Finished conversion. Processing now: {}".format(filename))

        ############# READ AND EVALUATE MUXP FILE #####################
        update, error = readMuxpFile(filename, LogName)
        if update == None:
            self.muxp_status_label.config(text="muxp-file ERROR")
            self.info_label.config(text="MUXP-file {} not found.".format(filename))
            log.error("MUXP-file {} not found.".format(filename))
            return -1
        error, resultinfo = validate_muxp(update, LogName) 
        log.info("Command Dictionary: {}".format(update))
        if error: #positive values mean that processing can still be performed
            displayNote(self.window, resultinfo + "\nCheck muxp.log for details.")
        if error < 0: #In case of real erros, processing Muxp has to be stopped
            self.muxp_status_label.config(text="muxp-file validation ERROR")
            self.info_label.config(text="Validation Error Code {}. Refer muxp.log for details.".format(error))
            return -2
        log.info("muxpfile id: {} version: {} for area:{} with {} commands read.".format(update["id"], update["version"], update["area"], len(update["commands"])))
        
        ############### SEARCH AND READ DSF FILE TO ADAPT ######################
        scenery_packs = None # dictionary of scenery packs for according tiles
        if len(self.dsf_sceneryPack) == 0:  # no scenery pack yet defined (e.g. via config file)
            self.muxp_status_label.config(text="Searching available meshes for {}. Please WAIT ...".format(update["tile"]))
            self.muxp_start.config(state="disabled")
            self.window.update()
            scenery_packs = findDSFmeshFiles(update["tile"], self.xpfolder, LogName)
            self.SelectDSF(scenery_packs)  # will set selected pack to self.dsf_sceneryPack
        elif self.dsf_sceneryPack == "[ACTIVE]":
            scenery_packs = findDSFmeshFiles(update["tile"], self.xpfolder, LogName)
            for sp in scenery_packs.keys():
                if scenery_packs[sp] == "ACTIVE":
                    self.dsf_sceneryPack = sp
                    break
            if self.dsf_sceneryPack == "[ACTIVE]":  # if no ACTIVE pack found above
                self.dsf_sceneryPack = "Global Scenery/X-Plane 11 Global Scenery"  # then use Default Scenery as ACTIVE
            log.info("Config requested to use active scenery pack as source, which is: {}".format( self.dsf_sceneryPack))
        else:  # scenery_pack defined (e.g. via config file)
            if self.dsf_sceneryPack.find("X-Plane 11 Global Scenery") >= 0: #in case default XP scenery selected
                if path.exists(self.muxpfolder + "/Earth nav data/" + get10grid(update["tile"]) + "/" + update["tile"] +".dsf"): #and tile is already in muxpfolder
                    self.dsf_sceneryPack = self.muxpfolder[self.muxpfolder.find("Custom Scenery"):]  # choose muxpfolder as scenery_pack to update
                    log.info("As muxp-folder {} includes tile {} this will be updated instead of plain default tile.".format(self.dsf_sceneryPack, update["tile"]))
        dsf_output_filename = self.xpfolder + "/" + self.dsf_sceneryPack + "/Earth nav data/" + get10grid(update["tile"]) + "/" + update["tile"] +".dsf" #this is default dsf filename name for scenery pack
            ### WARNING: In case of default mesh, the dsf_output_filname needs to be changed to the one in muxpfolder (done below)
        #if self.dsf_sceneryPack.find("X-Plane 11 Global Scenery") >= 0:
        #    log.info("Default mesh was selected to be updated. No need to check for conflicts.")
        #    dsf_filename = self.xpfolder + "/" + self.dsf_sceneryPack + "/Earth nav data/" + get10grid(update["tile"]) + "/" + update["tile"] +".dsf"
        #    dsf_output_filname = dsf_filename
        if self.conflictStrategy != "IGNORE": #if IGNORE is set e.g. in config file, do not check for conflicts
            dsf_filename = self.handleMUXPconflicts(dsf_output_filename, update) #Check for conflicts with existing mesh updates in dsf; might result in an other dsf-file to be processed
        else:
            dsf_filename = dsf_output_filename #no conflict so take default (in case of X-Plane default scenery this is clarified below)
            log.info("Conflict Strategey was set to IGNORE, so no check for conflicts!")
        if self.conflictStrategy == "CANCEL":
            log.info("CANCEL was chosen in conflict handling.")
            exit(0)
        log.info("Conflict Strategy {} resulting in follwing dsf file to adapt: {}".format(self.conflictStrategy, dsf_filename))
        if dsf_filename.find("X-Plane 11 Global Scenery") >= 0: #X-Plane default scenery selected  ### TBD: Define String globally to be replaced if it changes #####
            log.info("Adapting default scenery which will then be available in defined muxp folder.")
            self.dsf_sceneryPack = "Global Scenery/X-Plane 11 Global Scenery" #make sure that really the right pack is set
            dsf_output_filename = self.muxpfolder + "/Earth nav data/" + get10grid(update["tile"]) + "/" + update["tile"] +".dsf"
        else:
            log.info("Adapting Custom Scenery  ....")
            if not path.exists(dsf_output_filename + ".muxp.original"): #make sure that the original is saved
                log.info("There is currently no copy of original dsf file available. Generating Copy: {}".format(dsf_output_filename + ".muxp.original"))
                copy2(dsf_filename, dsf_output_filename + ".muxp.original")
        log.info("Loading dsf file {}".format(dsf_filename))
        self.current_action = "read"
        self.dsf.read(dsf_filename)
        
        ############## START PROCESSING MUXP FILE ON DSF FILE ################
        muxp_process_error = self.processMuxp(dsf_filename, update)  ### Returns return value of processing
        if muxp_process_error:
            return muxp_process_error #No writing of dsf file in case of error

        ########## UPDATE PROPERTIES OF DSF ACCORDING TO PROCESSED MUXP FILE #############
        #currentDSFisUNMUXED = False
        if "muxp/HashDSFbaseFile" not in self.dsf.Properties: #store the file hash of the base dsf file 
            self.dsf.Properties["muxp/HashDSFbaseFile"] = str(self.dsf.FileHash)
            #### OPTION: write hex-presentation instead binary string to dsf with binascii.b2a_hex ###
            #currentDSFisUNMUXED = True
        update_number = 0 
        for props in self.dsf.Properties: #check for alread included updates in dsf and find highest number
            if props.startswith("muxp/update/"):
                update_number_read = int(props[12:])
                if update_number_read > update_number:
                    update_number = update_number_read
        update_prop_key = "muxp/update/{}".format(str(update_number + 1)) #next number for new update, start with 1
        #For each update dsf will include property key 'muxp/update/number' with value 'update_id/update_version/updated_area'
        self.dsf.Properties[update_prop_key] = "{}/{}/{} {} {} {}".format(update["id"],update["version"], update["area"][0], update["area"][1], update["area"][2], update["area"][3])
        log.info("Updated dsf.Properties: {}".format(self.dsf.Properties))
        self.current_action = "write"
        
        ################ CREATE BACKUP FROM CURRENT DSF BEFORE WRITING #################
        if path.exists(dsf_output_filename): #only make backup if file exists
            copy2(dsf_output_filename, dsf_output_filename+".muxp.backup")
        
        ############## CHECK WRITE LOCATION AND WRITE UPDATED DSF FILE ##################
        if dsf_filename.find("X-Plane 11 Global Scenery") >= 0: #X-Plane default scenery selected, so file need to be written to muxp Folder
            #Check that all required folders for writing updated dsf to muxp folder do exist and create if missing
            if not path.exists(self.muxpfolder):
                log.error("muxpfolder for saving dsf updates does not exisit: {}".format(self.muxpfolder))
                self.muxp_status_label.config(text="muxp-folder ERROR")
                self.info_label.config(text="muxpfolder {} not existing.".format(self.muxpfolder))
                return -70 #error
            if not path.exists(self.muxpfolder + "/Earth nav data"):
                mkdir(self.muxpfolder + "/Earth nav data")
                log.info("Created 'Earth nav data' folder in: {}".format(self.muxpfolder))
            writefolder = self.muxpfolder + "/Earth nav data/" + get10grid(update["tile"]) 
            if not path.exists(writefolder):
                mkdir(writefolder)
                log.info("Created new 10grid folder in muxpfolder: {}".format(writefolder))
            #dsf_output_filename = writefolder + "/" + update["tile"] +".dsf" ## already set above
        log.info("Writing updated dsf file to: {}".format(dsf_output_filename))
        self.dsf.write(dsf_output_filename)   ### TBD: Error checking if writing fails ################
        
        #################### ACTIVATE SCENERY PACK ################
        if self.activatePack:
            self.muxp_status_label.config(text = "Checking if updated dsf is active in\n    scenery_packs.ini and updating when required.")  
            self.window.update()            
            if scenery_packs == None:
                scenery_packs = findDSFmeshFiles(update["tile"], self.xpfolder, LogName)
            if self.dsf_sceneryPack == "Global Scenery/X-Plane 11 Global Scenery": #in case of default Scenery muxpfolder is the pack
                head, newSceneryPack = path.split(self.muxpfolder)
                newSceneryPack = "Custom Scenery/" + newSceneryPack
            else:
                newSceneryPack = self.dsf_sceneryPack
            if newSceneryPack in scenery_packs and scenery_packs[newSceneryPack] == "ACTIVE":
                log.info("Great your new scenery is already activated in scenery_packs.ini")
            else:
                before_packs = [] #packs that are already in scenery_packs.ini and not disabled; postion of new needs to be before these
                for scen in scenery_packs:
                    if scenery_packs[scen] in ["ACTIVE", "PACK"]:
                        before_packs.append(scen)
                log.info("Updateing scnery_packs.ini and inserting new pack before {} in order that this scenery will be activated in X-Plane".format(before_packs))
                self.activateSceneryPack(newSceneryPack, before_packs)
        
        return 0 #processed muxp without error    
        
    def processMuxp(self, filename, update):
        """
        Adapts the self.dsf according the muxp commands stored in update dict.
        """
        #log.info("Loading dsf file {}".format(filename))
        #self.current_action = "read"
        #self.dsf.read(filename)
        a = muxpArea(self.dsf, LogName)
        a.extractMeshArea(*update["area"])
        elevation_scale = 1 ### IMPORTANT: When command set sub-meter vertices this scale has to be adapted
        
        areabound = [(update["area"][2],update["area"][0]), (update["area"][2],update["area"][1]), (update["area"][3],update["area"][1]),
                     (update["area"][3],update["area"][0]), (update["area"][2],update["area"][0]) ]
        
        if self.kmlExport:
            ######## TBD: incl. road segments in kml and allow to show different polygons, points with different color settings ##########
            ######## TBD: incl. parameter which aspects like raster, roads etc. should be shown ##################
            kml_filename = self.runfile[:self.runfile.rfind('\\')+1] + update["tile"] + "_dsf"
            log.info("Writing kml file before change to: {}".format(kml_filename + "_0.kml"))
            kmlExport2(self.dsf, [areabound], a.atrias, kml_filename + "_0")


        for c_index, c in enumerate(update["commands"]): #now go through all commands to update
            
            ### show currently processed command (incl. name if given) in GUI
            #if "name" in c:
            #    command_name = c["name"]
            self.muxp_status_label.config(text = "Processing {}\n{}".format(c["_command_info"], c["name"]))  #NEW 1.9: showing full processed command info + name should always be present, but normally empty
            self.window.update()
            log.info("--------------------------------------------------------------------")
            log.info("PROCESSING COMMAND: {}".format(c))
            
            if c["command"] == "update_elevation_in_poly":
                log.info("Updateing elevation to: {} in polygon: {}".format(c["elevation"], c["coordinates"]))
                for t in a.atrias: #go through all trias in area
                    for i, p in enumerate(t[0:3]): #all their points
                        if PointInPoly(p[0:2], c["coordinates"]):
                            t[i][2] = c["elevation"]
                            log.info("For coords: {} set elevation to: {}".format(t[i][0:2], t[i][2]))
                if self.kmlExport:
                    kmlExport2(self.dsf, [c["coordinates"]], a.atrias, kml_filename + "_{}".format(c_index+1))
                                
            
            if c["command"] == "update_network_levels":
                ###### tbd: put details below to separate file like mux.area.py #################
                ###### tbd: support creation of road segments incl. insertion of addtional vertices #################
                log.info("Updating network elevation in polygon: {}".format( c["coordinates"]))
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
                    kmlExport2(self.dsf, shown_polys, a.atrias, kml_filename + "_{}".format(c_index+1))
                    
            if c["command"] == "cut_flat_terrain_in_mesh":
                polysouter, polysinner, borderv = a.CutPoly(c["coordinates"], None, False) #False for not keeping inner trias; None for elevation as only new terrain should get elevation
                ########### TBD: CutPoly should not change elevation, so it would not needed to give parameter None !!! ############
                for vertex in a.getAllVerticesForCoords(borderv): #set borderv to correct elevation
                    vertex[2] = c["elevation"]
                ### NOTE: even if only elevation for terrain is set, the new changed trias will create different looking terrain also outside terrain mesh
                a.createPolyTerrain(c["coordinates"], c["terrain"], c["elevation"])
                for vertex in borderv: #insert in mesh for poly also vertices from surrounding mesh on the border
                    a.splitCloseEdges(vertex)
                shown_polys = polysouter
                for pol in shown_polys:
                    pol.append(pol[0])  #polys are returned without last vertex beeing same as first
                shown_polys.append(c["coordinates"]) 
                if self.kmlExport:
                    kmlExport2(self.dsf, shown_polys, a.atrias, kml_filename + "_{}".format(c_index+1))
                    
            if c["command"] == "cut_spline_segment":
                log.info("Cutting segment as spline for the following elevation profile: {} m".format(c["3d_coordinates"]))
                segment_bound = segmentToBox(c["3d_coordinates"][0], c["3d_coordinates"][-1], c["width"]) #box around first and last vertex with width
                segment_interval_bound = [] #bound including also vertices for interval steps
                for corner1, corner2 in [[1,2], [3,0]]:
                    interval_steps = int(distance(segment_bound[corner1], segment_bound[corner2]) /  c["profile_interval"]) + 1
                    interval_vector = [(segment_bound[corner2][0] - segment_bound[corner1][0]) / interval_steps, (segment_bound[corner2][1] - segment_bound[corner1][1]) / interval_steps]
                    segment_interval_bound.append(segment_bound[corner1-1]) #TBD: Do quicker with extend both values ???
                    segment_interval_bound.append(segment_bound[corner1])
                    for i in range(1,interval_steps): #first and last step not needed as these are corners of segment_bound
                        segment_interval_bound.append([segment_bound[corner1][0] + i * interval_vector[0],  segment_bound[corner1][1] + i * interval_vector[1]])
                segment_interval_bound.append(segment_interval_bound[0]) #add first coordinate to get closed poly
                polysouter, polysinner, borderv = a.CutPoly(segment_interval_bound, None, False) #False for not keeping inner trias; None for elevation as only new terrain should get elevation
                a.createPolyTerrain(segment_interval_bound, c["terrain"], -32768.0, "segment_intervals") #for first step take default elevation -32768 for raster, will be changed below, create trias as "segment_intervals"
                #log.info("BORDER VERTICES: {}".format(borderv))
                #split_trias = [] ## SPLIT TRIAS JUST FOR TESTING --> TO BE REMOVED
                for vertex in borderv: #insert in mesh for poly also vertices from surrounding mesh on the border
                    new_split = a.splitCloseEdges(vertex)   #### assigning split trias is just for testing --> Just call splitCloseEdges; remove split_trias; also definition above !!!! ##################
                #    if len(new_split) > 0: split_trias.extend(new_split)  ### to be removed after testing ###
                xp, yp = [], [] #points for spline to be created
                for p in c["3d_coordinates"]:
                    xp.append(distance([c["3d_coordinates"][0][1], c["3d_coordinates"][0][0]], [p[1], p[0]])) #### IMPORTANT: 3d coordinates currently not swapped !!!!!!!! ##################
                    yp.append(p[2])
                log.info("Points for spline: {}, {}".format(xp, yp))
                spline = getspline(xp, yp)
                log.info("Spline: {}".format(spline))
                for vertex in a.getAllVerticesForCoords(segment_interval_bound): #set vertices of intervals to correct elevation
                    elev, distSplineLine = interpolatedSegmentElevation([c["3d_coordinates"][0], c["3d_coordinates"][-1]], vertex[:2], spline)  #### IMPORTANT: 3d coords not swapped, but interpolation is okay for not swapped #####
                    log.info("Assigning Spline Elevation for {}, {}  to  {} m at distance {}".format(vertex[1], vertex[0], elev, distSplineLine))  ########### TESTING ONLY ############
                    vertex[2] = elev                
                for vertex in a.getAllVerticesForCoords(borderv): #set borderv to correct elevation
                    elev, distSplineLine = interpolatedSegmentElevation([c["3d_coordinates"][0], c["3d_coordinates"][-1]], vertex[:2], spline)   #### IMPORTANT: 3d coords not swapped, but interpolation is okay for not swapped #####
                    vertex[2] = elev
                elevation_scale = 0.05 #allows 5cm elevation steps   #### TBD: Make this value configurable in command #########
                shown_polys = polysouter
                for pol in shown_polys:
                    pol.append(pol[0])  #polys are returned without last vertex beeing same as first
                #shown_polys = [] ####### THIS IS JUST FOR CHECKING WHERE SPLIT TRIAS ARE: TO BE REMOVED ############
                #log.info("SPLIT TRIAS: {}".format(split_trias))
                #for t in split_trias:
                #    pol = []
                #    log.info("current t: {}".format(t))
                #    for e in range(3):
                #        pol.append(t[e][:2])
                #    pol.append(pol[0]) #closed poly
                #    shown_polys.append(pol)
                shown_polys.append(segment_bound) 
                if self.kmlExport:
                    kmlExport2(self.dsf, shown_polys, a.atrias, kml_filename + "_{}".format(c_index+1))
                ######### MAKE SURE THAT VERTICES ARE CREATED ON 5CM OPTION !!!!! ####################
                
                    
            if c["command"] == "limit_edges":
                a.limitEdges(c["coordinates"], c["edge_limit"])
                log.info("Edges in area have been limited")
                if self.kmlExport:
                    kmlExport2(self.dsf, [c["coordinates"]], a.atrias, kml_filename + "_{}".format(c_index))
            
            if c["command"] == "update_raster_elevation":
                log.info("CHANGING FOLLOWING RASTER SQUARES TO ELEVATION OF: {} m".format(c["elevation"]))
                raster_bounds = [c["coordinates"]] #include boundary for raster selection
                for raster_index, raster_corners, raster_center in a.rasterSquares(*BoundingRectangle(c["coordinates"])):
                    include_square = False
                    if c["include_raster_square_criteria"] == "center_inside":
                        if PointInPoly(raster_center, c["coordinates"]): include_square = True
                    elif c["include_raster_square_criteria"] == "square_cuts_poly":
                        log.error("Cut ruster square with poly not yet supported!!!!")  ########## TBD ###############
                    else: #Default case is just one or more corner(s) is/are in square
                        for corner in raster_corners:
                            if PointInPoly(corner, c["coordinates"]): include_square = True
                    if include_square:    
                        log.info("CHANGE RASTER SQUARE {}: {} and center {} to elevation of {}m".format(raster_index, raster_corners, raster_center, c["elevation"])) 
                        raster_corners.append(raster_corners[0]) #make squre to closed poly
                        raster_bounds.append(raster_corners)
                        self.dsf.Raster[0].data[raster_index[0]][raster_index[1]] = c["elevation"]
                if self.kmlExport:
                    kmlExport2(self.dsf, raster_bounds, a.atrias, kml_filename + "_{}".format(c_index+1))
                    
            if c["command"] == "update_raster4spline_segment":
                log.info("CHANGING FOLLOWING RASTER SQUARES on segement for following eleveation profile: {} m".format(c["3d_coordinates"]))
                segment_bound = segmentToBox(c["3d_coordinates"][0], c["3d_coordinates"][-1], c["width"]) #box around first and last vertex with width
                raster_bounds = [segment_bound] #include boundary for raster selection
                xp, yp = [], [] #points for spline to be created
                for p in c["3d_coordinates"]:
                    xp.append(distance([c["3d_coordinates"][0][1], c["3d_coordinates"][0][0]], [p[1], p[0]])) #### IMPORTANT: 3d coordinates currently not swapped !!!!!!!! ##################
                    yp.append(p[2])
                log.info("Points for spline: {}, {}".format(xp, yp))
                spline = getspline(xp, yp)
                log.info("Spline: {}".format(spline))
                for raster_index, raster_corners, raster_center in a.rasterSquares(*BoundingRectangle(segment_bound)):
                    for corner in raster_corners:
                        if PointInPoly(corner, segment_bound):
                            raster_corners.append(raster_corners[0]) #make squre to closed poly
                            raster_bounds.append(raster_corners)
                            elev, distSplineLine = interpolatedSegmentElevation([c["3d_coordinates"][0], c["3d_coordinates"][-1]], raster_center, spline)  #### IMPORTANT: 3d coords not swapped, but interpolation is okay for not swapped #####
                            self.dsf.Raster[0].data[raster_index[0]][raster_index[1]] = round(elev)
                            log.info("Set raster {} to elevation: {}m".format(raster_index, round(elev)))
                            break
                if self.kmlExport:
                    kmlExport2(self.dsf, raster_bounds, a.atrias, kml_filename + "_{}".format(c_index+1))                        

        log.info("DSF vertices created with scaling: {}".format(elevation_scale))
        self.muxp_status_label.config(text = "Creating new vertices and\n   insert mesh update in dsf file")  
        self.window.update()
        a.createDSFVertices(elevation_scale)
        a.insertMeshArea()


    
########### MAIN #############
log = defineLog('muxp', 'INFO', 'INFO') #no log on console for EXE version --> set first INFO to None
log.info("Started muxp Version: {}".format(muxp_VERSION))
runfile = argv[0]
if len(argv) > 1:
    muxpfile = argv[1]
else:
    muxpfile = None
main = muxpGUI(runfile, muxpfile)

