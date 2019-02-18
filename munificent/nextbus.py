import datetime
import requests
import uuid

from munificent import db
Session = db.configured_session()

JSON_FEED_URL = 'http://webservices.nextbus.com/service/publicJSONFeed'


def list_agencies():
    params = {
        'command': 'agencyList',
    }
    res = requests.get(JSON_FEED_URL, params=params)
    return res.json()


def get_schedule(agency='sf-muni', route='L'):
    params = {
        'command': 'schedule',
        'a': agency,
        'r': route,
    }
    res = requests.get(JSON_FEED_URL, params=params)
    return res.json()


def get_routes(agency='sf-muni'):
    params = {
        'command': 'routeList',
        'a': agency,
    }
    res = requests.get(JSON_FEED_URL, params=params)
    return res.json()


def get_route_config(agency='sf-muni', route=None):
    params = {
        'command': 'routeConfig',
        'a': agency,
        'r': route,
    }
    res = requests.get(JSON_FEED_URL, params=params)
    return res.json()


def get_predictions(agency='sf-muni', route='L', stop='...'):
    params = {
        'command': 'predictions',
        'a': agency,
        'r': route,
        's': stop,
    }
    res = requests.get(JSON_FEED_URL, params=params)
    return res.json()


def get_multistop_predictions(agency='sf-muni', stops=[]):
    '''
    Retrieves predictions for multiple stops of the form '<route_id>|<stop_id>'.
    '''
    params = {
        'command': 'predictionsForMultiStops',
        'a': agency,
        'stops': stops,
    }
    res = requests.get(JSON_FEED_URL, params=params)
    return res.json()


def to_epoch_time(dt):
    EPOCH_START = datetime.datetime(1970, 1, 1)
    return int((dt - EPOCH_START).total_seconds())


def parse_prediction_points(agency, stops):
    prediction_result = get_multistop_predictions(agency, stops)
    points = []
    request_id = uuid.uuid4()
    request_timestamp = to_epoch_time(datetime.datetime.utcnow())
    for prediction in prediction_result['predictions']:
        direction = prediction.get('direction')

        # Sometimes, no predictions are available because e.g. a tunnel is shut down
        if not direction:
            continue

        raw_points = direction.get('prediction', [])
        if type(raw_points) is dict:   # Single prediction
            raw_points = [raw_points]

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
            ))

    return points


def prediction_data_for_route(route):
    stop_codes = [r.route_stop_code for r in route.stops]
    return parse_prediction_points(route.agency.tag, stop_codes)


def prediction_data_for_stop(stop):
    stop_codes = [r.route_stop_code for r in stop.routes]
    return parse_prediction_points(stop.agency.tag, stop_codes)


def get_messages(agency='sf-muni', routes=[]):
    params = {
        'command': 'messages',
        'a': agency,
        'route': routes,
    }
    res = requests.get(JSON_FEED_URL, params=params)
    return res.json()


def get_vehicle_locations(agency='sf-muni', route='L', time=None):
    time = time or datetime.datetime.now()
    params = {
        'command': 'vehicleLocations',
        'a': agency,
        'r': route,
        't': time,  # TODO: to epoch
    }
    res = requests.get(JSON_FEED_URL, params=params)
    return res.json()


def populate_db():
    for agency in list_agencies()['agency']:
        Session.add(db.Agency(**agency))
    Session.commit()

    agencies = (Session.query(db.Agency)
        .filter(db.Agency.tag.in_(['sf-muni'])))

    for agency in agencies:
        route_config_result = get_route_config(agency.tag)
        routes = route_config_result['route']
        for route in routes:
            route_obj = db.Route(
                agency_id=agency.id,
                tag=route['tag'],
                title=route['title'],
            )
            Session.add(route_obj)

            for stop in route['stop']:
                stop_obj = (Session.query(db.Stop)
                    .filter(db.Stop.stopID == int(stop['stopId']))
                    .one_or_none())

                if not stop_obj:
                    stop_obj = db.Stop(
                        agency=agency,
                        lat=float(stop['lat']),
                        lon=float(stop['lon']),
                        stopID=stop['stopId'],
                        tag=stop['tag'],
                        title=stop['title'],
                    )
                    Session.add(stop_obj)

                route_stop_obj = (Session.query(db.RouteStop)
                    .filter(db.RouteStop.route_id == route_obj.id)
                    .filter(db.RouteStop.stop_id == stop_obj.id)
                    .one_or_none())

                if not route_stop_obj:
                    route_stop_obj = db.RouteStop(
                        agency_id=agency.id,
                        route_id=route_obj.id,
                        stop_id=stop_obj.id,
                    )
                    Session.add(route_stop_obj)

    Session.commit()
