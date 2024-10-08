# Choose an experiment that has already run in the server
export EXPERIMENT_NAMES=test-pipeline.sample-experiment
export TESTDIR=test1_simple

# Ensure thanos and opencost are set up
kubectl port-forward -n plantd-operator-system svc/plantd-thanos-querier 9090:9090 &
kubectl port-forward -n plantd-operator-system svc/plantd-opencost 9003:9003 &
echo "Ensuring redis is up"
redis-cli ping

# Download the json files where test.env will see them
kubectl get experiment -A -o json > $TESTDIR/experiment.json
kubectl get dataset -A -o json > $TESTDIR/dataset.json
kubectl get loadpattern -A -o json > $TESTDIR/loadpattern.json

# Set other variables
export REDIS_HOST="localhost"
export REDIS_PORT="6379"
export REDIS_PASSWORD=""
export PROMETHEUS_HOST="http://localhost:9090"
export PROMETHEUS_PASSWORD=""
export PROMETHEUS_ENDPOINT=$PROMETHEUS_HOST"/api/v1/query"
export OPENCOST_ENDPOINT="http://localhost:9003/allocation"
export SCENARIO_NAME=
export MODEL_TYPE="simple"
export DIGITAL_TWIN_TYPE="regular"
export DATASET_JSON="`cat $TESTDIR/dataset.json`"
export EXPERIMENT_JSON="`cat $TESTDIR/experiment.json`"
export LOAD_PATTERN_JSON="`cat $TESTDIR/loadpattern.json`"
source $TESTDIR/traffic-model-nominal.env
export TWIN_NAME="test-pipeline.test1-twin"
export SIM_NAME="test-pipeline.test1-sim"

# Delete all plantd redis keys
redis-cli keys "plantd:*" | xargs redis-cli del

# Run the code
python main.py sim_all $FROM_CACHED

# copy redis keys into a target_redis
mkdir -p $TESTDIR/target-redis

# Dump all redis keys to files
python redis_dump.py $TESTDIR/target-redis.json