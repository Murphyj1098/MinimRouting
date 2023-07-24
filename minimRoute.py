#!/usr/bin/env python3

import os
import sys

from argparse import ArgumentParser
from pyroute2 import IPRoute

# Subnets for each link
SRC_NET  = "10.0.0.0/24"
AB_NET   = "10.1.0.0/24"
AC_NET   = "10.3.0.0/24"
BC_NET   = "10.2.0.0/24"
LTU_NET  = "10.5.0.0/24"
WIFI_NET = "10.100.0.0/24"

# These get set based on whether this software is running at Pole A or Pole C
PATH_OPTION_1 = "" # One hop
PATH_OPTION_2 = "" # Two hop


def initialize(mode):
    global PATH_OPTION_1
    global PATH_OPTION_2

    ipr = IPRoute()

    if(mode == 0):
        # Init on Pole A Router
        PATH_OPTION_1 = "10.3.0.4"
        PATH_OPTION_2 = "10.1.0.4"

        # (Try to) delete existing route(s)
        delRoute(LTU_NET)
        delRoute(WIFI_NET)

        # Special case for non-split routing
        if (percent == 0 or percent == 100):
            # Add route without multipath
            routeGW = PATH_OPTION_1 if args.percent == 0 else PATH_OPTION_2
            ipr.route("add", dst=LTU_NET, gateway=routeGW)
            ipr.route("add", dst=WIFI_NET, gateway=routeGW)

    elif(mode == 1):
        # Init on Pole C Router
        PATH_OPTION_1 = "10.3.0.1"
        PATH_OPTION_2 = "10.2.0.1"

        # (Try to) delete existing route(s)
        delRoute(SRC_NET)

        # Special case for non-split routing
        if (percent == 0 or percent == 100):
            routeGW = PATH_OPTION_1 if percent == 0 else PATH_OPTION_2
            ipr.route("add", dst=SRC_NET, gateway=routeGW)

    ipr.close()


def delRoute(dstNet):
    with IPRoute() as ipr:
        try:
            ipr.route("del", dst=dstNet)
        except:
            print("Route to {} did not exist", dstNet)


def chgRoute(dstNET, weightLong):
    with IPRoute() as ipr:
        ipr.route(
            "add",
            dst=dstNET,
            multipath=[
                {"gateway": PATH_OPTION_1, "hops": ((100-weightLong)-1)}, # Hop = Weight - 1
                {"gateway": PATH_OPTION_2, "hops": (weightLong-1)}
            ]
        )


# 1. Assume default is to send all traffic the shortest path (AC link)
# 2. Provide a percentage as an argument for the amount of traffic that should
#    take the longer link (AB->BC) instead
if __name__ == '__main__':
    if not (os.geteuid() == 0):
        raise Exception("Need to run as root")

    parser = ArgumentParser()

    parser.add_argument('--delete', action='store_true')

    parser.add_argument('-r', '--router',
                        choices=('A', 'C'),
                        nargs='?',
                        help="Set the router this software is running on",
                        required=True)

    parser.add_argument('-p', '--percent',
                        choices=range(0,101,1),
                        default=0, # Default to all traffic on short route
                        type=int,
                        help="Set the percentage of traffic taking the longer route")

    args = parser.parse_args()

    percent = args.percent
    router = args.router

    # Clean up mode
    if(args.delete):
        delRoute(LTU_NET)
        delRoute(WIFI_NET)
        delRoute(SRC_NET)
        sys.exit(0)

    if(router == 'A'):
        initialize(0)
    else: # router == 'C'
        initialize(1)

    # Early exit if traffic is not split
    if(percent == 0 or percent == 100):
        sys.exit(0)

    # Multipath Routing
    if(router == 'A'):
        chgRoute(LTU_NET, percent)
        chgRoute(WIFI_NET, percent)
    else: # router == 'C'
        chgRoute(SRC_NET, percent)
