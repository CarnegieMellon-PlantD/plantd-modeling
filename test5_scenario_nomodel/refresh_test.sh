# Choose an experiment that has already run in the server
export EXPERIMENT_NAMES=
export SCENARIO_NAME=test-pipeline.sa-scenario-min
export NETCOSTS_NAME=test-pipeline.sa-netcost
export TESTDIR=test5_scenario_nomodel

# e2e-sim-schemaaware-1
# e2e-test3-schemaaware DT
#     ds: e2e-test3-schemaaware-bias-2
# sa-netcost
# e2e-scenario-schemaaware

# Ensure thanos and opencost are set up
kubectl port-forward -n plantd-operator-system svc/plantd-thanos-querier 9090:9090 &
kubectl port-forward -n plantd-operator-system svc/plantd-opencost 9003:9003 &
echo "Ensuring redis is up"
redis-cli ping

# Download the json files where test.env will see them
kubectl get experiment -A -o json > $TESTDIR/experiment.json
kubectl get dataset -A -o json > $TESTDIR/dataset.json
kubectl get loadpattern -A -o json > $TESTDIR/loadpattern.json
kubectl get scenario ${SCENARIO_NAME#*.} -n ${SCENARIO_NAME%%.*} -o json > $TESTDIR/scenario.json
kubectl get netcosts ${NETCOSTS_NAME#*.} -n ${NETCOSTS_NAME%%.*} -o json > $TESTDIR/netcosts.json

# Set other variables
export REDIS_HOST="localhost"
export REDIS_PORT="6379"
export REDIS_PASSWORD=""
export PROMETHEUS_HOST="http://localhost:9090"
export PROMETHEUS_PASSWORD=""
export PROMETHEUS_ENDPOINT=$PROMETHEUS_HOST"/api/v1/query"
export OPENCOST_ENDPOINT="http://localhost:9003/allocation"
export MODEL_TYPE="simple"
export DIGITAL_TWIN_TYPE="schemaaware"
export DATASET_JSON="`cat $TESTDIR/dataset.json`"
export EXPERIMENT_JSON="`cat $TESTDIR/experiment.json`"
export LOAD_PATTERN_JSON="`cat $TESTDIR/loadpattern.json`"
export NETCOSTS="`cat $TESTDIR/netcosts.json`"
export SCENARIO="`cat $TESTDIR/scenario.json`"
source $TESTDIR/traffic-model-nominal.env
export TWIN_NAME="test-pipeline.test5-twin"
export SIM_NAME="test-pipeline.test5-sim"

# Delete all plantd redis keys
redis-cli keys "plantd:*" | xargs redis-cli del

# Run the code
python main.py sim_all $FROM_CACHED

# copy redis keys into a target_redis
mkdir -p $TESTDIR/target-redis

# Dump all redis keys to files
python redis_dump.py $TESTDIR/target-redis.json