from plantd_modeling import metrics
import sys

metrics.redis.loadall("plantd:cache:", sys.argv[1])
