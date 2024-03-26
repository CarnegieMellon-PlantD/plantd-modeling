#aws eks --region us-east-1 update-kubeconfig --name windtunnel-eks-GU7jql7j

# if false; then...
if false; then
    # Create the cluster
    

    kubectl port-forward svc/prometheus 9090:9090 -n plantd-operator-system --context=arn:aws:eks:us-east-1:591334395036:cluster/windtunnel-eks-GU7jql7j &
    kubectl proxy --context=arn:aws:eks:us-east-1:591334395036:cluster/windtunnel-eks-GU7jql7j &
    kubectl port-forward -n plantd-operator-system svc/plantd-studio-service 3000:80  --context=arn:aws:eks:us-east-1:591334395036:cluster/windtunnel-eks-GU7jql7j &
    kubectl port-forward --namespace opencost service/opencost 9003 --context=arn:aws:eks:us-east-1:591334395036:cluster/ubi-cluster &
    kubectl port-forward --namespace plantd-operator-system service/prometheus 9990:9090 --context=arn:aws:eks:us-east-1:591334395036:cluster/ubi-cluster &

fi



#export EXPERIMENT_NAMES="test-pipeline.gentel-rise-fall2,test-pipeline.murph-test-2"
#export EXPERIMENT_NAMES="test-pipeline.chris-test-2,test-pipeline.gentel-rise-fall2"
export REDIS_HOST="localhost"
export REDIS_PASSWORD=""
export PROMETHEUS_HOST="http://localhost:9090"
export PROMETHEUS_PASSWORD=""
export EXPERIMENTS=""
export LOADPATTERNS=""

# For local testing, not for production 
#export KUBERNETES_SERVICE_ADDRESS=https://kubernetes.default.svc
export KUBERNETES_SERVICE_ADDRESS=http://localhost:8001/
export KUBERNETES_GROUP=windtunnel.plantd.org
export CONTROLLER_VERSION=v1alpha1

export MODEL_TYPE="simple"
export FROM_CACHED="from_cached"

export COST_PROMETHEUS_ENDPONT="http://localhost:9990/api/v1/query"
export OPENCOST_ENDPOINT="http://localhost:9003/allocation"
export PIPELINE_LABEL_KEY=
export PIPELINE_LABEL_VALUE=

# ADVANCED_SIMULATION lowplus-good
export SCENARIO_NAME="default.sample-scenario"
export NETCOST_NAME="default.netcost"

export EXPERIMENT_NAMES="ubi-chris-test.ubi-chris-test-good-triangle-3" 
export TWIN_NAME="ubi-chris-test.chris-model-good-tri"
export TRAFFIC_MODEL_NAME="traffic-model-lowplus"
export SIM_NAME="test-lowplus-good-tri"
python dev-setup-advanced-build.py
source dev-env-build-test-lowplus-good-tri.env
python main.py sim_all $FROM_CACHED

# SIMULATION lowplus-bad
export EXPERIMENT_NAMES="ubi-chris-test.ubi-chris-test-bad-triangle-3" 
export TWIN_NAME="ubi-chris-test.chris-model-bad-tri"
export TRAFFIC_MODEL_NAME="traffic-model-lowplus"
export SIM_NAME="test-lowplus-bad-tri"
python dev-setup-build.py
source dev-env-build-test-lowplus-bad-tri.env
python main.py sim_all  $FROM_CACHED

# SIMULATION lowplus-fixed
export EXPERIMENT_NAMES="ubi-chris-test.ubi-chris-test-fixed-triangle-3" 
export TWIN_NAME="ubi-chris-test.chris-model-fixed-tri"
export TRAFFIC_MODEL_NAME="traffic-model-lowplus"
export SIM_NAME="test-lowplus-fixed-tri"
python dev-setup-build.py
source dev-env-build-test-lowplus-fixed-tri.env
python main.py sim_all $FROM_CACHED 


# SIMULATION nom-good
export EXPERIMENT_NAMES="ubi-chris-test.ubi-chris-test-good-triangle-3" 
export TWIN_NAME="ubi-chris-test.chris-model-good-tri"
export TRAFFIC_MODEL_NAME="traffic-model-nominal"
export SIM_NAME="test-nom-good-tri"
python dev-setup-build.py
source dev-env-build-test-nom-good-tri.env
python main.py sim_all  $FROM_CACHED



# SIMULATION nom-bad
export EXPERIMENT_NAMES="ubi-chris-test.ubi-chris-test-bad-triangle-3" 
export TWIN_NAME="ubi-chris-test.chris-model-bad-tri"
export TRAFFIC_MODEL_NAME="traffic-model-nominal"
export SIM_NAME="test-nom-bad-tri"
python dev-setup-build.py
source dev-env-build-test-nom-bad-tri.env
python main.py sim_all  $FROM_CACHED

# SIMULATION nom-fixed
export EXPERIMENT_NAMES="ubi-chris-test.ubi-chris-test-fixed-triangle-3" 
export TWIN_NAME="ubi-chris-test.chris-model-fixed-tri"
export TRAFFIC_MODEL_NAME="traffic-model-nominal"
export SIM_NAME="test-nom-fixed-tri"
python dev-setup-build.py
source dev-env-build-test-nom-fixed-tri.env
python main.py sim_all  $FROM_CACHED


# SIMULATION low-bad
export EXPERIMENT_NAMES="ubi-chris-test.ubi-chris-test-bad-triangle-3" 
export TWIN_NAME="ubi-chris-test.chris-model-bad-tri"
export TRAFFIC_MODEL_NAME="traffic-model-low"
export SIM_NAME="test-low-bad-tri"
python dev-setup-build.py
source dev-env-build-test-low-bad-tri.env
python main.py sim_all  $FROM_CACHED

# SIMULATION low-good
export EXPERIMENT_NAMES="ubi-chris-test.ubi-chris-test-good-triangle-3" 
export TWIN_NAME="ubi-chris-test.chris-model-good-tri"
export TRAFFIC_MODEL_NAME="traffic-model-low"
export SIM_NAME="test-low-good-tri"
python dev-setup-build.py
source dev-env-build-test-low-good-tri.env
python main.py sim_all  $FROM_CACHED

# SIMULATION low-fixed
export EXPERIMENT_NAMES="ubi-chris-test.ubi-chris-test-fixed-triangle-3" 
export TWIN_NAME="ubi-chris-test.chris-model-fixed-tri"
export TRAFFIC_MODEL_NAME="traffic-model-low"
export SIM_NAME="test-low-fixed-tri"
python dev-setup-build.py
source dev-env-build-test-low-fixed-tri.env
python main.py sim_all  $FROM_CACHED
