# Experiment name previously set up in example files
export EXPERIMENT_NAMES=test-pipeline.e2e-test3-schemaaware-bias-1,test-pipeline.e2e-test3-schemaaware-bias-2,test-pipeline.e2e-test3-schemaaware-bias-3
export REDIS_HOST="localhost"
export REDIS_PORT="6379"
export REDIS_PASSWORD=""
export TESTDIR=test3_scenario

# Prometheus and opencost need not be port forwarded
# (Better if they are not, in case a bug in the test consults them)

# Redis local should be up, and loaded with cache values only
redis-cli ping
redis-cli flushall
python redis_load.py $TESTDIR/target-redis.json


# SIM1: No scenario, just simple model built from experiment
export PROMETHEUS_HOST="http://localhost:9090"
export PROMETHEUS_PASSWORD=""
export PROMETHEUS_ENDPOINT=$PROMETHEUS_HOST"/api/v1/query"
export OPENCOST_ENDPOINT="http://localhost:9003/allocation"
export NETCOSTS="`cat $TESTDIR/netcosts.json`"
export SCENARIO="`cat $TESTDIR/scenario.json`"
export MODEL_TYPE="simple"
export DIGITAL_TWIN_TYPE="schemaaware"
export DATASET_JSON="`cat $TESTDIR/dataset.json`"
export EXPERIMENT_JSON="`cat $TESTDIR/experiment.json`"
export LOAD_PATTERN_JSON="`cat $TESTDIR/loadpattern.json`"
source $TESTDIR/traffic-model-nominal.env
export TWIN_NAME="test-pipeline.test3-twin"
export SIM_NAME="test-pipeline.test3-sim"

python main.py sim_all from_cached

# Check things that should have been populated
echo "plantd:trafficmodel_predictions:traffic-model-nominal:" `redis-cli get plantd:trafficmodel_predictions:traffic-model-nominal | wc -l`
echo "plantd:metrics:$EXPERIMENT_NAMES:" `redis-cli get plantd:metrics:$EXPERIMENT_NAMES | wc -l`
echo "plantd:experiment_summary:$EXPERIMENT_NAMES:" `redis-cli get plantd:experiment_summary:$EXPERIMENT_NAMES | wc -l`
echo "plantd:twinmodel:test-pipeline.test3-twin:" `redis-cli get plantd:twinmodel:test-pipeline.test3-twin | wc -l`
echo "plantd:simulation_traffic:test-pipeline.test3-sim:" `redis-cli get plantd:simulation_traffic:test-pipeline.test3-sim | wc -l`
echo "plantd:simulation_summary:test-pipeline.test3-sim:" `redis-cli get plantd:simulation_summary:test-pipeline.test3-sim | wc -l`
echo "plantd:simulation_monthly:test-pipeline.test3-sim:" `redis-cli get plantd:simulation_monthly:test-pipeline.test3-sim | wc -l`


