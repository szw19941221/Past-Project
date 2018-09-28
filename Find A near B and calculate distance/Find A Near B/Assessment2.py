from shapely.geometry import shape, mapping, Point, Polygon, LineString
import fiona, mapnik
from pyproj import Geod, Proj, transform
from PIL import Image, ImageDraw, ImageFont
from math import sqrt, floor, log10
import rasterio
import networkx as nx
from osm2nx import read_osm


# Define distance
def ellipsoidalDistance(a, b):
	"""
	Calculate the 'as the crow flies' distance between two locations along an ellipsoid using 
	the Inverse Vincenty method, via the PyProj library. 
	"""
	
	# extract the longitude and latitude values for node a (neighbour)
	nodes = G.subgraph(a).nodes(data=True)
	lng1 = nodes[0][1]['lon']
	lat1 = nodes[0][1]['lat']
	
	# extract the longitude and latitude values for node b (target)
	nodes = G.subgraph(b).nodes(data=True)
	lng2 = nodes[0][1]['lon']
	lat2 = nodes[0][1]['lat']
	
	# set which ellipsoid you would like to use this one is a pretty safe bet for global stuff
	g = Geod(ellps='WGS84')

	# compute forward and back azimuths, plus distance
	azF,azB,distance = g.inv(lng1, lat1, lng2, lat2)

	# we are only interested in the distance
	return distance

# Define second distance function to calculate metric distance between office and to all bar
def ellipsoidalDistance2(lng1, lat1, lng2, lat2):
    g = Geod(ellps = 'WGS84')
    azF,azB,distance = g.inv(lng1,lat1,lng2,lat2)
    return distance


# Open the office shapefile and get geometry of it:
with fiona.open('./data/manchester/jonnysoffice.shp') as office:
    officeLocation = office[0]['geometry']['coordinates']
    print str("Jonny's office's coordinates is:"), str(officeLocation[0]), str(officeLocation[1])

    # Get the geometry of office in shapely format
    for feat in office:
            officeL = shape(feat['geometry'])
    

# Convert OSM XML into network graph and rtree index
G, idx = read_osm('./data/manchester/manchester.xml')


# Create a list to hold the final route and length to each pub
finalRoutes = []
finalLength = []
# Create a list to hold pubs' names
names = []
# Create a list to hold centroid coordinates of pub in shapely format
coors = []


# Calculate distance between Jonny's office and all bars:
# Open Manchester OSM data and extract geometries that categoried as "pub" and name of each pub
with fiona.open('./data/manchester/osm_polygons.shp') as pub:
        print 'Here are info of all pubs in Manchester area:'
        print '***********************************************************************'

        # Loop through all features in OSM polygons
        for feat in pub:
                if feat['properties']['amenity'] == 'pub': # Select polygons based on "amenity" = 'pub'
                        pubLocation = mapping(shape(feat['geometry']).centroid) # Calculate coordinate of centroid for each pub polygon
                        coorPub = pubLocation['coordinates'] # Store X and Y from pubLocation into a new variable
                        polyPub = shape(feat['geometry'])

                        # Store geometries of office and centroid coordinate
                        fromOffice = str(list(idx.nearest((officeLocation[0], officeLocation[1], officeLocation[0], officeLocation[1]), 1))[0])
                        toBar = str(list(idx.nearest((coorPub[0], coorPub[1], coorPub[0], coorPub[1]), 1)) [0])
                        pubName = (feat['properties']['name']) # Extract pubs' names from OSM shapefile

                      
                        print  'Pub Name:', pubName # Print pub name
                        print 'Centriod Coordinates:', coorPub # Print centroid coordinate of pub
                        print 'Node of Bar:', toBar # Print nodes of all pubs


                        #Calculate shorest distance from office to every pub based on nodes
                        try:
                                shortestPath = nx.astar_path(G, source=fromOffice, target=toBar, heuristic=ellipsoidalDistance)

                                # Create a list that holds the shortest path
                                routes = []
                                for n in shortestPath:
                                        node = G.subgraph(n).nodes(data=True) # Get the relevant node from the graph with lat lng data
                                        routes.append([node[0][1]['lon'], node[0][1]['lat']]) # Load the lat lng data into the lineString

                                routetoPub = LineString(routes) # Store routes as LineString

                                #print routetoPub
                                # Get geometries of each route because routetoPub is a sring without geometires
                                routetoPubG = mapping(routetoPub)
                                #print routetoPubG

                                # Measure distance of shortest paths from office to pubs using Inverse Vincenty
                                Length = 0
                                for l in range(len(routetoPubG['coordinates'])-1):
                                        Length += ellipsoidalDistance2(routetoPubG['coordinates'][l][0], routetoPubG['coordinates'][l][1], routetoPubG['coordinates'][l+1][0], routetoPubG['coordinates'][l+1][1])
                                        

                                if Length < 2500: # Filtering pubs within 2.5 km/ 30 mins
                                        finalRoutes.append(routetoPub) # Append routes to list of finalRoutes
                                        str(finalLength.append(Length)) # Append length that less han 25000
                                        with fiona.open('./outputs/shapefiles/route.shp', 'w', driver='ESRI Shapefile', crs='+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs ', schema={'geometry': 'LineString', 'properties': {"length": "str"}}) as o:
                                                # Loop through every length and LineString in finalLength and final Routes, then write them into shapefile
                                                for l, i in zip(finalRoutes, finalLength):
                                                        o.write({ 'geometry': mapping(l), 'properties':{'length': i}})

                                       
                                        #Append geometries of pub polygons in shapely format
                                        coors.append(polyPub)
                                        # Append pun names
                                        names.append(pubName)

                                        with fiona.open('./outputs/shapefiles/pub.shp', 'w', driver='ESRI Shapefile', crs='+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs ', schema={'geometry': 'Polygon', 'properties': {"name":"str"}}) as o:
                                                # Loop through every polygon that categorized as pub and pub name, then write info to shapefile
                                                for n, c in zip(names,coors):
                                                        o.write({ 'geometry': mapping(c), 'properties':{'name': n}})
                                        # Print results
                                        print 'Awesome!', pubName, 'is within 2.5 km of Jonnys office with distance of',str(Length),'M'
                        
                                else:
                                        # Print out info if a pub is 2.5 km away from office
                                        print '-------------------Oh! NO...' + str(pubName) + ' ' + 'is TOO Far------------------'
                                        pass

                        except nx.NetworkXNoPath as e: # Skip NoPath errors and nodes if no path is found
                                print '----------No Accessible Route...:', e # Print error out
                                pass
                        
                else:
                        pass
                # Calculation ends here.




