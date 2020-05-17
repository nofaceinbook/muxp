
filename = "insert filename"

muxp = [] #will at the end contain the muxp file data
area_lon = []
area_lat = []
elev_3d = None #used to store elevation of 3d coordiontes coming before coordinates
context = None #current context we are in kml file

with open(filename, encoding="utf8", errors="ignore") as f:
    for line in f:
        if line.find('<Document>') >= 0:
            context = "Document"
            line = line[line.find('<Document>')+10:]
        if context == "Document":
            if line.find('<description>') >= 0:
                context = "muxp_header"
                line = line[line.find('<description>')+13:]
            if line.find('<Placemark>') >= 0:
                context = "Document_Placemark"
            if line.find('</Placemark>') >= 0:
                context = "Document"
            if line.find('<Folder>') >= 0:
                context = "Folder"
                continue  ###### Assume no other tag than folder in one line; by this have chance to detect subfolder below
            if line.find('</Folder>') >= 0:
                context = "Document"
        if context == "muxp_header":
            if line.find('</description>') >= 0:
                line = line[:line.find('</description>')]
                context = "Document"
            muxp.append(line.strip())
        if context == "Document_Placemark":
            if line.find('<name>') >= 0 and line.find('area:') >= 0:
                context = "Area_Definition"
        if context == "Area_Definition":
            if line.find('<coordinates>') >= 0:
                line = line[line.find('<coordinates>')+13:]
                context = "Area_Coordinates"
        if context == "Area_Coordinates":
            if line.find('</coordinates>') >= 0:
                line = line[:line.find('</coordinates>')]
                muxp.append("area: {} {} {} {}".format(min(area_lon), max(area_lon), min(area_lat), max(area_lat)))
                context = "Document"
            line = line.strip()
            line = line.split()
            for v in line:
                v = v.split(',')
                area_lat.append(float(v[0]))
                area_lon.append(float(v[1]))
        if context == "Folder":
            if line.find('<name>') >= 0 and line.find(':') >= 0:
                muxp.append("") #empty line for new starting command
                muxp.append(line[line.find('<name>')+6:line.find('</name>')])
            if line.find('<description>') >= 0:      
                line = line[line.find('<description>')+13:]
                if line.find('</description>') >= 0:
                    muxp.append("    {}".format(line[:line.find('</description>')]))
                else:
                    context = "Command_Parameters"
            if line.find('<Placemark>') >= 0:
                context = "Folder_Placemark"
            if line.find("</Folder>") >= 0:
                context = "Document"
            if line.find("<Folder>") >= 0:
                context = "Subfolder"
        if context == "Command_Parameters":
            if line.find('</description>') >= 0:
                line = line[:line.find('</description>')]
                context = "Folder"
            line = line.strip()
            muxp.append("    {}".format(line))
        if context == "Folder_Placemark":
            if line.find('</Placemark>') >= 0:
                context = "Folder"
            if line.find('<name>') >= 0 and line.find(':') >= 0:
                muxp.append("    {}".format(line[line.find('<name>')+6:line.find('</name>')]))
                context = "Coords_Definition"
        if context == "Coords_Definition":
            if line.find('<coordinates>') >= 0:
                line = line[line.find('<coordinates>')+13:]
                context = "Coordinates"
        if context == "Coordinates":
            if line.find('</coordinates>') >= 0:
                line = line[:line.find('</coordinates>')]
                context = "Folder_Placemark"
            line = line.strip()
            line = line.split()
            for v in line:
                v = v.split(',')
                muxp.append("    - {} {}".format(v[1], v[0]))
        if context == "Subfolder":
            if line.find('<name>') >= 0 and line.find('3d_coordinates:') >= 0:
                muxp.append("    {}".format(line[line.find('<name>')+6:line.find('</name>')]))
                context = "3d_coordinates"
                continue #### assume name for folder is in separat line, no conflict with name of 3d elevation points below
            if line.find("</Folder>") >= 0:
                context = "Folder"
        if context =="3d_coordinates": #### expected only Pins wiht elevation in this subfolder, nothing else
            if line.find('<name>') >= 0:
                line = line[line.find('<name>')+6:line.find('</name>')]
                elev_3d = float(line)
            if line.find('<coordinates>') >= 0:
                line = line[line.find('<coordinates>')+13:line.find('</coordinates>')]
                line = line.strip()
                v = line.split(',')
                muxp.append("    - {} {} {}".format(v[1], v[0], elev_3d))
            if line.find('</Folder>') >= 0:
                context = "Folder" #Subfoler ends here
                

for line in muxp:
    print(line)

