MUXP-SAMPLE-FILES
==================

This directory includes sample files you can use to test MUXP and update your X-Plane mesh.
All files work with the default X-Plane mesh. The file Aleu.muxp will also update the SpainUHD
in case this is installed in your Custom Scenery.

Note
-------
In case you have already nice meshes installed for the areas (e.g Ortho4XP or UHD meshes)
that already updated your mesh as required, you actually don’t need to run MUXP here. You
can however still run MUXP but then the updated default scenery would be shown (in case
activated in X-Plane) instead of your nice mesh. MUXP can also update your O4XP and UHD
meshes but the current files (except Aleu.muxp) are just written to update default meshes at the
moment.

The following files are working for DEFAULT X-PLANE AIRPORTS, so nothing you need to install:

airport_XK0038.muxp: Private airport next to Beaver Lake in the mid of US which in default
X-Plane is flattened in a way that the lake runs uphill. MUXP adapts the mesh to look like in
reality

TIN_for_airport_FHAW.muxp: Creating better mesh for the airport on a remote island in
Southern Atlantic Ocean

LFLJ.muxp: Courchevel now with slope, nothing more to say

airport_PAKT_v1.muxp: Creating elevation profile for Ketchikan airport - works with default airport and
also with Airport 1.0.1 of relicroy in X-Plane forum. Can adapt default dsf and Ortho4XP.
Also works with HD mesh but then you need to remove the line starting "source_dsf ..." from MUXP file
in order to select your HD mesh.

KCLL.muxp: This MUXP file demonstrates how network levels can be changed with MUXP. In
that case it was a missing bridge north of the Easterwood airport in Texas. Also the mesh
was adapted in order to lower the road passing under the bridge.

LTBU.muxp: Corlu airport in Turkey now with its long sloped runway



The following updates are created for SPECIFIC AIRPORT SCENERIES. It is highly
recommended to install also the according airports sceneries (follow links) to really make use
out of the mesh change. 

CA446.muxp: Private airport nicely situated on Stuart Island in BC Canada
https://forums.x-plane.org/index.php?/files/file/49891-stuart-island-airstrip-in-bc-yrr-ca-0446/

Aleu.muxp: Bush strip on a mountain ridge in the Pyrenees
https://forums.x-plane.org/index.php?/files/file/60984-aleu-altisurface-lf0921-at-french-pyrenees/ 
Works best together with SpainUHD mesh. You don’t need to follow the instructions
on this site for mesh updating, as this is now done by MUXP.

Channel Islands Mesh Update contains muxp files for 4 airports on the Channel Islands
in the Pacific close to Santa Barbara. Wookie1 created nice airports for them:
https://forums.x-plane.org/index.php?/files/file/61678-san-miguel-island-airstrip-california/
https://forums.x-plane.org/index.php?/files/file/61694-santa-rosa-island-airfield-california/   
https://forums.x-plane.org/index.php?/files/file/61786-christy-airstrip-ca97-california/   
https://forums.x-plane.org/index.php?/files/file/61841-santa-cruz-island-conservancy-airfield-california/

PNG_airport_GOR_v1_3.muxp is to be used together with the great PNG airfields available at
X-Plane forum: https://forums.x-plane.org/index.php?/files/file/67463-png-airfields-series-1/

The update for the Scandinavian Mountains Airport (ESKS) was created to work with the commercial
scenery of RUNAWAYBOT at simmarket. This is the first MUXP file making use of type smooth and double_cut as well
as the new cut_path command.
