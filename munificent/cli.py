import argparse
import logging
import os
import signal
import sys

from munificent import __version__, db
import munificent.collect
from munificent.collect import Collector
from munificent.io import Emitter, open_file_gzip, open_file_normal
from munificent.nextbus import NextBusAPI

LOG = logging.getLogger(__name__)
Session = db.configured_session()


def build_parser():
    parser = argparse.ArgumentParser(
        prog='munificent',
        description='Tools for collecting real-time data from the NextBus API',
    )

    subparsers = parser.add_subparsers()

    # version
    version = subparsers.add_parser('version')
    version.set_defaults(func=print_version_info)

    # targets
    targets = subparsers.add_parser('targets')
    targets.set_defaults(func=list_targets)

    # collect
    collect = subparsers.add_parser('collect')
    collect.add_argument(
        '--period',
        default=60.0,
        type=float,
        help=''''
        Period of time between repeated queries, in seconds.  All queries in
        the specified query sets will be run over this time period.
        '''
    )
    collect.add_argument(
        '--gzip',
        action='store_true',
        default=False,
        help='Whether to apply gzip compression to the output file(s)',
    )
    collect.add_argument(
        '--target',
        nargs='+',
        choices=COLLECTION_TARGETS,
        help='''
        Named collection configuration to run. Use 'targets' subcommand to see
        a list of options.
        '''
    )
    collect.add_argument(
        'output_path',
    )
    collect.add_argument(
        '--log-file',
        help='Output file to write logs to',
    )
    collect.add_argument(
        '--log-level',
    )
    collect.set_defaults(func=run_collection)

    return parser

def print_version_info(args):
    print(__version__)


def list_targets(args):
    print("Collection targets:")
    print("-------------------")
    for target in COLLECTION_TARGETS:
        print("+ {}".format(target))


COLLECTION_TARGETS = [
    'sfmuni-train-predictions',
    'sfmuni-train-locations',
    ]


def get_target_probes(target):
    api = NextBusAPI()
    if target == 'sfmuni-train-predictions':
        return munificent.collect.get_muni_train_prediction_probes(api)
    if target == 'sfmuni-train-locations':
        return munificent.collect.get_muni_train_location_probes(api)
    raise ValueError("Unrecognized collection target: {}".format(target))


def get_file_opener(args):
    output_path = args.output_path
    opener = open_file_normal
    if args.gzip:
        opener = open_file_gzip
    return opener(output_path)


def run_collection(args):
    probes = [p for t in args.target for p in get_target_probes(t)]

    opener = get_file_opener(args)
    emitter = Emitter(opener)
    collector = Collector(probes, emitter=emitter, period=args.period)

    def hup(*args):
        LOG.info("Received HUP signal, flushing emitter")
        emitter.flush()

    signal.signal(signal.SIGHUP, hup)

    try:
        LOG.info("Running collection on PID: {}".format(os.getpid()))
        collector.run()
    finally:
        emitter.flush()


def main(raw_args=None):
    raw_args = raw_args or sys.argv[1:]
    parser = build_parser()
    args = parser.parse_args(raw_args)
    args.func(args)


if __name__ == '__main__':
    main()
