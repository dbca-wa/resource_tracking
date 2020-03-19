import os
import logging
import itertools
from multiprocessing import Process, Pipe
from osgeo import ogr

from django.contrib.gis.geos import GEOSGeometry,Polygon,MultiPolygon
from django.db import connection
from django.forms.models import model_to_dict
from django.db.models import Q,F
from django.utils import timezone

logger = logging.getLogger(__name__)

from .models import Repeater,RepeaterTXAnalysis,RepeaterRXAnalysis,RepeaterTXCoverage,RepeaterRXCoverage,RepeaterTXCoverageSimplified,RepeaterRXCoverageSimplified

TX = (RepeaterTXAnalysis,RepeaterTXCoverage,RepeaterTXCoverageSimplified)
RX = (RepeaterRXAnalysis,RepeaterRXCoverage,RepeaterRXCoverageSimplified)

def simplify(scope=TX,repeaterids=None,dn=None,enforce=False):
    #merge 
    parent_conn,child_conn = Pipe(True)
    p = Process(target=_mergeInProcess,args=(child_conn,))
    p.daemon = True
    p.start()
    parent_conn.send([scope,repeaterids,enforce])
    result = parent_conn.recv()
    parent_conn.close()

    #resolve dn overlap
    resovleDNOverlap(scope,repeaterids=repeaterids,dn=dn,enforce=enforce)

    resolveRepeaterOverlap(scope,enforce=enforce)

def _mergeInProcess(conn):
    scope,repeaterids,enforce = conn.recv()
    result = merge(scope,repeaterids,enforce)
    conn.send(result)
    conn.close()

def _fix_geometry(geom):
    """
    Return tuple(geom,invalid_geom)
    """
    polygons = []
    invalid_polygons = []
    for poly in [geom] if isinstance(geom,Polygon) else geom:
        if poly.valid:
            polygons.append(poly)
        else:
            ogr_poly = ogr.CreateGeometryFromWkt(poly.wkt)
            ogr_poly = ogr_poly.Buffer(0)
            buffered_poly = GEOSGeometry(ogr_poly.ExportToWkt())
            if isinstance(buffered_poly,Polygon):
                if buffered_poly.valid:
                    polygons.append(buffered_poly)
                else:
                    invalid_polygons.append(buffered_poly)
            else:
                for buffered_p in buffered_poly:
                    if buffered_p.valid:
                        polygons.append(buffered_p)
                    else:
                        invalid_polygons.append(buffered_p)
    if polygons:
        geom = MultiPolygon(polygons)
    else:
        geom = None
        
    if invalid_polygons:
        invalid_geom = MultiPolygon(invalid_polygons)
    else:
        invalid_geom = None

    return (geom,invalid_geom)
    


def merge(scope,repeaterids=None,enforce=False):
    analysis_model,coverage_model,simplified_coverage_model = scope
    if enforce:
        analysis_qs = analysis_model.objects.all().order_by("repeater__site_name")
    else:
        analysis_qs = analysis_model.objects.filter(Q(last_merged__isnull=True) | Q(last_merged__lt=F("last_analysed"))).order_by("repeater__site_name")
    if repeaterids:
        analysis_qs = analysis_qs.filter(repeater_id__in=repeaterids)
    #get the repeater list to merge.
    #reset simplify related columns in analysis model
    repeaters = []
    for analysis in analysis_qs:
        analysis.last_merged = None
        analysis.last_resolved = None
        analysis.last_simplified = None
        analysis.save(update_fields=["last_merged","last_resolved","last_simplified"])
        repeaters.append(analysis.repeater)
    #delete existing merged data   
    cov_qs = simplified_coverage_model.objects.filter(repeater__in=repeaters)
    cov_qs.delete()

    for rep in repeaters:
        multi = ogr.Geometry(ogr.wkbMultiPolygon)
        previous_coverage = None
        for coverage in itertools.chain(coverage_model.objects.filter(repeater=rep).order_by("-dn"),[None]):
            if previous_coverage is None:
                previous_coverage = coverage
            elif coverage and coverage.dn == previous_coverage.dn:
                pass
            else:
                #save the data
                union = multi.UnionCascaded()
                wkt = union.ExportToWkt()
                geom = GEOSGeometry(wkt)
                if isinstance(geom,Polygon):
                    geom = MultiPolygon([geom])
                invalid_geom = None
                if not geom.valid:
                    geom,invalid_geom = _fix_geometry(geom)
                
                if geom:
                    simplified_coverage = simplified_coverage_model()
                    for f in simplified_coverage_model._meta.fields:
                        setattr(simplified_coverage,f.name,getattr(previous_coverage,f.name))

                    simplified_coverage.geom = geom
                    simplified_coverage.id = None
                    simplified_coverage.save()
                    logger.info("Save the coverage for repeater (site_name={},dn={},polygons={})".format(rep.site_name,previous_coverage.dn,len(geom)))
                if invalid_geom:
                    simplified_coverage = simplified_coverage_model()
                    for f in simplified_coverage_model._meta.fields:
                        setattr(simplified_coverage,f.name,getattr(previous_coverage,f.name))

                    simplified_coverage.geom = invalid_geom
                    simplified_coverage.id = None
                    simplified_coverage.save()
                    logger.warning("Save the invalid coverage  for repeater (site_name={},dn={},polygons={})".format(rep.site_name,coverage.dn,len(geom)))
                if coverage:
                    multi = ogr.Geometry(ogr.wkbMultiPolygon)
                    previous_coverage = coverage
            if coverage:
                for poly in coverage.geom:
                    wkt = poly.wkt
                    multi.AddGeometryDirectly(ogr.CreateGeometryFromWkt(wkt))

        analysis_model.objects.filter(repeater=rep).update(last_merged=timezone.now())