print '----------All routes are saved into shapefile!----------'

print '---------- Rendering Map ...'              

# Render data to the map:
# Make a map to darw to
m = mapnik.Map(800,900)

# Set projetion
m.srs = "+proj=utm +zone=34 +ellps=WGS84 +datum=WGS84 +units=m +no_defs"

# Add scalebar
def addScaleBar(m, mapImg, right): # Three elements in the function: map, the image of scalebar, and position
    mapScale = m.scale() # Return the map scale
    twentyMap = m.width * 0.2 * mapScale # Not sure why 20%
    oom = 10 ** floor(log10(twentyMap)) # Calculate magnitude
    mScale = round(twentyMap/oom)*oom # Get desired width in m
    pxScale = round(mScale/mapScale) # Get desired width in px

    if oom >= 1000: # If the scale is larger than 1000, get a km after the number; if smaller than 1000, get a m after it.
        scaleText = str(int(mScale/1000)) + "km"
    else:
        scaleText = str(int(mScale)) + "m"

    # Draw on the mapImg
    draw = ImageDraw.Draw(mapImg)

    #Set dimensions of text
    tw, th = draw.textsize(scaleText)

    #Set font
    font = ImageFont.truetype('arial.ttf', 12)

    barBuffer  = 5 # Define the scale bar's height	
    lBuffer    = 5 # Line thinckness	
    tickHeight = 12 # The height of image of scale bar

    # add background
    draw.rectangle([(m.width-pxScale-lBuffer-lBuffer-barBuffer, 
	    m.height-barBuffer-lBuffer-lBuffer-tickHeight),
	    (m.width-barBuffer,m.height-barBuffer)], 
	    outline=(0,0,0), fill=(255,255,255))
	
    # add lines
    draw.line([
	    (m.width-lBuffer-pxScale-barBuffer, m.height-tickHeight-barBuffer), 
	    (m.width-lBuffer-pxScale-barBuffer, m.height-lBuffer-barBuffer), 
	    (m.width-lBuffer-barBuffer, m.height-lBuffer-barBuffer), 
	    (m.width-lBuffer-barBuffer, m.height-tickHeight-barBuffer)], 
	    fill=(0, 0, 0), width=1)
	
    # add label
    draw.text(( 
	    (m.width-lBuffer-lBuffer-pxScale/2) - tw/2, 
	    m.height-barBuffer-lBuffer-lBuffer-th), 
	    scaleText, fill=(0,0,0), font=font)


# Add background color to map
m.background = mapnik.Color('white')


# Make a style for the raster basemap and append to the map
bStyle = mapnik.Style()
bRule = mapnik.Rule()
bs = mapnik.RasterSymbolizer()
bs.opacity = 0.6
bRule.symbols.append(bs)
bStyle.rules.append(bRule)
m.append_style('Base Style',bStyle)
# create a layer for the raster basemap and add to the map
rLayer = mapnik.Layer('Manchester')
# Set projection of OSGB36 because this image hasn't been georeferenced
rLayer.srs ='+proj=tmerc +lat_0=49 +lon_0=-2 +k=0.9996012717 +x_0=400000 +y_0=-100000 +ellps=airy +datum=OSGB36 +units=m +no_defs'
rLayer.datasource = mapnik.Gdal(file='./data/manchester/maps/raster-25k/sj89.tif')
rLayer.styles.append('Base Style')
m.layers.append(rLayer)



