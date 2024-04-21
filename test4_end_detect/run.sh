

export PROMETHEUS_HOST="http://localhost:9090"
export PROMETHEUS_PASSWORD=""
export PROMETHEUS_ENDPOINT=$PROMETHEUS_HOST"/api/v1/query"

#export FROM_CACHED="from_cached"
export FROM_CACHED=

# if not cached, then load test1_simple/experiment.json with real data from k8s
# if cached, then load test1_simple/experiment.json with fake data
#
#if [ -z "$FROM_CACHED" ]; then
#    echo "REALOADING EXPERIMENT INFO FROM KUBERNETES"
#    kubectl get experiment -A -o json > test4_end_detect/experiment.json
#fi

# test4: end detection
export EXPERIMENT_NAMES=test-pipeline.test3w-experiment
export EXPERIMENT_JSON="`cat test4_end_detect/experiment.json`"
export DEBOUNCE_PERIOD=30
export QUERY_WINDOW=90
export POD_DETATCH_ADJUSTMENT=60

python end_detect.py $FROM_CACHED

