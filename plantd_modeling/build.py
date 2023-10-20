import os
import requests
import json
from datetime import timedelta, datetime
from dateutil.parser import parse
import re
from plantd_modeling import configuration
from plantd_modeling import metrics


def build_model():
    experiments = os.environ['EXPERIMENTS']
    load_patterns = os.environ['LOAD_PATTERNS']
    
    group = os.environ['GROUP']
    controller_version = os.environ['CONTROLLER_VERSION']
    twin_name = os.environ['TWIN_NAME']
    redis_host = os.environ['REDIS_HOST']
    redis_password = os.environ['REDIS_PASSWORD']
    prometheus_host = os.environ['PROMETHEUS_HOST']
    prometheus_password = os.environ['PROMETHEUS_PASSWORD']
    
    
    config = configuration.ConfigurationConnectionDirect(experiments, load_patterns)
    
    
    for exp in config.experiments:
        print(exp)
        print(f"      Start time  {config.experiments[exp].start_time.isoformat()}")
        print(f"      End time  {config.experiments[exp].end_time.isoformat()}")
        print(f"      Load Duration  {config.experiments[exp].duration}")
        print(f"      Pipeline  {config.experiments[exp].pipeline_name}")
        print(f"      Load patterns  {','.join(config.experiments[exp].load_pattern_names)}")
        lp_upload = config.experiments[exp].load_patterns["upload"]
        print(f"      1st Load pattern duration  {lp_upload.total_duration}")
        print(f"      1st Load pattern records sent  {lp_upload.total_records}")
    
    # Get metrics from Prometheus
    prom = metrics.Metrics(prometheus_host)
    
    for experiment_name in config.experiments:
        print(experiment_name)
        try:
            config.experiments[experiment_name].add_metrics(
                prom.get_metrics(config.experiments[experiment_name]))
        except requests.exceptions.HTTPError as e:
            print(f"Error getting metrics for {experiment_name}: {e.response.text}")
        print(config.experiments[experiment_name].metrics)

    return config.experiments

