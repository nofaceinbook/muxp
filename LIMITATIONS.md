# Current Limitations of MUXP
The program ist in its early development and has thus currently several limitations.

* **Only operation on default mesh:** This version adapts just the default mesh of X Plane. Futrue versions will also detect if you have e.g. a Orhto or HD mesh installed and will adapt those.

* **No tool for generating muxp files:** In future it is planned that muxp offers function to e.g. generate a runway profil based on the airport defintion apt.dat or uses drawn kml polygons (e.g. with google earth or WED) to flatten an area. For the moment you have to edit these coordinates manually in the muxp-file.

* **No autmatic removal of flatten flag:** If you adapt e.g. the elevation of parts of an airport and the airport has in the apt.dat the flatten flag set you have to remove this line manually in order to see the changes. 

* **No tooled management of muxp files:** For the moment you have to disable/de-install muxp changes manually. Also to make several changes for one tile is currently not directly possible from muxp.

* **No automated zipping of updated dsf files:** The updated dsf files are not zipped automatically. Meaning that they will be larger than original files and consuming more space on your drive. However you can manually 7zip them in arhcives for them moment.

* **No executable yet:** As the current version is still bugy and changed frequently there is currently no executable. So you need to run python for testing it.
