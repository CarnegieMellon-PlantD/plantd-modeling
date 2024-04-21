#from plantd_modeling import build, trafficmodel, twin, advanced_trafficmodel, build_advanced
import sys
from plantd_modeling import configuration, metrics
import json
import os
import time
import datetime
import pytz


config = configuration.ConfigurationConnectionEnvVars()
DEBOUNCE_PERIOD = int(os.environ['DEBOUNCE_PERIOD'])
QUERY_WINDOW = int(os.environ['QUERY_WINDOW'])
POD_DETATCH_ADJUSTMENT = int(os.environ['POD_DETATCH_ADJUSTMENT'])
experiment = list(config.experiments.keys())[0]   # Should just be one experiment
prometheus_host = os.environ['PROMETHEUS_HOST']
prometheus_password = os.environ['PROMETHEUS_PASSWORD']
prom = metrics.Metrics(prometheus_host)
    
while True:
    time.sleep(DEBOUNCE_PERIOD)
    
    recent_pd = prom.end_detector_simplified(experiment, QUERY_WINDOW, DEBOUNCE_PERIOD, POD_DETATCH_ADJUSTMENT)
    print("Recent activity level: ", recent_pd)

    if recent_pd is not None and  recent_pd["transition_direction"] == "downwards":
        now = time.time()
        wait_time = recent_pd["transition_time"] + POD_DETATCH_ADJUSTMENT - now
        print("EXPERIMENT ENDED AT ", datetime.datetime.fromtimestamp(recent_pd["transition_time"], tz=pytz.UTC).isoformat() )
        
        if wait_time > 0:
            print (f'WAITING {wait_time} SECONDS TO EXIT AT {datetime.datetime.fromtimestamp(now + wait_time, tz=pytz.UTC).isoformat()}')
            time.sleep (wait_time)
        elif wait_time == 0:
            print (f'EXITING NOW')
        else:
            print (f'MISSED THE WINDOW TO EXIT IN TIME; EXITING NOW')
        exit()