def _resolveDNOverlapInProcess(conn):
    simplified_coverage_model,coverageid = conn.recv()
    result = _resolveDNOverlap(simplified_coverage_model,coverageid)
    conn.send(result)
    conn.close()

def _resolveDNOverlap(simplified_coverage_model,coverageid):
    coverage = simplified_coverage_model.objects.get(id=coverageid)
    rep = coverage.repeater
    geom = coverage.geom

    polygons = []
    logger.info("\nBegin to resolve dn overlap for the coverage (site_name={},dn={})".format(rep.site_name,coverage.dn))

    bbox = geom.envelope
    for s_coverage in simplified_coverage_model.objects.filter(repeater=rep,dn__gt=coverage.dn).order_by("-dn"):
        s_geom = s_coverage.geom
        logger.info("    Begin to resolve dn overlap for the coverage (site_name={}) between (dn={},polygons={}) and (dn={},polygons={})".format(
            rep.site_name,coverage.dn,len(geom),s_coverage.dn,len(s_geom))
        )
        s_bbox = s_geom.envelope
        if not bbox.intersects(s_bbox):
            continue

        geom1 = geom.difference(s_geom)
        if not geom1:
            if not geom.valid:
                logger.warning("The polygon of the coverage is invalid, skip (site_name={},dn={})".format(rep.site_name,coverage.dn))
                geom = coverage.geom
                break
            elif not s_geom.valid:
                logger.warning("    The polygon of the coverage is invalid, skip (site_name={},dn={})".format(rep.site_name,s_coverage.dn))
                continue
            else:
                #geom totally contained by s_geom
                geom = None
                break

        else:
            geom = geom1
    
    if geom:
        if isinstance(geom,Polygon):
            geom = MultiPolygon([geom])

        if (geom == coverage.geom or geom.wkt == coverage.geom.wkt):
            logger.info("Coverage is not intersection with polygons with higher dn  (site_name={},dn={},new polygons={},polygons={})".format(rep.site_name,coverage.dn,len(geom),len(coverage.geom)))
            return

    invalid_geom = None
    if geom:
        if not geom.valid:
            logger.info("Resolved multi polygon is invalid. fix it")
            geom,invalid_geom = _fix_geometry(geom)

    if geom:
        coverage.geom = geom
        coverage.save(update_fields=["geom"])
        logger.info("Save the coverage which is intersection with polygons with higher dn  (site_name={},dn={},new polygons={},polygons={})".format(rep.site_name,coverage.dn,len(geom),len(coverage.geom)))
    else:
        coverage.delete()
        logger.info("Delete the coverage which is totally contained by the polygons with higher dn  (site_name={},dn={},polygons={})".format(rep.site_name,coverage.dn,len(geom)))

    if invalid_geom:
        coverage.geom = invalid_geom
        coverage.id = None
        coverate.save()
        logger.warning("Save the invalid coverage  for repeater (site_name={},dn={},polygons={})".format(rep.site_name,coverage.dn,len(invalid_geom)))

