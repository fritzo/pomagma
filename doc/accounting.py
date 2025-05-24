"""
Accounting computations to estimate costs of various algorithms.

References:
http://www.eecs.berkeley.edu/~rcs/research/interactive_latency.html
https://en.wikipedia.org/wiki/List_of_Intel_Xeon_microprocessors
http://www.ec2instances.info
https://cloud.google.com/compute/pricing#machinetype
https://cloud.google.com/compute/pricing#localssdpricing
http://www.intel.ie/content/dam/www/public/us/en/documents/\
product-specifications/ssd-dc-p3700-spec.pdf
http://www.storagereview.com/samsung_ssd_850_evo_ssd_review
"""

from parsable import parsable

KiB = 2.0**10
MiB = 2.0**20
GiB = 2.0**30
TiB = 2.0**40

ns = 1e-9
ms = 1e-6
us = 1e-3
sec = 1.0

MACHINES = {
    "toy": {
        "cpu_count": 16,
        "space": [
            {
                "type": "cache",
                "size": 20 * MiB,
                "latency": 4 * ns,
                "block": 64,
            },
            {
                "type": "memory",
                "size": 128 * GiB,
                "latency": 100 * ns,
                "bandwidth": (1 * MiB) / (15 * ns),
                "block": 64,
            },
            {
                "type": "ssd",
                "model": "intel.p3700",
                "size": 400 * GiB,
                "latency": 20 * us,
                "bandwidth": 2000 * MiB / sec,
                "block": 4096,
            },
            {
                "type": "ssd",
                "model": "samsung.evo-850",
                "size": 1 * TiB,
                "latency": 35 * us,
                "bandwidth": 520 * MiB / sec,
                "block": 4096,
            },
            {
                "type": "disk",
                "size": 1 * TiB,
                "latency": 4 * ms,
                "bandwidth": (1 * MiB) / (2 * ms),
                "block": 1 * MiB,
            },
        ],
    },
    "gce.n1-standard-32": {
        "cpu_count": 32,
        "space": [
            {
                "type": "cache",
                "size": 40 * MiB,
                "latency": 4 * ns,
                "block": 64,
            },
            {
                "type": "memory",
                "size": 120 * GiB,
                "latency": 100 * ns,
                "bandwidth": (1 * MiB) / (15 * us),
                "block": 64,
            },
            {
                "type": "ssd",
                "size": 750 * GiB,
                "latency": 16 * us,
                "bandwidth": (1 * MiB) / (200 * us),
                "block": 4096,
            },
            {
                "type": "disk",
                "size": 10 * TiB,
                "latency": 4 * ms,
                "bandwidth": (1 * MiB) / (2 * ms),
                "block": 1 * MiB,
            },
        ],
    },
    "ec2.c3.8xlarge": {
        "cpu_count": 32,
        "space": [
            {
                "type": "cache",
                "size": 40 * MiB,
                "latency": 4 * ns,
                "block": 64,
            },
            {
                "type": "memory",
                "size": 60 * GiB,
                "latency": 100 * ns,
                "bandwidth": (1 * MiB) / (15 * ns),
                "block": 64,
            },
            {
                "type": "ssd",
                "size": 640 * GiB,
                "latency": 16 * us,
                "bandwidth": (1 * MiB) / (200 * us),
                "block": 4096,
            },
            {
                "type": "disk",
                "size": 10 * TiB,
                "latency": 4 * ms,
                "bandwidth": (1 * MiB) / (2 * ms),
                "block": 1 * MiB,
            },
        ],
    },
}


@parsable
def infer_cost():
    """
    Calculate cost of inference for various machines.
    """
    ob_counts = [1e4, 1e5, 1e6]
    for ob_count in ob_counts:
        raise NotImplementedError("TODO")


if __name__ == "__main__":
    parsable()
