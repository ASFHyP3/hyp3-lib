"""Read OPOD State Vector"""

import argparse
import logging
import os

from hyp3lib.sentinel1.orbits import verify_opod


def main():
    """Main entrypoint"""

    parser = argparse.ArgumentParser(
        prog=os.path.basename(__file__),
        description=__doc__,
    )
    parser.add_argument("OPODfile", help="S1 OPOD file")
    args = parser.parse_args()

    log_file = "OPOD_{}.log".format(os.getpid())
    logging.basicConfig(filename=log_file, format='%(asctime)s - %(levelname)s - %(message)s',
                        datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.DEBUG)
    logging.getLogger().addHandler(logging.StreamHandler())
    logging.info("Starting run")

    verify_opod(args.OPODfile)


if __name__ == '__main__':
    main()
