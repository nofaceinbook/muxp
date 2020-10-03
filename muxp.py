# -*- coding: utf-8 -*-
# ******************************************************************************
#
# muxp.py
#        
muxp_VERSION = "0.2.8a exp"
# ---------------------------------------------------------
# Python Tool: Mesh Updater X-Plane (muxp)
#
# For more details refer to GitHub: https://github.com/nofaceinbook/betterflat
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

from logging import StreamHandler, FileHandler, getLogger, Formatter
from muxp_math import *
from muxp_area import *
from muxp_file import *
from muxp_KMLexport import *
from xplnedsf2 import *
from wed_conv import MUXP
from os import path, remove, mkdir, sep, replace, walk
from shutil import copy2

from tkinter import *
from tkinter.filedialog import askopenfilename, askdirectory
from sys import argv, exit
from glob import glob



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
    def __init__(self, rf, muxpfiles=[]):
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
        self.activatePack = 1 #set to 1/True if after writing of updated dsf file user is queried to directly activate pack in scenery_Packs.ini

        self.button_selected = None  # keeps track of selected button in GUI

        self.header = Label(self.window, text="WARNING - This is still a test version.")
        self.header.grid(row=0, column=0, columnspan=2)
        self.config_button = Button(self.window, text=' Config ', fg='black', command=lambda: self.ConfigMenu())
        self.config_button.grid(row=0, column=2, sticky=W, pady=4, padx=10)        
        self.help_button = Button(self.window, text=' Help ', fg='red', command=lambda: displayHelp(self.window))
        self.help_button.grid(row=0, column=3, sticky=W, pady=4, padx=10)

        self.muxpfile_label = Label(self.window, text="MUXP File:")
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
        self.muxp_create = Button(self.window, text='  Create muxp   ', command=lambda: self.create_muxp())
        self.muxp_create.grid(row=9, column=0, sticky=E, pady=4)
        self.muxp_undo = Button(self.window, text='  Undo muxp   ', state=DISABLED, command=lambda: self.undo_muxp())
        self.muxp_undo.grid(row=9, column=2, sticky=E, pady=4)        
        log.info("GUI is set up.")
        


        self.createConfig()  # creates a Config File if none is present
        error = self.getConfig()
        if error: #in case of config error, config has to be defined
            displayNote(self.window, "Configuration file 'muxp.config' not found (check muxp.log) or\nyou are starting muxp the first time.\n\n" +
                                     "When you start muxp the first time you need to set X-Plane folder and \na folder for the updated default dsf files.\n" +
                                     "This folder needs to be inside your 'Custom Scenery' folder of X-Plane.\nYou can also choose to generate a new folder\n"
                                     "like 'zzzz_muxp_default_mesh_updates'.\n" +
                                     "Very low priority in 'scenery_packs.ini' is sufficient, as it is only \nused for replacing default scenery.\n\n" +
                                     "IMPORTANT: This tool is in an early development stage.\n                       All you are doing, you do it at your own risk!")
            self.ConfigMenu()
        else:
            if muxpfiles != []: #if muxpfiles given
                for mf in muxpfiles:
                    self.select_muxpfile(self.muxpfile_entry, mf)
                    error = self.runMuxp(mf)  # directly run muxpfile if it was given as argument
                    if error: break ### TBD: Better have all errors on one list to show
            #else: #OPTION TO DIRECTLY RUN NEW MUXP-FILES IN DIRECTORY; MAY BE TOO MANY OPTIONS ....
            #    self.handle_new_muxp_files()  # in case of new muxpfiles directly process them
        if muxpfiles == [] or error: #program that was run directly, terminates directly in case of no errors
            mainloop()

    def handle_new_muxp_files(self):
        """
        Will show all new muxp files (newer than muxp.config) to be directly processed.
        WARNING: Function not finished and currently not used as these might be to many options for user
           ---> Probably to be removed
        """
        def process_new_muxes(box, mlist):
            ids = box.curselection()
            if len(ids) == 0:
                selected_muxes = range(len(mlist))
            else:
                selected_muxes = box.get(ids)
            ### PROCESS SELECTED IDs ####
            ### Set modification time to time of processed file (not process again)
            self.button_selected = "OK"

        ###### TBD: ONLY handle new MUXP-files if not forbidden by config #####################
        muxp_conf = self.runfile[:self.runfile.rfind('.')]+'.config'
        new_date = path.getmtime(muxp_conf)
        log.info("Searching new .muxp files in MUXP-folder: {}  (incl. subfolders)".format(self.muxpfolder))
        muxp_files = glob(self.muxpfolder + '/**/*.muxp', recursive=True)  # all files ending .muxp incl. sub-folders
        new_files = [f for f in muxp_files if path.getmtime(f) > new_date]
        muxp_list = []
        for f in new_files:
            fsep = f.replace(sep, "/")
            fshort = fsep[len(self.muxpfolder)+1:]  # +1 to get rid of separator
            muxp_list.append([fsep, path.getmtime(f), fshort])
        self.window.withdraw()  # hide main-window for this simple-processing
        self.button_selected = None   # set to empty, as this is variable needs value for window to be closed
        new_muxes_win = Toplevel(self.window)
        new_muxes_win.attributes("-topmost", True)
        topinfo = Label(new_muxes_win, text="New MUXP Files to be processed:")
        topinfo.grid(row=0, column=0)
        listbox = Listbox(new_muxes_win, selectmode = "multiple", width=80)
        listbox.grid(row=1, column=0, columnspan=3)
        for item in muxp_list:
            listbox.insert(END, item[2])
        buttoninfo = Label(new_muxes_win, text="Press OK to process these new muxp-files and update your mesh.\n"
                                               "You could also select just individual files to be processed.")
        buttoninfo.grid(row=2, column=0, columnspan=3)
        ok_button = Button(new_muxes_win, text='  OK  ', command=lambda: process_new_muxes(listbox, muxp_list))
        ok_button.grid(row=3, column=0)
        exit_button = Button(new_muxes_win, text='  EXIT  ', command=lambda: exit(0)) ### DOES NOT WORK --> FIRST CALL process_.. set button to "EXIT" and then exit at end of fucntion
        exit_button.grid(row=3, column=2)
        skip_button = Button(new_muxes_win, text='  skip for advanced processing  ', command=lambda: process_new_muxes(listbox, muxp_list))
        skip_button.grid(row=3, column=1)
        while self.button_selected == None: #wait until selection is done
            new_muxes_win.update()
        new_muxes_win.destroy()
        self.window.update()
        self.window.deiconify()  # show now up muxp main window, update required first
        self.button_selected = None






    def getConfig(self):
        """
        Gets configuration from muxp.config from same directory as runfile.
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
            head, tail = path.split(path.abspath(path.dirname(self.runfile)))
            while len(tail) > 0:
                if tail == "Custom Scenery" or path.exists(path.join(head, 'X-Plane.exe')):
                    self.xpfolder = head.replace(sep, '/')  # setting for all OS the correct separators in filename
                    log.info("Set X-Plane folder to: {}".format(self.xpfolder))
                    break
                head, tail = path.split(head)
            if len(tail) == 0:
                log.error("Not inside X-Plane folder as stated in config file. X-Plane Folder not set! Current folder is: {}".format(path.abspath(path.dirname(runfile))))
                self.xpfolder = ""
                return -3
        self.muxpfolder = c["muxpfolder"].strip()
        if self.muxpfolder.find("[THIS_FOLDER]") == 0: 
            self.muxpfolder = path.abspath(path.dirname(self.runfile))
            self.muxpfolder = self.muxpfolder.replace(sep, '/')  # setting for all OS the correct separators in filename
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
        ### Now check if optional values are in file and read values
        if "dsfSourcePack" in c: #This path is relative from xpfolder
            self.dsf_sceneryPack = c["dsfSourcePack"].strip()
            if self.dsf_sceneryPack != "[ACTIVE]" and not path.exists(self.xpfolder + "/" + c["dsfSourcePack"]):
                log.error("DSF Source Package {} given in config file does not exist. It is ignored!".format(self.dsf_sceneryPack))
                self.dsf_sceneryPack = ""
            else:
                log.info("Scenery Source Package set to: {}".format(self.dsf_sceneryPack))
        else:
            self.dsf_sceneryPack = ""
        if "conflictStrategy" in c:
            self.conflictStrategy = c["conflictStrategy"].strip()
            log.info("Conflict Strategy for multiple changes in same DSF file set to: {}".format(self.conflictStrategy))
        else:
            self.conflictStrategy = ""
        if "activatePack" in c:
            try:
                self.activatePack = int(c['activatePack'])
            except ValueError:
                log.error("activatePack is not of type int; value not updated")
            log.info("activatePack set to: {}".format(self.activatePack))
        else:
            self.activatePack = 0
        return 0 #no error


    def createConfig(self):
        """
        Would save a default MUXP config file in case no such file is present and
        MUXP is started from a directory under the XP 11 Custom Scenery Folder.
        Returns 0 if config exists, 1 if created, -1 if it cannot be created.
        """
        filename = self.runfile[:self.runfile.rfind('.')] + '.config'
        if path.isfile((filename)):
            log.info("MUXP Configuration file: {} exits.".format(filename))
            return 0

        head, tail = path.split(path.abspath(path.dirname(self.runfile)))
        while len(tail) > 0:
            if tail == "Custom Scenery" or path.exists(path.join(head, 'X-Plane.exe')):
                self.xpfolder = head.replace(sep, '/')  # setting for all OS the correct separators in filename
                self.muxpfolder = path.abspath(path.dirname(self.runfile))
                self.muxpfolder = self.muxpfolder.replace(sep, '/')  # setting for all OS the correct folder separators
                log.info("Set X-Plane folder to: {}".format(self.xpfolder))
                log.info("Set MUXP-Folder to: {}".format(self.muxpfolder))
                self.safeConfig(self.xpfolder, self.muxpfolder, 0, 1, "", "ORIGINAL")
                return 1
            head, tail = path.split(head)
            if len(tail) == 0:
                log.info("Not inside X-Plane folder so MUXP Config has to be created manually.")
                return -1

        
    def showProgress(self, percentage):
        if self.current_action == 'read':
            self.muxp_status_label.config(text="read dsf-file ({} percent)".format(percentage))
        elif self.current_action == 'write':
            self.muxp_status_label.config(text="write updated dsf-file ({} percent)".format(percentage))
        self.window.update()

    def select_muxpfile(self, entry, filename=None):
        # if file is set it is directly displayed
        if filename is None:
            filename = askopenfilename(filetypes=[("MUXP files", ".muxp"), ("kml files", "muxp.kml"),
                                                  ("YAML files", "muxp.yaml"), ("all files", "*")])
            if not filename:
                return

        entry.delete(0, END)
        entry.insert(0, filename)
        self.muxp_start.config(state="normal")
        self.muxp_status_label.config(text="   this can take some minutes....")
        self.info_label.config(text="")


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
            copy2(inifile, inicopy)
            log.info("BASE-Backup of current scenery_packs.ini saved to: {}".format(inicopy))
        copy2(inifile, inibackup) #In each activation make a backup
        log.info("Backup of current scenery_packs.ini saved to: {}".format(inibackup))
        with open(inifile, encoding="utf8", errors="ignore") as f:
            pack_activated = False
            for line in f:
                if line.startswith("SCENERY_PACK"):
                    scenery = line[line.find(" ")+1:]
                    if scenery == pack+'/\n':  # '/\n' always in .ini at end of folder
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
                new_infile.append("SCENERY_PACK {}/\n".format(pack))  # '/' required in ini to be a correct path
                log.info("Added new scenery pack for at end of scenery_packs.ini.")
        with open(inifile, "w", encoding="utf8", errors="ignore") as f:
            for line in new_infile:
                f.write(line)
        return 0  # no error

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
        self.getConfig()  # always read config from file first to not overwrite settings that changed while processing
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
        and waits until user has selected one scenery in listbox.
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

        self.dsf_sceneryPack = ""   # set to empty, as this is variable needs value for window to be closed
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
        for i, f in enumerate(filenames): ### TBD: Define all file extensions AND directory names globally
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

        if issues[0] == "None":
            # in case of no issues of current file nothing to do, just stay with current file to be updated
            self.conflictStrategy = "CURRENT"
            return filename
        if issues[2] == "None" and len(getMUXPdefs(props[0])) == 1 and updateAlreadyInProps(update['id'], props[0]):
            ########## TBD: check that version to be installed is not older than current !!!! ###################
            # in case of no issues with original and the current file only includes the update, it can be overwritten
            self.conflictStrategy = "ORIGINAL"
            return filenames[2]
        if issues[1] == "None":
            # in case that backup-file has no issues, then just update this one
            # disadvantage when using backup-file is that, the current file will not be back-upped
            #   --> backup stays in order to be able to test again and again new updates starting always from backup
            self.conflictStrategy = "BACKUP"
            return filenames[1]

        conflictwin = Toplevel(self.window)
        conflictwin.attributes("-topmost", True)
        topinfo = Label(conflictwin, anchor='w', justify=LEFT, text="The DSF file you want to update was already updated in a way that may conflict witht current update.\n"
                                                  "You should think of applying the update to un-muxed dsf file. How do you want to proceed?\n Update details  " +
                                                  "id: " + update["id"] + "  version: " + update["version"] + "  area: {} ".format(update["area"]))
        topinfo.grid(row=0, column=0, columnspan=3)
        scenerylabel = [None, None, None]
        scenerybutton = [None, None, None]
        Label(conflictwin, text="================================================================================").grid(column=0, row=1, columnspan=3)
        dsftype_def = ["CURRENT", "BACKUP", "ORIGINAL"]
        for i, dsftype in enumerate(dsftype_def):
            scenerylabel[i] = Label(conflictwin, anchor='w', justify=LEFT, text=dsftype+" DSF FILE:\n   filename: "+filenames[i]+"\n   issue: " + issues[i] + "\n   Included mesh updates:\n" + muxes[i])
            scenerylabel[i].grid(row=2*i+2, column=0, columnspan=2)
            if i == 0:
                scenerybutton[0] = Button(conflictwin, text=' Update ', command=lambda: done(dsftype_def[0]))
            elif i == 1:
                scenerybutton[1] = Button(conflictwin, text=' Update ', command=lambda: done(dsftype_def[1]))
            elif i == 2:
                scenerybutton[2] = Button(conflictwin, text=' Update ', command=lambda: done(dsftype_def[2]))
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
                                             "Note: ORIGINAL DSF FILE will never be overwritten, but current is OVERWRITTEN with new version.\n"
                                             "WARNING: When selecting ORIGINAL DSF FILE all previous mesh updates in CURRENT DSF FILE  will be lost and would need to be applied again!")
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

    def warn_window(self, message, b1="OK", b2="CANCEL"):
        def set_button_selected(value):
            self.button_selected = value
        warn_win = Toplevel(self.window)
        warn_win.attributes("-topmost", True)
        warn_label = Label(warn_win, text=message)
        warn_label.grid(row=0, column=0, columnspan=2)
        b1_button = Button(warn_win, text='  {}  '.format(b1), command=lambda: set_button_selected(b1))
        b1_button.grid(row=2, column=0, pady=4)
        b2_button = Button(warn_win, text='  {}  '.format(b2), command=lambda: set_button_selected(b2))
        b2_button.grid(row=2, column=1, pady=4)
        while self.button_selected is None:
            warn_win.update()
        warn_win.destroy()
        result = (self.button_selected + '.')[:-1]  # create new string, not just copy reference
        self.button_selected = None
        return result

    def create_muxp(self):
        def select_file(entry): #if file is set it is directly displayed
            file = askopenfilename()
            entry.delete(0, END)
            entry.insert(0, file)
        def process_file(action, source, destination, info_field):
            info_field.config(state=NORMAL)
            result, error = None, None
            info_field.insert(END, "\nStarting {} for file {} ...\n".format(action, source))
            if not path.isfile(source):
                info_field.insert(END, "  ERROR: File does not exist!\n")
                info_field.config(state=DISABLED)
                info_field.yview(END)
                return
            if action == "INJECT IN WED":
                if not path.isfile(destination):  # special case where destination needs present for injection
                    error = "WED file: {} does not exist for injecting MUXP file.".format(destination)
                else:
                    muxp = MUXP(source)
                    result = muxp.wed_inject(destination)
                    if not result:
                        error = "Injection of MUXP into WED did not work."
            elif action == "CONVERT WED TO MUXP":
                muxp = MUXP()
                result = muxp.wed2muxp(source)
                if not result:
                    error = "Conversion from WED to MUXP did not work."
            elif action == "CONVERT MUXP TO KML":
                result, destination = muxp2kml(source, LogName)
                if not result:
                    error = destination  # in case muxp2kml has error, the error is within second argument
            elif action == "CONVERT KML TO MUXP":
                result, destination = kml2muxp(source)
                if not result:
                    error = destination  # in case kml2muxp has error, the error is within second argument
            elif action == "CREATE MUXP FROM APT":
                # destination includes list with ICAO code and mesh_type
                result, destination = apt2muxp(source, self.muxpfolder, LogName, destination[0], destination[1])
                if not result:
                    error = destination  # in case apt2muxp has error, the error is within second argument

            if error:
                info_field.insert(END, "  ERROR: {}\n".format(error))
                info_field.config(state=DISABLED)
                info_field.yview(END)
                return
            if path.isfile(destination):
                info_field.insert(END, "  WARNING: Destination file {} already exists.\n".format(destination))
                bak_file = destination + ".bak"
                if path.isfile(bak_file):
                    info_field.insert(END, "  WARNING: Backup file {} also exists.\n".format(bak_file))
                    #choice = warn_overwrite(bak_file)
                    choice = self.warn_window("WARNING: Backupfile {} already exists!\nWhen you would like to keep it select CANCEL and rename it first.".format(bak_file), "OVERWRITE", "CANCEL")
                    if choice == "CANCEL":
                        info_field.insert(END, "  Canceled current action!\n")
                        info_field.config(state=DISABLED)
                        info_field.yview(END)
                        return
                    info_field.insert(END, "  Overwriting backup file\n")
                replace(destination, bak_file)
                info_field.insert(END, "     --> Created backup to file: {}\n".format(bak_file))
            with open(destination, 'w', errors="ignore") as f:
                f.write(result)
            info_field.insert(END, "  Finished successful writing: {}\n".format(destination))
            info_field.config(state=DISABLED)
            info_field.yview(END)

        create_win = Toplevel(self.window)
        top_create_label = Label(create_win, anchor=W, justify=LEFT, text="SUPPORTS CREATION OF  M U X P  FILES", font=('Arial',12,'bold')).grid(row=0, column=1, columnspan=2, pady=10, padx=10)
        section_apt_label = Label(create_win, anchor=E, justify=LEFT, text="Create MUXP file based on airport definition in apt.dat file", font=('Arial',10,'bold')).grid(row=1, column=0, columnspan=3, pady=10, padx=10)
        aptdat_label = Label(create_win, text="ICAO in apt.dat: ")
        aptdat_label.grid(row=2, column=0, pady=4, sticky=E)
        icao_entry = Entry(create_win, width=8)
        icao_entry.grid(row=2, column=1, columnspan=2, sticky=W)
        create_mesh_type = StringVar()
        radio_TIN = Radiobutton(create_win, text="TIN", variable=create_mesh_type, value="TIN")
        radio_TIN.grid(row=2, column=2, sticky=W)
        radio_flatten = Radiobutton(create_win, text="flatten", variable=create_mesh_type, value="flatten")
        radio_flatten.grid(row=2, column=3, sticky=W)
        radio_TIN.select()
        aptfile_label = Label(create_win, text="apt.dat file:")
        aptfile_label.grid(row=3, column=0, pady=4, sticky=E)
        aptfile_entry = Entry(create_win, width=70)
        aptfile_entry.grid(row=3, column=1, columnspan=3, sticky=W)
        aptfile_entry.insert(0, self.xpfolder+"/Custom Scenery/Global Airports/Earth Nav data/apt.dat")
        aptfile_select = Button(create_win, text='Select', command=lambda: select_file(aptfile_entry))
        aptfile_select.grid(row=3, column=4, sticky=W, pady=4, padx=10)
        create_muxp_button = Button(create_win, text='  CREATE MUXP  ', command=lambda: process_file("CREATE MUXP FROM APT", aptfile_entry.get(), [icao_entry.get(), create_mesh_type.get()], info_text))
        create_muxp_button.grid(row=4, column=1, pady=4)
        section_devider_1 = Label(create_win, text="                                                                                                                        ", font=('Arial',12,'bold','underline')).grid(row=5, column=0, columnspan=4)
        section_apt_label = Label(create_win, anchor=E, justify=LEFT, text="Convert MUXP to kml file for further editing and back to MUXP",font=('Arial', 10, 'bold')).grid(row=6, column=0, columnspan=3, pady=10, padx=10)
        muxp2kml_file_label = Label(create_win, text="muxp or kml file:")
        muxp2kml_file_label.grid(row=7, column=0, pady=4, sticky=E)
        muxp2kml_file_entry = Entry(create_win, width=70)
        muxp2kml_file_entry.grid(row=7, column=1, columnspan=3, sticky=W)
        muxp2kml_file_select = Button(create_win, text='Select', command=lambda: select_file(muxp2kml_file_entry))
        muxp2kml_file_select.grid(row=7, column=4, sticky=W, pady=4, padx=10)
        convert2kml_button = Button(create_win, text='  MUXP TO KML  ', command=lambda: process_file("CONVERT MUXP TO KML", muxp2kml_file_entry.get(), None, info_text))
        convert2kml_button.grid(row=8, column=1, pady=4)
        convert2muxp_button = Button(create_win, text='  KML TO MUXP  ', command=lambda: process_file("CONVERT KML TO MUXP", muxp2kml_file_entry.get(), None, info_text))
        convert2muxp_button.grid(row=8, column=2, pady=4)

        section_devider_2 = Label(create_win, text="                                                                                                                        ", font=('Arial',12,'bold','underline')).grid(row=9, column=0, columnspan=4)
        section_wed_label = Label(create_win, anchor=E, justify=LEFT, text="Conversion Between MUXP and WED Files                      ",font=('Arial', 10, 'bold')).grid(row=10, column=0, columnspan=3, pady=10, padx=10)
        muxp2wed_file_label = Label(create_win, text="muxp file:")
        muxp2wed_file_label.grid(row=11, column=0, pady=4, sticky=E)
        muxp2wed_file_entry = Entry(create_win, width=70)
        muxp2wed_file_entry.grid(row=11, column=1, columnspan=3, sticky=W)
        muxp2wed_file_select = Button(create_win, text='Select', command=lambda: select_file(muxp2wed_file_entry))
        muxp2wed_file_select.grid(row=11, column=4, sticky=W, pady=4, padx=10)
        wed_file_label = Label(create_win, text="wed file:")
        wed_file_label.grid(row=12, column=0, pady=4, sticky=E)
        wed_file_entry = Entry(create_win, width=70)
        wed_file_entry.grid(row=12, column=1, columnspan=3, sticky=W)
        wed_file_select = Button(create_win, text='Select', command=lambda: select_file(wed_file_entry))
        wed_file_select.grid(row=12, column=4, sticky=W, pady=4, padx=10)
        muxp2wed_button = Button(create_win, text='  INJECT MUXP IN WED  ', command=lambda: process_file("INJECT IN WED", muxp2wed_file_entry.get(), wed_file_entry.get(), info_text))
        muxp2wed_button.grid(row=14, column=1, pady=4)
        wed2muxp_button = Button(create_win, text='  CONVERT WED TO MUXP  ', command=lambda: process_file("CONVERT WED TO MUXP", wed_file_entry.get(), muxp2wed_file_entry.get(), info_text))
        wed2muxp_button.grid(row=14, column=2, pady=4)
        info_text = Text(create_win,  height=4, state=DISABLED)
        info_text.grid(row=15, column=0, columnspan=5, padx=4, pady=6)
        scrollbar = Scrollbar(create_win, command=info_text.yview)
        scrollbar.grid(row=15, column=5, sticky='nsew')


    def runMuxp(self, filename):
        """
        Initiates updating the mesh based on the muxp file (filename).
        """
        ########## GUI SETTINGS AFTER / DURING RUN ################
        self.muxpfile_select.config(state="disabled")  # disable select option while running
        self.muxp_start.config(state="disabled")  # also disable a start while running
        self.config_button.config(state="disabled")
        def showRunResult(status, info, err=False):  # shows results/errors and re-sets GUI after run
            self.muxp_status_label.config(text=status)
            self.info_label.config(text=info)
            self.muxpfile_select.config(state="normal")
            self.config_button.config(state="normal")
            if err:
                log.error(status + " // " + info)
            else:
                log.info(status + " // " + info)
            self.getConfig()  # re-set all config variables based on config.file for next run


        ##### IN CASE CONVERSION FROM KML/WED TO MUXP NEEDED ########
        if filename.rfind(".wed.xml") == len(filename) - 8 or filename.rfind(".kml") == len(filename) - 4:
            log.info("Converting file: {} to muxp-file.".format(filename))
            if filename.rfind(".wed.xml") == len(filename) - 8:
                muxp = MUXP()
                result = muxp.wed2muxp(filename)
            else:  # muxp-file given
                result, error = kml2muxp(filename)
            if not result:
                showRunResult("Conversion ERROR", error, True)
                return -35
            filename += "_temporary_conversion_file.muxp"
            with open(filename, 'w', errors="ignore") as f:
                f.write(result)
            log.info("Finished conversion. Processing now: {}".format(filename))

        ############# READ AND EVALUATE MUXP FILE #####################
        update, error = readMuxpFile(filename, LogName)
        if filename.rfind("_temporary_conversion_file.muxp") > 0:
            log.info("FOLLOWING TEMPORARY MUXP FILE WAS READ: {}\n".format(update))
            remove(filename)  # remove temporary conversion file created above
            log.info("Temporary muxp file: {} removed.".format(filename))
        if update == None:
            showRunResult("muxp-file ERROR", "MUXP-file {} not found.".format(filename), True)
            return -1
        error, resultinfo = validate_muxp(update, LogName) 
        log.info("Command Dictionary: {}".format(update))
        if error: #positive values mean that processing can still be performed
            displayNote(self.window, resultinfo + "\nCheck muxp.log for details.")
        if error < 0: #In case of real erros, processing Muxp has to be stopped
            showRunResult("muxp-file validation ERROR", "Validation Error Code {}. Refer muxp.log for details.".format(error), True)
            return -2
        update["filename"] = filename  # needed for commands based on files
        log.info("muxpfile {} with id: {} version: {} for area:{} with {} commands read.".format(update["filename"], update["id"], update["version"], update["area"], len(update["commands"])))
        
        ############### SEARCH AND READ DSF FILE TO ADAPT ######################
        scenery_packs = None  # dictionary of scenery packs for according tiles
        log.info("source_dsf in muxp-file: {}".format(update["source_dsf"]))
        if update["source_dsf"].find("DEFAULT") == 0:  # skip searches when DEFAULT mesh is first preferred in MUXP file
            self.dsf_sceneryPack = "Global Scenery/X-Plane 11 Global Scenery"  #### TBD: Define this string globally!!!
            log.info("MUXP file asks to use DEFAULT scenery, so updating: {}".format(self.dsf_sceneryPack))

        if len(self.dsf_sceneryPack) == 0:  # no scenery pack yet defined (e.g. via config file)
            self.muxp_status_label.config(text="Searching available meshes for {}. Please WAIT ...".format(update["tile"]))
            self.muxp_start.config(state="disabled")
            self.window.update()
            scenery_packs = findDSFmeshFiles(update["tile"], self.xpfolder, LogName)
            preferred_pack = find_preferred_pack(update["source_dsf"], scenery_packs)
            if not preferred_pack:
                log.info("None of the preferred packs: {}  in muxp-file found.".format(update["source_dsf"]))
                self.SelectDSF(scenery_packs)  # will set selected pack to self.dsf_sceneryPack
            else:
                log.info("Following preferred scenery pack of muxp-file found to be updated: {}".format(preferred_pack))
                self.dsf_sceneryPack = preferred_pack
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
            showRunResult("Nothing updated!", "CANCEL was chosen in conflict handling.")
            return 1
        log.info("Conflict Strategy {} resulting in following dsf file to adapt: {}".format(self.conflictStrategy, dsf_filename))
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
            if muxp_process_error == 99:  # special command for exiting without update
                showRunResult("Muxp file includes exit command.", "No update saved!", False)
            elif muxp_process_error == -10:
                showRunResult(".obj file for insertion not found", "Mesh not inserted!", True)
            elif muxp_process_error == -11:
                showRunResult("Error loading .obj file!", "Mesh not inserted (refer log for details)", True)
            else:
                showRunResult("Error {} while updating mesh".format(muxp_process_error), "No update saved!", True)
            return muxp_process_error #No writing of dsf file in case of error

        ########## UPDATE PROPERTIES OF DSF ACCORDING TO PROCESSED MUXP FILE #############
        #currentDSFisUNMUXED = False
        if "muxp/HashDSFbaseFile" not in self.dsf.Properties: #store the file hash of the base dsf file 
            self.dsf.Properties["muxp/HashDSFbaseFile"] = str(self.dsf.FileHash)
            #### OPTION: write hex-presentation instead binary string to dsf with binascii.b2a_hex ###
            #currentDSFisUNMUXED = True
        update_number = 0 
        for props in self.dsf.Properties:  # check for already included updates in dsf and find highest number
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
        if path.exists(dsf_output_filename) and self.conflictStrategy != "BACKUP":
            # only make backup if existing dsf-file will be overwritten and not if the backup-file is the source
            #   in that case, the backup-file should be kept in order to be able to test the latest update again
            #   and again without starting from scratch. HOWEVER: a previous current file will be LOST
            copy2(dsf_output_filename, dsf_output_filename+".muxp.backup")
        
        ############## CHECK WRITE LOCATION AND WRITE UPDATED DSF FILE ##################
        if dsf_filename.find("X-Plane 11 Global Scenery") >= 0: #X-Plane default scenery selected, so file need to be written to muxp Folder
            #Check that all required folders for writing updated dsf to muxp folder do exist and create if missing
            if not path.exists(self.muxpfolder):
                showRunResult("muxp-folder ERROR", "muxpfolder {} not existing".format(self.muxpfolder), True)
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
        self.dsf.write(dsf_output_filename)
        
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
                selection = self.warn_window("The scenery package {}\n".format(newSceneryPack) +
                                 "is currently not activated in scenery_packs.ini\n" +
                                 "In order to see the changes by MUXP this ini-file needs\n" +
                                 "to be updated by placing the package in the ini-file\n" +
                                 "before: {}\n\n".format(before_packs) +
                                 "By pressing OK MUXP will activate the update for you,\n" +
                                 "by pressing CANCEL you have to activate on your own.\n\n")

                if selection == "OK":
                    log.info("Updateing scenery_packs.ini and inserting new pack {} before {} in order that this scenery will be activated in X-Plane".format(newSceneryPack, before_packs))
                    self.activateSceneryPack(newSceneryPack, before_packs)
                else:
                    log.info("Decsion to update scenery_packs.ini manually.")

        showRunResult("Finished Mesh Update {} successful".format(path.basename(filename)), "Scenery Pack {} adapted.".format(self.dsf_sceneryPack))
        return 0 #processed muxp without error    
        
    def processMuxp(self, filename, update):
        """
        Adapts the self.dsf according the muxp commands stored in update dict.
        """
        #log.info("Loading dsf file {}".format(filename))
        #self.current_action = "read"
        #self.dsf.read(filename)
        a = muxpArea(self.dsf, LogName)
        log.info("Area to be extracted: {}".format(update["area"]))
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
                if c["elevation"] is not None:
                    ##### currently elevation_scale not adapted here, so if not changed by other commands will be full meter here #####
                    log.info("Updating elevation to: {} in polygon: {}".format(c["elevation"], c["coordinates"]))
                    for t in a.atrias: #go through all trias in area
                        for i, p in enumerate(t[0:3]): #all their points
                            if PointInPoly(p[0:2], c["coordinates"]):
                                log.info("For tria memory id {}: with coords: {} set elevation from: {}  to: {}".format(hex(id(t[i])), t[i][0:2], t[i][2],  c["elevation"]))
                                t[i][2] = c["elevation"]
                elif "3d_coordinates" in c:
                    ramp_tria = c["3d_coordinates"]  # 3 first 3d-coordinates build the tria for ramp inclination
                    ramp_tria[0][0], ramp_tria[0][1] = ramp_tria[0][1], ramp_tria[0][0]  # 3d coords currently
                    ramp_tria[1][0], ramp_tria[1][1] = ramp_tria[1][1], ramp_tria[1][0]  # NOT SWAPPED
                    ramp_tria[2][0], ramp_tria[2][1] = ramp_tria[2][1], ramp_tria[2][0]  # TBD
                    log.info("Following Tria is used for setting elevation: {}".format(ramp_tria))
                    for nt, t in enumerate(a.atrias):
                        for v in range(3):
                            if PointInPoly(t[v][0:2], c["coordinates"]):  # adapt all vertices inside polygon
                                l0, l1 = PointLocationInTria(t[v][:2], ramp_tria)
                                t[v][2] = ramp_tria[2][2] + l0 * (ramp_tria[0][2] - ramp_tria[2][2]) + l1 * (
                                            ramp_tria[1][2] - ramp_tria[2][2])
                                log.info(
                                    "Vertex no. {} of tria no. {} at {} set to elevation {} with l0={} and l1={}".format(
                                        v, nt, t[v][:2], t[v][2], l0, l1))
                    elevation_scale = 0.05  # allows 5cm elevation steps  #### TBD: Make this value configurable in command
                else:
                    log.warning("Command {} does neither have value to set elevation nor 3d_coordinates for elevation by triangle. So nothing changed".format(c["command"]))
                if self.kmlExport:
                    kmlExport2(self.dsf, [c["coordinates"]], a.atrias, kml_filename + "_{}".format(c_index+1))

            if c["command"] == "extract_mesh_to_file":
                head, tail = path.split(update["filename"])
                if c["name"] == "":
                    obj_filename = path.join(head, "muxp_mesh.obj")
                    log.info("extract mesh command has no name attribute; using default name: {}".format(obj_filename))
                else:
                    obj_filename = path.join(head, c["name"])
                log.info("Extract mesh in polygon: {} to file {}".format(c["coordinates"], obj_filename))
                file_info = "# X-Plane Mesh Extract by MUXP (version: {})\n".format(muxp_VERSION)
                file_info += "# from scenery pack: {}\n".format(self.dsf_sceneryPack)
                file_info += "# dsf file hash: {}\n".format(self.dsf.FileHash)
                a.extractMeshToObjFile(c["coordinates"], obj_filename, file_info)
                if self.kmlExport:
                    kmlExport2(self.dsf, [c["coordinates"]], a.atrias, kml_filename + "_{}".format(c_index + 1))

            if c["command"] == "insert_mesh_from_file":
                head, tail = path.split(update["filename"])
                if c["name"] == "":
                    obj_filename = path.join(head, "muxp_mesh.obj")
                    log.info("insert mesh command has no name attribute; using default name: {}".format(obj_filename))
                else:
                    obj_filename = path.join(head, c["name"])
                if not path.isfile(obj_filename):  # Error that insertion file not existent
                    return -10
                borderlandpoly = a.insertMeshFromObjFile(obj_filename, c["coordinates"], c["terrain"])
                if len(borderlandpoly) == 0:  # Error occurred when inserting
                    return -11
                elevation_scale = 0.05  # allows 5cm elevation steps   #### TBD: Make this value configurable in command #########
                if self.kmlExport:
                    kmlExport2(self.dsf, [c["coordinates"], borderlandpoly], a.atrias, kml_filename + "_{}".format(c_index + 1))
            
            if c["command"] == "update_network_levels":
                ###### tbd: put details below to separate file like mux.area.py #################
                ###### tbd: support creation of road segments incl. insertion of addtional vertices #################
                log.info("Updating network elevation in polygon: {}".format(c["coordinates"]))
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

            if c["command"] == "cut_ramp":
                ###### tbd: support further values like terrain and accuracy ####################
                elev_placeholder = 333333  # first set this elevation to all cut vertices and then replace by ramp
                polysouter, polysinner, borderv = a.CutPoly(c["coordinates"], elev_placeholder)
                ramp_tria = c["3d_coordinates"]  # 3 first 3d-coordinates build the tria for ramp inclination
                ramp_tria[0][0], ramp_tria[0][1] = ramp_tria[0][1], ramp_tria[0][0]  # 3d coords currently
                ramp_tria[1][0], ramp_tria[1][1] = ramp_tria[1][1], ramp_tria[1][0]  # NOT SWAPPED
                ramp_tria[2][0], ramp_tria[2][1] = ramp_tria[2][1], ramp_tria[2][0]  # TBD
                log.info("Following Tria is used for ramp elevation: {}".format(ramp_tria))
                for nt, t in enumerate(a.atrias):
                    for v in range(3):
                        if t[v][2] == elev_placeholder:  # adapt all marked vertices with elev. from position on ramp
                            l0, l1 = PointLocationInTria(t[v][:2], ramp_tria)
                            t[v][2] = ramp_tria[2][2] + l0 * (ramp_tria[0][2] - ramp_tria[2][2]) + l1 * (ramp_tria[1][2] - ramp_tria[2][2])
                            log.info("Vertex no. {} of tria no. {} at {} set to ramp-elevation {} with l0={} and l1={}".format(v, nt, t[v][:2], t[v][2], l0, l1))
                elevation_scale = 0.05  # allows 5cm elevation steps  #### TBD: Make this value configurable in command
                shown_polys = polysouter
                for pol in shown_polys:
                    pol.append(pol[0])  # polys are returned without last vertex beeing same as first
                shown_polys.append(c["coordinates"])
                if self.kmlExport:
                    kmlExport2(self.dsf, shown_polys, a.atrias, kml_filename + "_{}".format(c_index+1))

            if c["command"] == "cut_flat_terrain_in_mesh":
                polysouter, polysinner, borderv = a.CutPoly(c["coordinates"], None, False) #False for not keeping inner trias; None for elevation as only new terrain should get elevation
                ########### TBD: CutPoly should not change elevation, so it would not needed to give parameter None !!! ############
                borderv, log_info = sortPointsAlongPoly(borderv, c["coordinates"]) # NEW 16.08.20
                log.info("Logs from sorting Points along Poly: {}\n".format(log_info))
                borderv.append(borderv[0])  # make it a closed poly
                for v in borderv:
                    log.info("Border Vertex after Cut: {}".format(v))
                a.createPolyTerrain(borderv, c["terrain"], c["elevation"])  # NEW 16.08. was c["coordinates"] instead borderv
                ### NEW 16.08.20 Following 2 lines not used, as mesh should already be split by cut above
                #for vertex in borderv: #insert in mesh for poly also vertices from surrounding mesh on the border
                #    a.splitCloseEdges(vertex)
                ### NOTE: even if only elevation for terrain is set, the new changed trias will create different looking terrain also outside terrain mesh
                for vertex in a.getAllVerticesForCoords(borderv): #set borderv to correct elevation
                    vertex[2] = c["elevation"]
                shown_polys = polysouter
                for pol in shown_polys:
                    pol.append(pol[0])  #polys are returned without last vertex beeing same as first
                shown_polys.append(c["coordinates"]) 
                if self.kmlExport:
                    kmlExport2(self.dsf, shown_polys, a.atrias, kml_filename + "_{}".format(c_index+1))
                    
            if c["command"] == "cut_spline_segment":
                log.info("Cutting segment as spline for the following elevation profile: {} m".format(c["3d_coordinates"]))
                segment_bound = segmentToBox(c["3d_coordinates"][0], c["3d_coordinates"][-1], c["width"])  # box around first and last vertex with width
                log.info("Box around runway is: {}".format(segment_bound))
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

            if c["command"] == "exit_without_update":
                return 99

            if c["command"] == "unflatten_default_apt":
                log.info("Default Airport with ICAO: {} shall not be flattened.".format(c["name"]))
                apt_default_file = path.join(self.xpfolder, "Custom Scenery", "Global Airports", "Earth nav data", "apt.dat")
                log.info("Checking for flattening flag in default airport definition file: {}".format(apt_default_file))
                if not path.isfile(apt_default_file):
                    log.error("Default apt.dat not found. No unflatting performed!")
                else:
                    code, new_aptdat = unflatten_apt(apt_default_file, c["name"], LogName)
                    if code < 0:
                        log.error("Processing Error in default apt.dat: {}".format(new_aptdat))
                    elif code == 0:
                        log.info("No flattening flag set, nothing changed")
                    elif code == 1:
                        log.info("TBD Flattening default apt.dat")
                        warn_message =  "The airport: {} that should by changed by MUXP\n".format(c["name"])
                        warn_message += "is set to flatten in the default apt.dat file:\n"
                        warn_message += "{}\n\n".format(apt_default_file)
                        warn_message += "In order to make changes by MUXP visible, MUXP\n"
                        warn_message += "will set the flatten flag in this file to a\n"
                        warn_message += "comment line: # 1302 flatten 1  # removed flattening by MUXP\n\n"
                        if not path.isfile(apt_default_file+".beforeMUXP"):  # check if BackupFile exists
                            warn_message += "As this is the first change by MUXP, MUXP will also create\n"
                            warn_message += "a backup file called apt.dat.beforeMUXP in the apt.dat directory."
                        selection = self.warn_window(warn_message)
                        if selection == "OK":
                            if not path.isfile(apt_default_file + ".beforeMUXP"):  # check if BackupFile exists
                                copy2(apt_default_file, apt_default_file + ".beforeMUXP")
                            with open(apt_default_file, 'w', errors="ignore") as f:
                                f.write(new_aptdat)


        log.info("DSF vertices will be created with scaling: {}".format(elevation_scale))
        self.muxp_status_label.config(text="Creating new vertices and\n   insert mesh update in dsf file")
        self.window.update()
        a.validate_mesh()
        a.createDSFVertices(elevation_scale)
        a.insertMeshArea()



########### MAIN #############
log = defineLog('muxp', 'INFO', 'INFO')  # no log on console for EXE version --> set first INFO to None
log.info("Started muxp Version: {}".format(muxp_VERSION))

muxpfiles = []
for i in range(len(argv)):
    f = argv[i].replace(sep, '/')   # setting for all OS the correct separators in filename
    if path.isfile(f):
        muxpfiles.append(f)
    if path.isdir(f):  # in case of directories include all files in it (not going down to sub-directories)
        for (_, _, filenames) in walk(f):
            filenames = [f + '/' + fn for fn in filenames]  # write directory befor filename to get full path
            muxpfiles.extend(filenames)
            break

log.info("MUXP runfile: {} \n   processing following files: {}".format(muxpfiles[0], muxpfiles[1:]))
main = muxpGUI(muxpfiles[0], muxpfiles[1:])  # first element in muxpfiles is argv[0], the runfile

