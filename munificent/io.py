import gzip
import json


def open_file_normal(path):
    return lambda mode: open(path, mode)


def open_file_gzip(path):
    return lambda mode: gzip.open(path, mode)


class Emitter(object):

    def __init__(self, file_opener):
        self._open_file = file_opener

    def emit(self, record):
        f = self._output_handle
        f.write(json.dumps(record, ensure_ascii=False).encode('utf-8'))
        f.write(b'\n')

    @property
    def _output_handle(self):
        if not hasattr(self, '_output_handle_'):
            self._output_handle_ = self._open_file('ab')
        return self._output_handle_

    def flush(self):
        '''
        Higher level flush that closes and resets the internal output handle
        '''
        output_handle = getattr(self, '_output_handle_', None)
        if output_handle:
            if not output_handle.closed:
                output_handle.flush()
                output_handle.close()
            del self._output_handle_

    def __del__(self):
        self.flush()
