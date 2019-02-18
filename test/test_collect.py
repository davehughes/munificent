from __future__ import absolute_import
import unittest

from munificent.collect import parse_prediction_points

from . import utils


class TestPredictionResultParsing(unittest.TestCase):

    def test_multiple_predictions_fixture(self):
        prediction_points = utils.load_json_fixture('multiprediction.json')
        points = parse_prediction_points(prediction_points)
        self.assertEqual(299, len(points))
