"""
Read OpenStreetMap XML into a NetworkX Graph and rtree Index
by jonnyhuck (2016) 

based upon Gist:
https://gist.github.com/rajanski/ccf65d4f5106c2cdc70e
by GitHub user rajanski 

...which is a modification of Gist:
https://gist.github.com/aflaxman/287370/ 
by GitHub user aflaxman

...which is based on osm.py from brianw's osmgeocode
http://github.com/brianw/osmgeocode

...which is based on osm.py from Graphserver:
http://github.com/bmander/graphserver/tree/master 
and is copyright (c) 2007, Brandon Martin-Anderson under the BSD License.
"""

import xml.sax
import copy
import networkx as nx
from rtree import index

def read_osm(filename_or_stream, only_roads=True):
    """
    Read graph in OSM format from file specified by name or by stream object.

    Parameters
    ----------
    filename_or_stream : filename or stream object

    Returns
    -------
    G : networkx Graph
    idx : rtree Index
    """
    osm = OSM(filename_or_stream)
    G = nx.DiGraph()
    
    # create rtree index
    idx = index.Index()
 
    for w in osm.ways.itervalues():
        if only_roads and 'highway' not in w.tags:
            continue
        G.add_path(w.nds, id=w.id, highway = w.tags['highway'])
        
        if 'oneway' not in w.tags and  w.tags['highway'] != 'motorway':
            G.add_path(reversed(w.nds), id=w.id, highway = w.tags['highway'])

        elif w.tags['oneway'] != 'yes' and w.tags['oneway'] != '-1' and  w.tags['highway'] != 'motorway':
            G.add_path(reversed(w.nds), id=w.id, highway = w.tags['highway'])

        
    for n_id in G.nodes_iter():
        n = osm.nodes[n_id]
        G.node[n_id] = dict(lon=n.lon,lat=n.lat)#, pos=(n.lon,n.lat))
        
        # load point into the rtree index
        idx.insert(int(n_id), (n.lon, n.lat, n.lon, n.lat))
        
    return G, idx
        
    
class Node:
    def __init__(self, id, lon, lat):
        self.id = id
        self.lon = lon
        self.lat = lat
        self.tags = {}
        
class Way:
    def __init__(self, id, osm):
        self.osm = osm
        self.id = id
        self.nds = []
        self.tags = {}
        
    def split(self, dividers):
        # slice the node-array using this nifty recursive function
        def slice_array(ar, dividers):
            for i in range(1,len(ar)-1):
                if dividers[ar[i]]>1:
                    left = ar[:i+1]
                    right = ar[i:]
                    rightsliced = slice_array(right, dividers)
                    return [left]+rightsliced
            return [ar]
            
        slices = slice_array(self.nds, dividers)
        
        # create a way object for each node-array slice
        ret = []
        i=0
        for slice in slices:
            littleway = copy.copy( self )
            littleway.id += "-%d"%i
            littleway.nds = slice
            ret.append( littleway )
            i += 1
            
        return ret
        
        
 
class OSM:
    def __init__(self, filename_or_stream):
        """ File can be either a filename or stream/file object."""
        nodes = {}
        ways = {}
        
        superself = self
        
        class OSMHandler(xml.sax.ContentHandler):
            @classmethod
            def setDocumentLocator(self,loc):
                pass
            
            @classmethod
            def startDocument(self):
                pass
                
            @classmethod
            def endDocument(self):
                pass
                
            @classmethod
            def startElement(self, name, attrs):
                if name=='node':
                    self.currElem = Node(attrs['id'], float(attrs['lon']), float(attrs['lat']))
                elif name=='way':
                    self.currElem = Way(attrs['id'], superself)
                elif name=='tag':
                    self.currElem.tags[attrs['k']] = attrs['v']
                elif name=='nd':
                    self.currElem.nds.append( attrs['ref'] )
                
            @classmethod
            def endElement(self,name):
                if name=='node':
                    nodes[self.currElem.id] = self.currElem
                elif name=='way':
                    ways[self.currElem.id] = self.currElem
                
            @classmethod
            def characters(self, chars):
                pass
 
        xml.sax.parse(filename_or_stream, OSMHandler)
        
        self.nodes = nodes
        self.ways = ways

        #count times each node is used
        node_histogram = dict.fromkeys( self.nodes.keys(), 0 )
        for way in self.ways.values():
            if len(way.nds) < 2:       #if a way has only one node, delete it out of the osm collection
                del self.ways[way.id]
            else:
                for node in way.nds:
                    node_histogram[node] += 1
        
        #use that histogram to split all ways, replacing the member set of ways
        new_ways = {}
        for id, way in self.ways.iteritems():
            split_ways = way.split(node_histogram)
            for split_way in split_ways:
                new_ways[split_way.id] = split_way
        self.ways = new_ways
