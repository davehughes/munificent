# -*- coding: utf-8 -*-
import logging
import time

from munificent import db
from munificent.nextbus import NextBusAPIRequestBuilder

Session = db.configured_session()
LOG = logging.getLogger(__name__)


class Collector(object):

    def __init__(self, probes, emitter, period=60.0):
        self.probes = probes
        self.period = period
        self.emitter = emitter

    def run(self):
        def generate_records():
            per_request_period = self.period / float(len(self.probes))
            cycle = 0
            while True:
                cycle += 1
                cycle_start = time.time()
                for probe in self.probes:
                    request_start = time.time()
                    try:
                        for record in probe.collect():
                            yield record
                    except Exception as e:
                        LOG.exception(e)
                    finally:
                        request_elapsed = time.time() - request_start
                        request_period_remaining = per_request_period - request_elapsed
                        time.sleep(max(request_period_remaining, 0))
                cycle_end = time.time()
                LOG.info("Finished cycle {} in {} seconds".format(cycle, cycle_end - cycle_start))

        for record in generate_records():
            self.emitter.emit(record)


class CollectionProbe(object):
    def __init__(self, api, request, record_parser):
        self.api = api
        self.request = request
        self.record_parser = record_parser

    def collect(self, **request_args):
        result = self.api.perform_request(self.request, timeout=10)
        return self.record_parser(result)


MUNI_TRAIN_ROUTES = [
    'F-Market & Wharves',
    'J-Church',
    'KT-Ingleside-Third Street',
    'L-Taraval',
    'M-Ocean View',
    'N-Judah',
    'NX-Express',
    'S-Shuttle',
    ]


def get_muni_train_prediction_probes(api):
    route_titles = MUNI_TRAIN_ROUTES
    routes = (Session.query(db.Route).filter(db.Route.title.in_(route_titles)).all())
    reqbuilder = NextBusAPIRequestBuilder()
    requests = [reqbuilder.get_predictions_for_route(route) for route in routes]
    probes = [CollectionProbe(api, req, parse_prediction_points) for req in requests]
    return probes


def get_muni_train_location_probes(api):
    route_titles = MUNI_TRAIN_ROUTES
    routes = (Session.query(db.Route).filter(db.Route.title.in_(route_titles)).all())
    reqbuilder = NextBusAPIRequestBuilder()
    requests = [reqbuilder.get_vehicle_locations_for_route(route) for route in routes]
    probes = [CollectionProbe(api, req, parse_vehicle_locations) for req in requests]
    return probes


def get_prediction_results(api, requests):
    '''
    Gather prediction results once for the given requests.
    '''
    results = []
    for req in requests:
        res = api.perform_request(req)
        predictions = parse_prediction_points(res)
        results.extend(predictions)
    return results


def parse_prediction_points(prediction_result):
    points = []
    request_id = prediction_result['_meta']['request_id']
    request_timestamp = prediction_result['_meta']['timestamp']
    for prediction in prediction_result['predictions']:
        direction = prediction.get('direction')

        # Sometimes, no predictions are available because e.g. a tunnel is shut down
        if not direction:
            continue

        # 'direction' can be a scalar or a list (single/multi prediction)
        if type(direction) is list:
            prediction_records = direction
        else:
            prediction_records = [direction]

        # Coalesce the many options into a standardized list of prdiction points
        raw_points = []
        for prediction_rec in prediction_records:
            rec_points = prediction_rec.get('prediction', [])
            if type(rec_points) is dict:   # Single prediction
                raw_points.append(rec_points)
            else:
                raw_points.extend(rec_points)

        for prediction_point in raw_points:
            points.append(dict(
                # Context data
                type='prediction',
                request_id=str(request_id),
                request_timestamp=request_timestamp,
                routeTag=prediction['routeTag'],
                stopTag=prediction['stopTag'],
                routeTitle=prediction['routeTitle'],
                stopTitle=prediction['stopTitle'],

                # Prediction data
                epochTime=int(prediction_point['epochTime']),
                seconds=int(prediction_point['seconds']),
                minutes=int(prediction_point['minutes']),
                isDeparture=(prediction_point['isDeparture'].lower().strip() == 'true'),
                block=prediction_point.get('block'),
                vehicle=prediction_point.get('vehicle'),
                dirTag=prediction_point.get('dirTag'),
                tripTag=prediction_point.get('tripTag'),
                affectedByLayover=parse_bool_string(
                    prediction_point.get('affectedByLayover', 'false'),
                    true_values=['true'],
                ),
            ))

    return points


def parse_vehicle_locations(location_result):
    locations = []
    request_id = location_result['_meta']['request_id']
    request_timestamp = location_result['_meta']['timestamp']
    try:
        for location in location_result.get('vehicle', []):
            location.update(dict(
                # Context data
                type='vehicle_location',
                request_id=request_id,
                request_timestamp=request_timestamp,

                # Location data
                vehicle=location['id'],
                lat=float(location['lat']),
                lon=float(location['lon']),
                heading=int(location['heading']),
                predictable=parse_bool_string(location['predictable']),
                secsSinceReport=int(location['secsSinceReport']),
            ))
            locations.append(location)
    except Exception as e:
        import ipdb; ipdb.set_trace();

    return locations


def parse_bool_string(s, true_values=None):
    true_values = true_values or ['true']
    return s in true_values
