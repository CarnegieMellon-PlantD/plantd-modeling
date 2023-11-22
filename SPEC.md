# Using these modeling functions

This repository contains a convenience function that does data analysis, or experiment end detection, on PlantD's measured data

Set up the following environment variables:

    - TWIN_NAME
        - namespace.name of the model to be constructed from the experiments
    - MODEL_TYPE
        - simple, autoscaling, or quickscaling
    - SIM_NAME
        - A name for the simulation to be run 
    - TRAFFIC_MODEL_NAME
        - The traffic model to use.  See samples directory for an example. 
        - This will be looked up from redis key `plantd:trafficmodel_params:$TRAFFIC_MODEL`
    - REDIS_HOST
    - REDIS_PASSWORD
    - PROMETHEUS_HOST
    - PROMETHEUS_PASSWORD
        - if missing, no password is sent
    - COST_PROMETHEUS_ENDPOINT  
        - This will eventually go away, when the opencost prometheus is merged with the windtunnel prometheus
    - OPENCOST_ENDPOINT
        - Endpoint of the opencost service
    - PIPELINE_LABEL_KEY
    - PIPELINE_LABEL_VALUE
        - Used by opencost.  Optional.
    - EXPERIMENT_NAMES
        - comma-separated list of namespace.name of each experiment to use when constructing a digital twin
    - EXPERIMENTS
        - json dictionary, where the keys are the names of experiments in the form namespace.name, and the values are the records containing describe information for all experiments 
        - Note that experiments not listed in EXPERIMENT_NAMES will be omitted from analysis (so it's OK to dump every experiment here; they'll just be ignored)
        - See samples directory for an example
    - LOADPATTERNS
        - json dictionary of all load patterns mentioned in the EXPERIMENTS. 
        - Note that load patterns not listed in EXPERIMENTs will be ignored (so it's OK to dump all load patterns here; they'll just be ignored)
        - See samples directory for an example

2. *sim_all* To build a model from a set of experiments, simulate the traffic model, and run the twin on the model, call `python make.py sim_all`
    - This writes the following to redis:
        - `plantd:trafficmodel_params:$TRAFFIC_MODEL`  copy of the traffic model passed in
        - `plantd:trafficmodel_prediction:$TRAFFIC_MODEL`
        - `plantd:twinmodel:$TWIN_NAME`  Parameters describing the digital twin created from the experiments
        - `plantd:experiment_cost:$EXPERIMENT_NAME`  Cache of cost logs retrieved from opencost
        - `plantd:metrics:$EXPERIMENT_NAME`  This will be a cache of data scraped from prometheus for each experiment (since prometheus data disappears after a few days)
        - `plantd:simulation_traffic:$SIM_NAME` contains a CSV string with a timeseries of all simulation results
        - `plantd:simulation_summary:$SIM_NAME` Contains summary of simulation data over the whole simluation year
    - If the experiment data in prometheus has already aged out (e.g. more than 3 days old), but the experiment has previously been used in a
        simulation, then the data can be used from the cache by calling `python make.py sim_all from_cached`.  (However, if you don't use from_cached, and it's
        aged out, it'll write 0's to the cache, and the data will be lost.  So we really need a better technique here.)
    - If the simulation succeeds, the script will print "SIMULATION_STATUS: Success"
    - If the simulation fails, the script will print "SIMULATION_STATUS: Failure" and "ERROR_REASON: <explanation>" 



3. *end_detector* To determine when a pipeline may have finished processing the data that was passed in in an experiment, call `python make.py end_detector`
    - not implemented yet
    - EXPERIMENTS should contain just one experiment 
    - This writes the end time to redis, with key `plantd:experiment:namespace.name:detected_end`

