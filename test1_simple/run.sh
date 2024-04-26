# Experiment name previously set up in example files
export EXPERIMENT_NAMES=test-pipeline.sample-experiment
export REDIS_HOST="localhost"
export REDIS_PORT="6379"
export REDIS_PASSWORD=""

# Prometheus and opencost need not be port forwarded
# (Better if they are not, in case a bug in the test consults them)

# Redis local should be up, and loaded with cache values only
redis-cli ping
redis-cli flushall
python redis_load.py test1_simple/target-redis.json


# SIM1: No scenario, just simple model built from experiment
export PROMETHEUS_HOST="http://localhost:9090"
export PROMETHEUS_PASSWORD=""
export PROMETHEUS_ENDPOINT=$PROMETHEUS_HOST"/api/v1/query"
export OPENCOST_ENDPOINT="http://localhost:9003/allocation"
export PIPELINE_LABEL_KEYS=pipeline-infrastructure
export PIPELINE_LABEL_VALUES=testpipeline
export SCENARIO_NAME=
export NETCOST_NAME=
export MODEL_TYPE="simple"
export DIGITAL_TWIN_TYPE="regular"
export DATASET_JSON="`cat test1_simple/dataset.json`"
export EXPERIMENT_JSON="`cat test1_simple/experiment.json`"
export LOAD_PATTERN_NAMES=test-pipeline.test1-loadpattern
export LOAD_PATTERN_JSON="`cat test1_simple/loadpattern.json`"
source test1_simple/traffic-model-nominal.env
export TWIN_NAME="test-pipeline.test1-twin"
export SIM_NAME="test-pipeline.test1-sim"

python main.py sim_all from_cached

# Check things that should have been populated
echo "plantd:trafficmodel_predictions:traffic-model-nominal:" `redis-cli get plantd:trafficmodel_predictions:traffic-model-nominal | wc -l`
echo "plantd:metrics:$EXPERIMENT_NAMES:" `redis-cli get plantd:metrics:$EXPERIMENT_NAMES | wc -l`
echo "plantd:experiment_summary:$EXPERIMENT_NAMES:" `redis-cli get plantd:experiment_summary:$EXPERIMENT_NAMES | wc -l`
echo "plantd:twinmodel:test-pipeline.test1-twin:" `redis-cli get plantd:twinmodel:test-pipeline.test1-twin | wc -l`
echo "plantd:simulation_traffic:test-pipeline.test1-sim:" `redis-cli get plantd:simulation_traffic:test-pipeline.test1-sim | wc -l`
echo "plantd:simulation_summary:test-pipeline.test1-sim:" `redis-cli get plantd:simulation_summary:test-pipeline.test1-sim | wc -l`
echo "plantd:simulation_monthly:test-pipeline.test1-sim:" `redis-cli get plantd:simulation_monthly:test-pipeline.test1-sim | wc -l`


# Note: writes to these REDIS keys:

#
# These are outputs the system will need to read.  In testing, it's useful to delete these
# before a run, to make sure they are being written correctly.  In production, these may
# be read by the studio to display results.
#
#   plantd:trafficmodel_predictions:traffic-model-nominal
#       - fleshes out traffic model: csv by year/month/day, data in column "hourly"
#   plantd:metrics:test1.sample-experiment
#       - CSV in quotes with metrics from experiment: time, then thru and latency for each phase
#   plantd:temp:experiment_summary:test1.sample-experiment
#       - JSON record with high level summary stats: records injected, total span, mean latency, throughput, total cost, cost per hour
#   plantd:twinmodel:test1.test-twin
#       - parameters of the digital twin
#   plantd:simulation_traffic:test1.test-sim
#       - traffic model and hourly results for the simulation
#   plantd:simulation_summary:test1.test-sim
#       - simulation results summarized
#
#
# These are cached data, used for dev -- run once, then read from these by passing
# in from_cached flag.  Not used in production.
#
#   plantd:cache:opencost_data:{'window....
#       - Opencost data collected from this experiment; name is unweildy because using params for caching
#       - result is just a cache of what's returned from a prometheus call.
#   plantd:cache:prometheus_cost_data:kubecost_cluster_management_cost
#   plantd:cache:prometheus_cost_data:node_cpu_hourly_cost
#   plantd:cache:prometheus_cost_data:node_ram_hourly_cost
#       - cache of raw prometheus result, used for running offline
#   plantd:cache:experiment_cr:test1.sample-experiment
#       - cache of the experiment CR's JSON dump, used for running offline
#   plantd:cache:experiment_loadpatterns:test1.sample-experiment
#       - cache of the load patterns used in the experiment, used for running offline
#
