# Run the experiment this test relies on

kubectl create -f pipeline.yaml
while ! kubectl get pipeline sample-pipeline -n test1; do sleep 1; done
kubectl create -f schema.yaml
while ! kubectl get schema product -n test1; do sleep 1; done
while ! kubectl get schema warehouse -n test1; do sleep 1; done
while ! kubectl get schema supplier -n test1; do sleep 1; done
kubectl create -f dataset.yaml
kubectl create -f loadpattern.yaml
sleep 120
kubectl create -f experiment.yaml

echo After running this, wait until
echo  kubectl get experiments -n test1 shows that the experiment has completed.
#
# Then you can run test1_simple/run.sh
# with FROM_CACHED="from_cached" commented out.
# 
# After that, re-add that line, and you can run this repeatedly from cache, without needing a network connection
# 
