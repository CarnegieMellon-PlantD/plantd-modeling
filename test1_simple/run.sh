
# if false; then...
if false; then
    aws eks --region us-east-1 update-kubeconfig --name windtunnel-eks-GU7jql7j
    kubectl proxy --context=arn:aws:eks:us-east-1:591334395036:cluster/windtunnel-eks-GU7jql7j &
    kubectl port-forward -n plantd-operator-system svc/plantd-studio-service 3000:80  --context=arn:aws:eks:us-east-1:591334395036:cluster/windtunnel-eks-GU7jql7j &
    kubectl port-forward -n plantd-operator-system pod/opencost-757d5b9c8-7fvtq 9003  &
    kubectl port-forward -n plantd-operator-system pod/prometheus-prometheus-0 9090:9090 &
fi

export REDIS_HOST="localhost"
export REDIS_PASSWORD=""
export PROMETHEUS_HOST="http://localhost:9090"
export PROMETHEUS_PASSWORD=""
export PROMETHEUS_ENDPOINT=$PROMETHEUS_HOST"/api/v1/query"

# For local testing, not for production 
export KUBERNETES_SERVICE_ADDRESS=http://localhost:8001/
export KUBERNETES_GROUP=windtunnel.plantd.org
export CONTROLLER_VERSION=v1alpha1
export OPENCOST_ENDPOINT="http://localhost:9003/allocation"
export PIPELINE_LABEL_KEY=
export PIPELINE_LABEL_VALUE=

# SIM1: No scenario, just simple model built from experiment
export SCENARIO_NAME=
export NETCOST_NAME=
export MODEL_TYPE="simple"
#export FROM_CACHED="from_cached"
export FROM_CACHED=
export DATASET_METADATA="`cat test1_simple/dataset.json`"
export EXPERIMENT_NAMES=test-pipeline.sample-experiment
export EXPERIMENT_METADATA="`cat test1_simple/experiment.json`"
export LOAD_PATTERN_NAMES=test-pipeline.test-loadpattern
export LOAD_PATTERN_METADATA="`cat test1_simple/loadpattern.json`"
source test1_simple/traffic-model-nominal.env
export TWIN_NAME="test-pipeline.test-twin"
export SIM_NAME="test-pipeline.test-sim"

# Delete stuff that we're going to populate
redis-cli del plantd:trafficmodel_predictions:traffic-model-nominal
redis-cli del plantd:metrics:test-pipeline.sample-experiment
redis-cli del plantd:experiment_summary:test-pipeline.sample-experiment
redis-cli del plantd:twinmodel:test-pipeline.test-twin
redis-cli del plantd:simulation_traffic:test-pipeline.test-sim
redis-cli del plantd:simulation_summary:test-pipeline.test-sim

python main.py sim_all $FROM_CACHED

# Check things that should have been populated
echo "plantd:trafficmodel_predictions:traffic-model-nominal:" `redis-cli get plantd:trafficmodel_predictions:traffic-model-nominal | wc -l`
echo "plantd:metrics:test-pipeline.sample-experiment:" `redis-cli get plantd:metrics:test-pipeline.sample-experiment | wc -l`
echo "plantd:experiment_summary:test-pipeline.sample-experiment:" `redis-cli get plantd:experiment_summary:test-pipeline.sample-experiment | wc -l`
echo "plantd:twinmodel:test-pipeline.test-twin:" `redis-cli get plantd:twinmodel:test-pipeline.test-twin | wc -l`
echo "plantd:simulation_traffic:test-pipeline.test-sim:" `redis-cli get plantd:simulation_traffic:test-pipeline.test-sim | wc -l`
echo "plantd:simulation_summary:test-pipeline.test-sim:" `redis-cli get plantd:simulation_summary:test-pipeline.test-sim | wc -l`


# Note: writes to these REDIS keys:

#
# These are outputs the system will need to read.  In testing, it's useful to delete these
# before a run, to make sure they are being written correctly.  In production, these may
# be read by the studio to display results.
#
#   plantd:trafficmodel_predictions:traffic-model-nominal
#       - fleshes out traffic model: csv by year/month/day, data in column "hourly"
#   plantd:metrics:test-pipeline.sample-experiment
#       - CSV in quotes with metrics from experiment: time, then thru and latency for each phase
#   plantd:temp:experiment_summary:test-pipeline.sample-experiment
#       - JSON record with high level summary stats: records injected, total span, mean latency, throughput, total cost, cost per hour
#   plantd:twinmodel:test-pipeline.test-twin
#       - parameters of the digital twin
#   plantd:simulation_traffic:test-pipeline.test-sim
#       - traffic model and hourly results for the simulation
#   plantd:simulation_summary:test-pipeline.test-sim
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
#   plantd:cache:experiment_cr:test-pipeline.sample-experiment
#       - cache of the experiment CR's JSON dump, used for running offline
#   plantd:cache:experiment_loadpatterns:test-pipeline.sample-experiment
#       - cache of the load patterns used in the experiment, used for running offline
#
