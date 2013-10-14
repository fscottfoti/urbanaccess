import psycopg2, cPickle, string, StringIO, sys
import numpy

conn_string = "host='paris.urbansim.org' dbname='sandbox' user='urbanvision' password='Visua1ization'"
conn_string = "host='paris.urbansim.org' dbname='bayarea' user='urbanvision' password='Visua1ization'"
conn_string = "host='paris.urbansim.org' dbname='openstreetmap' user='urbanvision' password='Visua1ization'"

conn = psycopg2.connect(conn_string)
cursor = conn.cursor()

# this is navteq
#s = "select link_id, ST_Length(the_geom), ref_in_id, ST_X(ST_StartPoint(the_geom)), ST_Y(ST_StartPoint(the_geom)), nref_in_id, ST_X(ST_EndPoint(the_geom)), ST_Y(ST_EndPoint(the_geom)) from navteq_streets where cast(func_class as int) > 2"
# osm using distance
s = "select n.id, km*1000, source, ST_X(geom_source3740), ST_Y(geom_source3740), target, ST_X(geom_target3740), ST_Y(geom_target3740) from osm_topo n"
#srid = 2232
#s = "select n.id, km*1000, source, st_x(st_startpoint(st_transform(geom_way,%d))), st_y(st_startpoint(st_transform(geom_way,%d))), target, st_x(st_endpoint(st_transform(geom_way,%d))), st_y(st_endpoint(st_transform(geom_way,%d))) from osm_drcog n where clazz != 11" % (srid,srid,srid,srid)
# osm using travel time
#s = "select id, km*1000, source, ST_X(geom_source3740), ST_Y(geom_source3740), target, ST_X(geom_target3740), ST_Y(geom_target3740), ctimam, ctimmd, ctimea, ctimpm, ctimev, km_tot*1000, geom_way3740 from osm_topo left join travelmodel2010 on osm_topo.tm_id = travelmodel2010.gid where osm_topo.matched > 0"
# network straight from the travel model
#s = "select gid, distance, a, ST_X(ST_StartPoint(the_geom)), ST_Y(ST_StartPoint(the_geom)), b, ST_X(ST_EndPoint(the_geom)), ST_Y(ST_EndPoint(the_geom)), ctimea, ctimam, ctimmd, ctimpm, ctimev, distance, the_geom from travelmodel2010"
#s = "select gid, distance, a, ST_X(ST_StartPoint(the_geom)), ST_Y(ST_StartPoint(the_geom)), b, ST_X(ST_EndPoint(the_geom)), ST_Y(ST_EndPoint(the_geom)), ctimea, ctimam, ctimmd, ctimpm, ctimev, distance, fft, \"TTI_P50\", \"TTI_P80\", the_geom from travelmodelandpems"

srid = 3857
srid = 3740
s = "select n.id, km*1000, source, st_x(st_startpoint(st_transform(geom_way,%d))), st_y(st_startpoint(st_transform(geom_way,%d))), target, st_x(st_endpoint(st_transform(geom_way,%d))), st_y(st_endpoint(st_transform(geom_way,%d))) from osm_planet n where clazz != 11" % (srid,srid,srid,srid)
envelope = (-107.621,34.258,-105.288,36.231)
envelope = (-74.265547,40.484168,-73.718376,40.934265)
envelope = (-123.728,36.668,-120.399,39.011)
s = s + " and st_within(centroid, st_makeenvelope(%f,%f,%f,%f,4326))" % envelope

print s

cursor.execute(s)

records = cursor.fetchall()

print "Fetched %d records" % len(records)

nodes = {}
edges = {}
impedances = {}
geom = {}
for r in records:
    try:
        edgeid, length, aid, ax, ay, bid, bx, by, ea, am, md, pm, ev, tot_km, fft, TTI_50, TTI_80, the_geom = r
    except:
        edgeid, length, aid, ax, ay, bid, bx, by = r
    else: 
        if not TTI_50: TTI_50 = 1.0
        if not TTI_80: TTI_80 = 1.0
        a = numpy.array([ea,am,md,pm,ev,fft,fft*TTI_50,fft*TTI_80],dtype=numpy.float32)
        if tot_km: 
            #print length, tot_km
            assert length <= tot_km+.01
            assert tot_km != 0
            ratio = length / tot_km
            a *= ratio
 
		# travel time for 20MPH based on distance
        static_tt = length / (15 * .44704) / 60.0 

        a = numpy.nan_to_num(a) 
        a[a==0] = static_tt 

        impedances[edgeid] = a
        geom[edgeid] = the_geom

    edges[edgeid] = (length,aid,bid)
    nodes[aid] = (ax,ay)
    nodes[bid] = (bx,by)

d = {}
d['nodeids'] = numpy.array(nodes.keys(),dtype=numpy.int32)
d['nodes'] = numpy.array(nodes.values(),dtype=numpy.float32)
noded = dict(zip(nodes.keys(),range(len(nodes.keys()))))
d['edgeids'] = numpy.array(edges.keys())
d['edges'] = numpy.array([[noded[x[1]],noded[x[2]]] \
								for x in edges.values()],dtype=numpy.int32)
d['edgeweights'] = numpy.array([x[0] for x in edges.values()],dtype=numpy.float32)
d['impedances'] = numpy.array(impedances.values(),dtype=numpy.float32)

walk = d
from pyaccess.pyaccess import PyAccess
pya = PyAccess()
pya.createGraphs(1)
pya.createGraph(0,walk['nodeids'],walk['nodes'],walk['edges'],walk['edgeweights']/1000.0,twoway=1)
SUBGRAPHKEEPTHRESHOLD = 20
numnodes = pya.computeAllDesignVariables(3,"NUMNODES") # nodes within a large distance, 5km
dropidx = numpy.where(numnodes < SUBGRAPHKEEPTHRESHOLD)[0]
print "Removing %d nodes" % dropidx.size
drop_d = {}
for idx in dropidx:
    nid = d['nodeids'][idx]
    del(nodes[nid])
    drop_d[nid] = 1
for eid, value in edges.items():
    if value[1] in drop_d or value[2] in drop_d:
        del(edges[eid])

d['nodeids'] = numpy.array(nodes.keys(),dtype=numpy.int32)
d['nodes'] = numpy.array(nodes.values(),dtype=numpy.float32)
noded = dict(zip(nodes.keys(),range(len(nodes.keys()))))
d['edgeids'] = numpy.array(edges.keys())
d['edges'] = numpy.array([[noded[x[1]],noded[x[2]]] \
								for x in edges.values()],dtype=numpy.int32)
d['edgeweights'] = numpy.array([x[0] for x in edges.values()],dtype=numpy.float32)
d['impedances'] = numpy.array(impedances.values(),dtype=numpy.float32)

cPickle.dump(d,open('network.jar','w'))

sys.exit(0)

t = ['impedance%d float8' % (i+1) for i in range(d['impedances'].shape[1])]
t = string.join(t,sep=',')
s = "DROP TABLE osm_impedances; CREATE TABLE osm_impedances (%s, speed float8, the_geom geometry)" % t

cursor.execute(s)

s = ''
for eid in geom.keys():
    t = string.join([str(x) for x in impedances[eid]],sep=',')
    spd = edges[eid][0] / 1000.0 / 1.6 / (impedances[eid][0]/60.0)
    s += "%s,%f,%s\n" % (t,spd,geom[eid])

s = StringIO.StringIO(s)
cursor.copy_from(s,'osm_impedances',sep=',')
conn.commit()
