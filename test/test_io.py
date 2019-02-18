import tempfile
import unittest

from munificent.io import Emitter, open_file_gzip, open_file_normal


class TestFileOpeners(unittest.TestCase):

    def test_normal_opener(self):
        with tempfile.NamedTemporaryFile('a') as output_file:
            opener = open_file_normal(output_file.name)
            emitter = Emitter(opener)
            emitter.emit({'foo': 'bar', 'baz': 72})
            emitter.flush()

    def test_gzip_opener(self):
        with tempfile.NamedTemporaryFile('a') as output_file:
            opener = open_file_gzip(output_file.name)
            emitter = Emitter(opener)
            emitter.emit({'foo': 'bar', 'baz': 72})
            emitter.flush()
