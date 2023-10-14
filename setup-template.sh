kubectl port-forward svc/prometheus 9090:9090 -n plantd-operator-system &
kubectl proxy &
export EXPERIMENT_NAMES="test-pipeline.gentel-rise-fall2,test-pipeline.murph-test-2"
export TWIN_NAME="test-pipeline.chris-model"
export REDIS_HOST=""
export REDIS_PASSWORD=""
export PROMETHEUS_HOST="http://localhost:9090"
export PROMETHEUS_PASSWORD=""
export KUBERNETES_SERVICE_ADDRESS=http://localhost:8001/
export GROUP=windtunnel.plantd.org
export CONTROLLER_VERSION=v1alpha1
