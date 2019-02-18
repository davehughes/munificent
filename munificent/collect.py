import json
import time

from munificent import db
from munificent.nextbus import NextBusAPI, NextBusAPIRequestBuilder
Session = db.configured_session()


def run_collection(requests, output_file, period=60.0):
    api = NextBusAPI()

    def generate_data():
        per_request_period = period / float(len(requests))
        cycle = 0
        while True:
            cycle += 1
            cycle_start = time.time()
            for req in requests:
                try:
                    res = api.perform_request(req)
                    predictions = parse_prediction_points(res)
                    for prediction in predictions:
                        yield prediction
                except Exception as e:
                    print(e)
                finally:
                    time.sleep(per_request_period)
            cycle_end = time.time()
            print("Finished cycle {} in {} seconds".format(cycle, cycle_end - cycle_start))

    with open(output_file, 'w') as f:
        for datapoint in generate_data():
            json.dump(datapoint, f)
            f.write('\n')


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
                request_id=unicode(request_id),
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
