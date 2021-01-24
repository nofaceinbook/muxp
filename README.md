# Mesh Updater X-Plane (MUXP)
![muxp overview](https://github.com/nofaceinbook/muxp/blob/master/doc/images/MUXP_LOGO.jpg)

This program allows to update the mesh files (.dsf-files) for X-Plane 11.
![muxp overview](https://github.com/nofaceinbook/muxp/blob/master/doc/images/MuxpBeforeAfterYYR.JPG)

As shown in this picture you can adapt the mesh e.g. to prepare the terrain for a new runway or even change the terrain like adding lakes.


## Highlights
* Option to **change the mesh and thus elevation** for the area e.g. for your airport and **share these changes with others** without the need to share complete dsf files which are large, might have copyright issues and change only your area (e.g. not if there are changes required for another airport.

* **Better flatten airports** only where needed (not a hughe area as done by the X-Plane flatten flag) or generate **runway profiles** exactly as they are.

* Define mesh updates directly within **World Editor X-Plane (WED)**.

* **See how the mesh really looks like** via .kml files that can e.g. be visualized and changed with Google Earth.

* Pyhsical mesh can be **exported/imported to/from .obj files to be worked on in Blender**.

* You can also change the terrain, the elevation of **raster squares** and **update the elevation layers for networks/roads** to e.g. generate bridges.


## Installation
Under Windows just [downlaod the executable](https://github.com/nofaceinbook/muxp/releases/latest/download/MUXP_Win64_EXE.zip) 
and unzip the folder with executalbe MUXP program in your X-Plane Custom Scenery Folder. Done.
For Mac/Linux you need to download the Python Source Code, install further needed libraries and run it with Python
on your computer. The [manual](https://github.com/nofaceinbook/muxp/releases/latest/download/MUXP-Manual.pdf) 
includes more information.


## Updating Your Mesh
Updating your Mesh is very simple. Under Windows just drop the MUXP File on muxp.exe using Windows File Explorer.
MUXP will then automatically update according X-Plane mesh files. 
Alternatively you can also run MUXP (via double click on muxp.exe or via Python for Mac/Linux) und  and then select the MUXP file from GUI. 
Use [MUXP-Sample-Files](https://github.com/nofaceinbook/muxp/releases/latest/download/Muxp-Sample-Files.zip) to get started.
The README file for these samples gives you more information about what changes are performed by each MUXP file.
MUXP is pre-configured to activate updated mesh in your scenery_packs.ini file so that after
start/re-start of X-Plane it becomes visible. You can also change this config and control scenery_packs.ini yourself.


## Manual / Own Mesh Updates
Much more details on MUXP are included in the [manual](https://github.com/nofaceinbook/muxp/releases/latest/download/MUXP-Manual.pdf).
Especially creation of your own mesh updates requires some learning but the manual includes examples to get you started.
There is also a [video](https://youtu.be/XXBA7OrakMo) by Pierre (thanks!) explaining the basics of MUXP in detail.


## WARNING - Alpha Status - Still under Development
This program is stil under development and still has some errors. Use it carefully. Everything you do  on your own risk.

Refer to the already [Known Issues](https://github.com/nofaceinbook/muxp/issues) and feel free to add ones that you might find.


## How does MUXP work
MUXP adapts the dsf-files of X-Plane that do include the mesh information (not the dsf files including overlays or e.g. 
airport buildings). For the adaption the scenery developer creates a MUXP file (yaml text file) including 
definitions for the mesh like flattening of a certain area. This MUXP file is submitted e.g. with other scenery files 
(e.g. new airport) to the user. The user installs scenery as normal. The MUXP file is then processed by this MUXP tool.
The tool is searching automatically for installed mesh files (such as Ortho, HD Mesh or even already adapted dsf files)
and the user can decide which one to be updated (however the MUXP file can itself specify which mesh shall be used, so. 
you might not be asked). 
Processed default dsf files are stored in the MUXP updated default mesh folder 
within Custom Scenery. Adapted custom meshes will stay in their Custom Scenery sub-folder and the original custom dsf
is saved as file with ending '.muxp.original". When X-Plane starts the adapted mesh will be shown (in case there is no 
other custom mesh with higher priority in scenery_packs.ini file or you did MUXP allow to activate the change
directly via updating scenery_packs.ini).

![Functioning Of Muxp](https://github.com/nofaceinbook/muxp/blob/master/doc/images/muxpFunciton.JPG)


