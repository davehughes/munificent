from __future__ import absolute_import
import unittest

from munificent.collect import parse_prediction_points, parse_vehicle_locations

from . import utils


class TestPredictionResultParsing(unittest.TestCase):

    def test_multiple_predictions_fixture(self):
        prediction_points = utils.load_json_fixture('multiprediction.json')
        points = parse_prediction_points(prediction_points)
        self.assertEqual(299, len(points))

    def test_vehicle_locations_fixture(self):
        locations_fixture = utils.load_json_fixture('vehicle-locations.json')
        locations = parse_vehicle_locations(locations_fixture)
        self.assertEqual(11, len(locations))

    def test_vehicle_locations_empty(self):
        locations_fixture = utils.load_json_fixture('vehicle-locations.json')
        del locations_fixture['vehicle']
        locations = parse_vehicle_locations(locations_fixture)
        self.assertEqual(0, len(locations))