def resovleDNOverlap(scope,repeaterids=None,dn=None,enforce=False):
    coverageid_sql = "SELECT id FROM {} WHERE repeater_id = {}{} order by dn desc"

    analysis_model,coverage_model,simplified_coverage_model = scope
    if enforce:
        analysis_qs = analysis_model.objects.all().order_by("repeater__site_name")
    else:
        analysis_qs = analysis_model.objects.filter(Q(last_resolved__isnull=True) | Q(last_resolved__lt=F("last_merged"))).order_by("repeater__site_name")
    if repeaterids:
        analysis_qs = analysis_qs.filter(repeater_id__in=repeaterids)
    #get the repeater list to merge.
    #reset simplify related columns in analysis model
    repeaters = []
    for analysis in analysis_qs:
        analysis.last_resolved = None
        analysis.last_simplified = None
        analysis.save(update_fields=["last_resolved","last_simplified"])
        repeaters.append(analysis.repeater)

    for rep in repeaters:
        coverageids = []
        with connection.cursor() as cursor:
            cursor.execute(coverageid_sql.format(simplified_coverage_model._meta.db_table,rep.id, "" if dn is None else "AND dn < {}".format(dn)))
            coverageids = [int(row[0]) for row in cursor.fetchall()]

        for coverageid in coverageids[1:]:
            parent_conn,child_conn = Pipe(True)
            p = Process(target=_resolveDNOverlapInProcess,args=(child_conn,))
            p.daemon = True
            p.start()
            parent_conn.send([simplified_coverage_model,coverageid])
            result = parent_conn.recv()
            parent_conn.close()

        analysis_model.objects.filter(repeater=rep).update(last_resolved=timezone.now())


def _resolveRepeaterOverlapInProcess(conn):
    analysis_model,simplified_coverage_model,rep1,rep2 = conn.recv()
    result = _resolveRepeaterOverlap(analysis_model,simplified_coverage_model,rep1,rep2)
    conn.send(result)
    conn.close()

def _resolveRepeaterOverlap(analysis_model,simplified_coverage_model,rep1,rep2):
    logger.info("\nReolve the overlap between repeater({}) and repeater({})".format(rep1.site_name,rep2.site_name))
    rep2_coverages = list(simplified_coverage_model.objects.filter(repeater=rep2).order_by("-dn"))
    for coverage1 in simplified_coverage_model.objects.filter(repeater=rep1).order_by("-dn"):
        geom1 = coverage1.geom
        cov1_bbox = geom1.envelope

        for coverage2 in rep2_coverages:
            logger.info("    Reolve the overlap between coverage(site_name={},dn={}) and coverage(site_name={},dn={})".format(rep1.site_name,coverage1.dn,rep2.site_name,coverage2.dn))
            geom2 = coverage2.geom
            cov2_bbox = geom2.envelope
            if not cov1_bbox.intersects(cov2_bbox):
                continue
            if coverage1.dn >= coverage2.dn:
                _geom = geom2.Difference(geom1)
                if not _geom:
                    if not geom1.valid:
                        logger.warning("The polygon of the coverage is invalid, skip (site_name={},dn={})".format(rep1.site_name,coverage1.dn))
                        break
                    elif not geom2.valid:
                        logger.warning("The polygon of the coverage is invalid, skip (site_name={},dn={})".format(rep2.site_name,coverage2.dn))
                        continue
                    else:
                        #geom2 is totally contained by geom1
                        geom2 = None
                        logger.info("The polygon of the coverage is totally contained by another coverage(site_name={},dn={}), skip (site_name={},dn={})".format(
                            rep1.site_name,coverage1.dn,rep2.site_name,coverage2.dn)
                        )
                        coverage2.delete()
                        coverage2.id = None
                else:
                    geom2 = _geom
                    if isinstance(geom2,Polygon):
                        geom2 = MultiPolygon([geom2])
                    coverage2.geom = geom2
                    coverage2.save(update_fields=["geom"])
                    logger.info("The polygon of the coverage is overlaped with another coverage(site_name={},dn={}), (site_name={},dn={})".format(
                        rep1.site_name,coverage1.dn,rep2.site_name,coverage2.dn
                    ))
            else:
                _geom = geom1.Difference(geom2)
                if not _geom:
                    if not geom1.valid:
                        logger.warning("The polygon of the coverage is invalid, skip (site_name={},dn={})".format(rep1.site_name,coverage1.dn))
                        break
                    elif not geom2.valid:
                        logger.warning("The polygon of the coverage is invalid, skip (site_name={},dn={})".format(rep2.site_name,coverage2.dn))
                        continue
                    else:
                        #geom2 is totally contained by geom1
                        geom1 = None
                        break
                else:
                    geom1 = _geom

        
        if geom1:
            if isinstance(geom1,Polygon):
                geom1 = MultiPolygon([geom1])
    
            if (geom1 == coverage1.geom or geom1.wkt == coverage1.geom.wkt):
                logger.info("Coverage is not intersected with polygons with higher dn  (site_name={},dn={},new polygons={},polygons={})".format(rep1.site_name,coverage1.dn,len(geom1),len(coverage1.geom)))
                return
    
        invalid_geom = None
        if geom1:
            if not geom1.valid:
                logger.info("Resolved multi polygon is invalid. fix it")
                geom1,invalid_geom = _fix_geometry(geom1)
    
        if geom1:
            coverage1.geom = geom1
            coverage1.save(update_fields=["geom"])
            logger.info("Save the coverage which is intersected with polygons with higher dn  (site_name={},dn={},new polygons={},polygons={})".format(rep1.site_name,coverage1.dn,len(geom1),len(coverage1.geom)))
        else:
            coverage1.delete()
            logger.info("Delete the coverage which is totally contained by the polygons with higher dn  (site_name={},dn={},polygons={})".format(rep1.site_name,coverage1.dn,len(geom1)))
    
        if invalid_geom:
            coverage1.geom = invalid_geom
            coverage1.id = None
            coverate1.save()
            logger.warning("Save the invalid coverage  for repeater (site_name={},dn={},polygons={})".format(rep1.site_name,coverage1.dn,len(invalid_geom)))

