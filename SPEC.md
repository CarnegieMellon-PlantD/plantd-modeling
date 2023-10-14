# Using these modeling functions

This repository contains several convenience functions that do data analysis on PlantD's measured data

1. Set up the following environment variables
    - EXPERIMENT_NAMES
        - comma-separated list of experiments, as namespace.name
    - TWIN_NAME
        - namespace.name of the model to be constructed from the experiments
    - REDIS_HOST
    - REDIS_PASSWORD
    - PROMETHEUS_HOST
    - PROMETHEUS_PASSWORD
        - if missing, no password is sent
    - KUBERNETES_SERVICE_ADDRESS
        - if missing default is https://kubernetes.default.svc
    - GROUP
        - use windtunnel.plantd.org
    - CONTROLLER_VERSION
        - currently v1alpha1

2. To build a model from a set of experiments, call `python make.py build`
    - This writes model parameters to redis, with key `twin:$TWIN_NAME:model_params`

3. To determine when a pipeline may have finished processing the data that was passed in in an experiment, call `python make.py end_detector`
    - EXPERIMENT_NAMES should contain just one experiment namespace.name
    - TWIN_NAME is ignored for this call
    - This writes the end time to redis, with key `experiment:namespace.name:detected_end`

4. To create a forecast, set up the forecasting parameters as a JSON record in environment variable `FORECAST_PARAMETERS`, then call `python make.py forecast`.
    - FORECAST_PARAMETERS holds a json record with the following fields:
        - start_row_cnt - int
        - corrections - array of 12 values for each of four metrics:
            - growth
            - row_cnt_seasonal_correction
            - num_vehicles_seasonal_correction
            - num_trips_seasonal_correction
        - correction_weekly - array of 168 values for each of 3 metrics
            - row_cnt_weekly_correction
            - num_vehicles_weekly_correction
            - num_trips_weekly_correction
        - monthly_rate  - float
        - yearly_growth_rate - float
    - FORECAST_NAME - namespace.name
    - Running this will generate an array of 8760 in redis with keys `forecast:namespace.name:inputs`  
    - `forecast:namespace.name:metadata` will be a record containing some metadata and summary statistics about the forecast; things like max_rps or total_records_sent for example

5. To run a simulation,
    - FORECAST_NAME - (string, a reference to a forecast name)
    - TWIN_NAME - (string, a reference to a twin name)
    - SIMULATION_NAME - the name of this simulation
    - Running this will generate a set of metrics in redis with keys `simulation:$SIMULATION_NAME:<metric>`  
    - `simulation:$SIMULATION_NAME:metadata` will be a record containing some metadata and summary statistics about the simulation; things like max_hourly_latency for exampleThis will put with metrics like cost, throughput, latency.  Each will be 8760 values, representing the hours of a year