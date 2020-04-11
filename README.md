# Mesh Updater X-Plane (MUXP)
This program allows to update the mesh files (.dsf-files) for X-Plane 11.
![muxp overview](https://github.com/nofaceinbook/muxp/blob/master/doc/images/MuxpBeforeAfterYYR.JPG)
As shonw in this picture you can adapt the mesh e.g. to prepare the terrain for a new runway.

## WARNING - Early Development Stage
This program is in an early development stage and still has some errors. For the moment only use it in case you know what you are doing. In any case you do everything on your own risk.

Refer [Limitations](https://github.com/nofaceinbook/muxp/blob/master/LIMITATIONS.md)  of that early version and the already [Known Issues](https://github.com/nofaceinbook/muxp/issues).

## Highlights

* Option to **change the mesh and thus elevation** for the area e.g. for your airport and **share these changes with others** without the need to share complete dsf files which are large, might have copyright issues and change only your area (e.g. not if there are changes required for another airport.

* **Better flatten airports** only where needed (not a hughe area as done by the X-Plane flatten flag)

* Generate **runway profiles** exactly as they are.

* You can also change the elevation of **raster squares**.

* **See how the mesh really looks like** via .kml files that can e.g. be visualized with Google Earth

* Also **update the elevation layers for networks/roads** to e.g. generate bridges.

## How does MUXP work

Muxp adapts the dsf-files of X-Plane that do include the mesh information (not the dsf files including overlays or e.g. airport buildings). For the adaption the scenery developer creates a muxp file (yaml text file) including defintions for the mesh like flattening of a certain area. This muxp file is submitted e.g. with other scenerey files (e.g. new airport) to the user. The user installs scenery as normal. The muxpf file is then processed by this muxp tool. The tool is searching automatically the correct dsf mesh file (for the moment just X-Plane default mesh, in future all other installed mesh files will be checked such as Ortho, HD Mesh or even already adapted dsf files). The processed dsf file is then stored in the muxp updated mesh folder within Custom Scenery. So when X-Plane starts the adapted mesh will be shown.

![Functioning Of Muxp](https://github.com/nofaceinbook/muxp/blob/master/doc/images/muxpFunciton.JPG)

**Important:** In order that the changes are visible in X-Plane the muxp folder in Custom Scenery has to have a priority over all other mesh dsf files in Custom Scenery. Refer to availible documentes and YouTube tutorials how to organize your *scenery_packs.ini* file in the right order, in case you have issues.


## Manual for Users

As a user of muxp you just need to install muxp. Until the executable will be published (when a more stable version is ready) you need a 64 bit version of python 3 on your computer. Copy all the *.py* files in a folder. In order to not required the manual unzipping of the packed dsf-files you will need also to install [pyzlma](https://github.com/fancycode/pylzma) which should be easy with *pip install pylzma*. Now you can run pyhton on *muxp.py*. 

When starting muxp the first time you need to set your X-Plane 11 folder and the muxp folder (there is a option to create a new folder called "zmuxp mesh updates" within your Custom Secenery folder. When you tick the option for generating .kml files, muxp will create .kml files where you can see the mesh changes e.g. within Google Earth.

Running muxp is just to select the muxp file including mehs changes. When no error has occured (which might for the current version still be the case) the updated dsf file is stored in the muxp folder and you can start X-Plane to see the changes.


## Manual for Scenery Developers

The developer needs to define the *.muxp* file. As these file are in yaml file format you could name the file also *.yaml* at the end and make use of editors supporting yaml files. In future I will set up a wiki including all details on the file structure and possible commands. For the moment I can just offer you to look at the [examples](https://github.com/nofaceinbook/muxp/tree/master/muxpfiles).