def resolveRepeaterOverlap(scope,enforce=False):
    analysis_model,coverage_model,simplified_coverage_model = scope

    repeaters_bbox = []
    bbox_sql = "SELECT ST_AsText(ST_Envelope(ST_Collect(geom))) FROM {} WHERE repeater_id = {}"
    with connection.cursor() as cursor:
        for rep in Repeater.objects.all().order_by("id"):
            cursor.execute(bbox_sql.format(simplified_coverage_model._meta.db_table,rep.id))
            wkt = cursor.fetchone()[0]
            if wkt:
                bbox = GEOSGeometry(wkt)
                repeaters_bbox.append((rep,bbox))

    index1 = 0
    while index1 < len(repeaters_bbox):
        index2 = index1 + 1
        rep1,bbox1 = repeaters_bbox[index1]
        index1 += 1
        if index1 == len(repeaters_bbox):
            #last repeater
            analysis_model.objects.filter(repeater=rep1).update(last_simplified=timezone.now())
            continue

        analysis1 = analysis_model.objects.get(repeater=rep1)
        changed = False
        while index2 < len(repeaters_bbox):
            rep2,bbox2 = repeaters_bbox[index2]
            index2 += 1
            analysis2 = analysis_model.objects.get(repeater=rep2)
            if not enforce and analysis1.last_simplified and analysis1.last_simplified > analysis1.last_resolved and analysis1.last_simplified > analysis2.last_resolved:
                continue

            changed = True
            if not bbox1.intersects(bbox2):
                continue

            changed = True
            parent_conn,child_conn = Pipe(True)
            p = Process(target=_resolveRepeaterOverlapInProcess,args=(child_conn,))
            p.daemon = True
            p.start()
            parent_conn.send([analysis_mode,simplified_coverage_model,rep1,rep2])
            result = parent_conn.recv()
            parent_conn.close()
        
        if changed:
            analysis_model.objects.filter(repeater=rep1).update(last_simplified=timezone.now())


#merge(TX,repeaterids=[153])
#resovleDNOverlap(TX) 
#resovleDNOverlap(TX,repeaterids=[153],dn=155) 
#resovleDNOverlap(TX,repeaterids=[153]) 
#simplify(TX,repeaterids=[153])
#simplify(TX)
