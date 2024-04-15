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


#TO DO:
#- set up four scripts:
#    0. No scenario or netcost, simple simulation.  "no-scenario-no-netcost-simple"
#    1. Scenario and netcost.  Output should be new style sim, AUGMENTING old style, along with netcost data    "with-scenario-with-netcost"
#    2. No scenario or netcost.  Old style simulation.   "no-scenario-no-netcost"
#    3. Scenario and no netcost. Output should AUGMENT old style sim     "with-scenario-no-netcost"
#    4. No scenario and netcost.  Output should be old style sim and netcost data        "no-scenario-with-netcost"


export REDIS_HOST="localhost"
export REDIS_PASSWORD=""
export PROMETHEUS_HOST="http://localhost:9090"
export PROMETHEUS_PASSWORD=""
export PROMETHEUS_ENDPOINT=$PROMETHEUS_HOST "/api/v1/query"

# For local testing, not for production 
export KUBERNETES_SERVICE_ADDRESS=http://localhost:8001/
export KUBERNETES_GROUP=windtunnel.plantd.org
export CONTROLLER_VERSION=v1alpha1
export OPENCOST_ENDPOINT="http://localhost:9003/allocation"
export PIPELINE_LABEL_KEY=
export PIPELINE_LABEL_VALUE=

# SIM1: "with-scenario-with-netcost"
export SCENARIO_NAME="test-pipeline.sample-scenario"
export NETCOST_NAME="test-pipeline.sample-netcost"

export MODEL_TYPE="quickscaling"
export FROM_CACHED="from_cached"
export EXPERIMENT_NAMES="test-pipeline.sample-scenario-experiment-pure-product,test-pipeline.sample-scenario-experiment-pure-supplier,test-pipeline.sample-scenario-experiment-pure-warehouse" 
source test-pipeline.sample-scenario-experiments.env
source test-pipeline.sample-scenario-loadpatterns.env
source traffic-model-nominal.env
export TWIN_NAME="test-pipeline.with-scenario-with-netcost"
export SIM_NAME="test-with-scenario-with-netcost"
python main.py sim_all $FROM_CACHED

exit 


# SIM0: "no-scenario-no-netcost-simple"
export SCENARIO_NAME=
export NETCOST_NAME=
export MODEL_TYPE="simple"
export FROM_CACHED="from_cached"
source experiment_ubi_chris_test_good_triangle_3.env
source loadpattern_triangle_40.env
source traffic-model-nominal.env
export TWIN_NAME="ubi-chris-test.no-scenario-no-netcost-simple"
export SIM_NAME="test-no-scenario-no-netcost-simple"
python main.py sim_all $FROM_CACHED

# SIM4: "no-scenario-no-netcost"
export SCENARIO_NAME=   #"default.sample-scenario"
export NETCOST_NAME=    #"default.netcost"
export MODEL_TYPE="quickscaling"
export FROM_CACHED="from_cached"
source experiment_ubi_chris_test_good_triangle_3.env
source loadpattern_triangle_40.env
source traffic-model-nominal.env
export TWIN_NAME="ubi-chris-test.no-scenario-with-netcost"
export SIM_NAME="test-no-scenario-with-netcost"
python main.py sim_all $FROM_CACHED





echo "BETTER NOT RUN"

# SIM2: "no-scenario-no-netcost"
export SCENARIO_NAME=   #"default.sample-scenario"
export NETCOST_NAME=    #"default.netcost"

export MODEL_TYPE="quickscaling"
export FROM_CACHED="from_cached"
export EXPERIMENT_NAMES="ubi-chris-test.ubi-chris-test-good-triangle-3" 
export TWIN_NAME="ubi-chris-test.no-scenario-no-netcost"
export TRAFFIC_MODEL_NAME="traffic-model-lowplus"
export EXPERIMENT_METADATA='{"apiVersion": "windtunnel.plantd.org/v1alpha1", "items": [{"apiVersion": "windtunnel.plantd.org/v1alpha1", "kind": "Experiment", "metadata": {"creationTimestamp": "2023-11-22T14:36:13Z", "generation": 1, "managedFields": [{"apiVersion": "windtunnel.plantd.org/v1alpha1", "fieldsType": "FieldsV1", "fieldsV1": {"f:spec": {".": {}, "f:loadPatterns": {}, "f:pipelineRef": {}}}, "manager": "Go-http-client", "operation": "Update", "time": "2023-11-22T14:36:13Z"}, {"apiVersion": "windtunnel.plantd.org/v1alpha1", "fieldsType": "FieldsV1", "fieldsV1": {"f:status": {".": {}, "f:cloudVendor": {}, "f:duration": {".": {}, "f:input-endpoint": {}}, "f:enableCostCalculation": {}, "f:experimentState": {}, "f:protocols": {".": {}, "f:input-endpoint": {}}, "f:startTime": {}}}, "manager": "Go-http-client", "operation": "Update", "subresource": "status", "time": "2023-11-22T14:38:47Z"}], "name": "ubi-chris-test-good-triangle-2", "namespace": "ubi-chris-test", "resourceVersion": "68476175", "uid": "b354d68e-b20a-4ed0-9be9-905fa5c983e3"}, "spec": {"loadPatterns": [{"endpointName": "input-endpoint", "loadPatternRef": {"name": "triangle-40", "namespace": "ubi-chris-test"}}], "pipelineRef": {"name": "pipeline-good-8", "namespace": "ubi-chris-test"}}, "status": {"cloudVendor": "aws", "duration": {"input-endpoint": "2m0s"}, "enableCostCalculation": true, "experimentState": "Finished", "protocols": {"input-endpoint": "http.withDataSet"}, "startTime": "2023-11-22T14:36:31Z"}}], "kind": "ExperimentList", "metadata": {"continue": "", "resourceVersion": "68621526"}}'
export LOAD_PATTERN_METADATA='{"items": [{"apiVersion": "windtunnel.plantd.org/v1alpha1", "kind": "LoadPattern", "metadata": {"creationTimestamp": "2023-11-19T19:22:57Z", "generation": 1, "managedFields": [{"apiVersion": "windtunnel.plantd.org/v1alpha1", "fieldsType": "FieldsV1", "fieldsV1": {"f:spec": {".": {}, "f:maxVUs": {}, "f:preAllocatedVUs": {}, "f:stages": {}, "f:startRate": {}, "f:timeUnit": {}}}, "manager": "Go-http-client", "operation": "Update", "time": "2023-11-19T19:22:57Z"}], "name": "triangle-40", "namespace": "ubi-chris-test", "resourceVersion": "67199824", "uid": "5e086238-d9c8-4e82-be59-d353c32a4685"}, "spec": {"maxVUs": 100, "preAllocatedVUs": 30, "stages": [{"duration": "120s", "target": 40}], "startRate": 0, "timeUnit": "1s"}}]}'
export SIM_NAME="test-no-scenario-no-netcost"
python main.py sim_all $FROM_CACHED

# SIM3: "no-scenario-no-netcost"
export SCENARIO_NAME=   #"default.sample-scenario"
export NETCOST_NAME=    #"default.netcost"

export EXPERIMENT_NAMES="ubi-chris-test.ubi-chris-test-good-triangle-3" 
export TWIN_NAME="ubi-chris-test.with-scenario-no-netcost"
export TRAFFIC_MODEL_NAME="traffic-model-lowplus"
export SIM_NAME="test-with-scenario-no-netcost"
python dev-setup-advanced-build.py
source dev-env-build-with-scenario-no-netcost.env
python main.py sim_all $FROM_CACHED

