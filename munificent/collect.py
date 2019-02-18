# -*- coding: utf-8 -*-
import gzip
import json
import logging
import os
import signal
import time

from munificent import db
from munificent.nextbus import NextBusAPI, NextBusAPIRequestBuilder
Session = db.configured_session()

LOG = logging.getLogger(__name__)


def run_collection(requests, output_file, period=60.0):
    api = NextBusAPI()
    emitter = Emitter(open_file_gzip(output_file))
    collector = Collector(api, requests, emitter=emitter, period=period)

    def hup(*args):
        LOG.info("Received HUP signal, flushing emitter")
        emitter.flush()

    signal.signal(signal.SIGHUP, hup)

    try:
        LOG.info("Running collection on PID: {}".format(os.getpid()))
        collector.run()
    finally:
        emitter.flush()


class Collector(object):

    def __init__(self, api, requests, emitter, period=60.0):
        self.api = api
        self.requests = requests
        self.period = period
        self.emitter = emitter

    def run(self):
        def generate_records():
            per_request_period = self.period / float(len(self.requests))
            cycle = 0
            while True:
                cycle += 1
                cycle_start = time.time()
                for req in self.requests:
                    request_start = time.time()
                    try:
                        res = self.api.perform_request(req, timeout=10.0)
                        predictions = parse_prediction_points(res)
                        for prediction in predictions:
                            yield prediction
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


def open_file_normal(path):
    def open_file(mode):
        return open(path, mode)
    return open_file


def open_file_gzip(path):
    def open_file(mode):
        return gzip.open(path, mode)
    return open_file


class Emitter(object):

    def __init__(self, file_opener):
        self._open_file = file_opener

    def emit(self, record):
        f = self._output_handle
        json.dump(record, f)
        f.write('\n')

    @property
    def _output_handle(self):
        if not hasattr(self, '_output_handle_'):
            self._output_handle_ = self._open_file('a')
        return self._output_handle_

    def flush(self):
        '''
        Higher level flush that closes and resets the internal output handle
        '''
        output_handle = getattr(self, '_output_handle_', None)
        if output_handle:
            output_handle.flush()
            output_handle.close()
            del self._output_handle_

    def __del__(self):
        self.flush()


def get_prediction_results(requests):
    '''
    Gather prediction results once for the given requests.
    '''
    api = NextBusAPI()
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


def parse_bool_string(s, true_values=None):
    true_values = true_values or ['true']
    return s in true_values


def get_muni_train_requests():
    route_titles = [
        'F-Market & Wharves',
        'J-Church',
        'KT-Ingleside-Third Street',
        'L-Taraval',
        'M-Ocean View',
        'N-Judah',
        'NX-Express',
        'S-Shuttle',
        ]
    routes = (Session.query(db.Route).filter(db.Route.title.in_(route_titles)).all())
    reqbuilder = NextBusAPIRequestBuilder()
    return [reqbuilder.get_predictions_for_route(route) for route in routes]
