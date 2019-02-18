import datetime
import uuid

import requests

from munificent import db
Session = db.configured_session()


DEFAULT_JSON_FEED_URL = 'http://webservices.nextbus.com/service/publicJSONFeed'


class NextBusAPI(object):

    def __init__(self, json_feed_url=DEFAULT_JSON_FEED_URL):
        self.request_builder = NextBusAPIRequestBuilder(json_feed_url)
        self.session = requests.Session()
        self._build_proxy_methods()

    def perform_request(self, request, **kwargs):
        '''
        Perform the provided request, returning a JSON result.  This is typically
        used in situations where prebuilt queries (e.g. from a request builder object)
        are being performed against the API generically.
        '''
        request_id = uuid.uuid4()
        res = self.session.send(request.prepare(), **kwargs)
        res.raise_for_status()
        result = res.json()
        result['_meta'] = {
            'timestamp': to_epoch_time(datetime.datetime.utcnow()),
            'request_id': request_id,
        }
        return result

    def _build_proxy_methods(self):
        '''
        Creates wrapped methods corresponding to all request builder methods that
        proxy passed arguments to build a request, then perform that request using
        the API's configured session.
        '''
        proxy_methods = []
        for attr_name in dir(self.request_builder):
            if attr_name.startswith('_'):
                continue

            attr_value = getattr(self.request_builder, attr_name, None)
            if not callable(attr_value):
                continue

            proxy_methods.append((attr_name, attr_value))

        def build_proxy_method(attr, m):
            def perform_request(*args, **kwargs):
                request_args = kwargs.pop('request_args', {})
                req = m(*args, **kwargs)
                return self.perform_request(req, **request_args)
            perform_request.__name__ = 'proxy_{}'.format(attr)
            return perform_request

        for attr, value in proxy_methods:
            setattr(self, attr, build_proxy_method(attr, value))


class NextBusAPIRequestBuilder(object):

    def __init__(self, json_feed_url=DEFAULT_JSON_FEED_URL):
        self.feed_url = json_feed_url

    # Core requests
    def list_agencies(self):
        return requests.Request('GET', self.feed_url, params={
            'command': 'agencyList',
            })

    def get_schedule(self, agency, route):
        return requests.Request('GET', self.feed_url, params={
            'command': 'schedule',
            'a': agency,
            'r': route,
            })

    def get_routes(self, agency, route=None):
        return requests.Request('GET', self.feed_url, params={
            'command': 'routeList',
            'a': agency,
            })

    def get_route_config(self, agency, route=None):
        return requests.Request('GET', self.feed_url, params={
            'command': 'routeConfig',
            'a': agency,
            'r': route,
            })

    def get_predictions(self, agency, route, stop):
        return requests.Request('GET', self.feed_url, params={
            'command': 'predictions',
            'a': agency,
            'r': route,
            's': stop,
            })

    def get_multistop_predictions(self, agency, stops):
        return requests.Request('GET', self.feed_url, params={
            'command': 'predictionsForMultiStops',
            'a': agency,
            'stops': stops,
            })

    def get_messages(self, agency, routes=[]):
        return requests.Request('GET', self.feed_url, params={
            'command': 'messages',
            'a': agency,
            'route': routes,
            })

    def get_vehicle_locations(self, agency, route, time=None):
        return requests.Request('GET', self.feed_url, params={
            'command': 'vehicleLocations',
            'a': agency,
            'r': route,
            't': time,  # TODO: to epoch
            })

    # Higher-level requests
    def get_predictions_for_route(self, route):
        stop_codes = [r.route_stop_code for r in route.stops]
        return self.get_multistop_predictions(route.agency.tag, stop_codes)

    def get_predictions_for_stop(self, stop):
        stop_codes = [r.route_stop_code for r in stop.routes]
        return self.get_multistop_predictions(stop.agency.tag, stop_codes)


def to_epoch_time(dt):
    EPOCH_START = datetime.datetime(1970, 1, 1)
    return int((dt - EPOCH_START).total_seconds())


def populate_db():
    api = NextBusAPI()
    for agency in api.list_agencies()['agency']:
        Session.add(db.Agency(**agency))
    Session.commit()

    agencies = (Session.query(db.Agency)
        .filter(db.Agency.tag.in_(['sf-muni'])))

    for agency in agencies:
        route_config_result = api.get_route_config(agency.tag)
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