# Add a style for office
oStyle = mapnik.Style()
oRule = mapnik.Rule()
os = mapnik.PointSymbolizer()
os.filename = "office.png" # Add external source of symbol
os.transform = "scale(0.15)"
os.allow_overlap = False
oRule.symbols.append(os)
oStyle.rules.append(oRule)
m.append_style('Office Style',oStyle)
# Add a layer for office
layer = mapnik.Layer('Office')
layer.datasource = mapnik.Shapefile(file='./data/manchester/jonnysoffice.shp')
layer.styles.append('Office Style')
m.layers.append(layer)



# Add a style for the routes
sStyle = mapnik.Style()
sRule1 = mapnik.Rule()
sRule2 = mapnik.Rule()
sRule3 = mapnik.Rule()
# Create filters to display different colors based on distance
s1_f = mapnik.Filter("[length] > '1000'and [length] < '2000'".encode('utf-8'))
s2_f = mapnik.Filter("[length] > '2000'and [length] < '2500'".encode('utf-8'))
s3_f = mapnik.Filter("[length] < '1000'".encode('utf-8'))
# Add styles
sRule1.symbols.append(mapnik.LineSymbolizer(mapnik.Color('blue'), 4))
sRule2.symbols.append(mapnik.LineSymbolizer(mapnik.Color('red'), 4))
sRule3.symbols.append(mapnik.LineSymbolizer(mapnik.Color('green'), 10))# No route show up and I an not sure why
# Add filter to map
sRule1.filter = s1_f
sRule2.filter = s2_f
sRule3.filter = s3_f
# Append rules to style
sStyle.rules.append(sRule1)
sStyle.rules.append(sRule2)
sStyle.rules.append(sRule3)
m.append_style('Route Style',sStyle)
# Add layer for routes
layer = mapnik.Layer('Shortest_Path_Pub')
layer.datasource = mapnik.Shapefile(file='./outputs/shapefiles/route.shp')
layer.styles.append('Route Style')
m.layers.append(layer)



# Add labels to the pub using TextSymbolizer: first define which field is used as label, in my case 'name', next define font case, size and color.
t = mapnik.TextSymbolizer(mapnik.Expression('[name]'), 'DejaVu Sans Bold', 15, mapnik.Color('black'))
# Add halo
t.halo_fill = mapnik.Color('white')
t.halo_radius = 2
# Add a style for pubs within 30-min of walk
# However, polygons are actually not visible on the map because they are overlapped with labels
sp = mapnik.Style()
rp = mapnik.Rule()
rp.symbols.append(mapnik.PolygonSymbolizer(mapnik.Color('red')))
rp.symbols.append(mapnik.LineSymbolizer(mapnik.Color('#ffffff'), 3))
rp.symbols.append(t)
sp.rules.append(rp)
m.append_style('Pub Style',sp)
# Add layer for pubs
layer = mapnik.Layer('Pubs')
layer.datasource = mapnik.Shapefile(file='./outputs/shapefiles/pub.shp')
layer.styles.append('Pub Style')
m.layers.append(layer)


# Get the bounds of office
b = officeL.bounds

# create a 'Proj' object for WGS84 and UTM zone 34
p1 = Proj(init='epsg:4326')
p2 = Proj(init='epsg:32634') # I tried to change second proj to OSGB36, but it didn't work with a blank final output

# Transform the bounds coordinates to the map projection
x1, y1 = transform(p1, p2, b[0], b[1])
x2, y2 = transform(p1, p2, b[2], b[3])

# Set a buffer to zoom out map
buffer = 350

# Zoom the map to the route shape (with buffer) and render the map to file
m.zoom_to_box(mapnik.Box2d(x1-buffer, y1-buffer, x2+buffer, y2+buffer))
m.zoom(5)
mapnik.render_to_file(m, 'outputs/final.png', 'png')

# Open pub image
mapImg = Image.open('outputs/final.png')

# Call the scalebar function and set 'left' True to position scalebar on the left side
addScaleBar(m,mapImg,True)

# open and resize north arrow onto the map (using itself as a mask to maintain transparency)
northArrow = Image.open('arrow.png').resize((40,70), Image.ANTIALIAS)
mapImg.paste(northArrow, (5, 6), northArrow)

# Save image
mapImg.save('outputs/final.png')

# Open final map
Image.open('outputs/final.png').show()
print "All Done! Hell YEAH!"
