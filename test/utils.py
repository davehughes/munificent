import json
import os

TEST_ROOT = os.path.realpath(os.path.dirname(__file__))
TEST_DATA_ROOT = os.path.join(TEST_ROOT, 'data')


def load_json_fixture(relpath):
    path = os.path.join(TEST_DATA_ROOT, relpath)
    return json.load(open(path))
