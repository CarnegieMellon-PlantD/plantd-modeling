from plantd_modeling import metrics
import sys

metrics.redis.dumpall("plantd:", sys.argv[1])
