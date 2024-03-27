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
export SIM_NAME="test-advanced"
python dev-setup-advanced-build.py
source dev-env-build-sample-scenario.env
python main.py advanced_net_cost_only $FROM_CACHED
