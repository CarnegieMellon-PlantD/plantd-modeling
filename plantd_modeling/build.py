import os
import requests
import json
from datetime import timedelta, datetime
from dateutil.parser import parse
import re
from plantd_modeling import configuration
from plantd_modeling import metrics


def build_model():
    experiment_names = os.environ['EXPERIMENT_NAMES']
    experiment_names = experiment_names.split(',')
    experiment_names = [name.strip() for name in experiment_names]
    experiment_names = []   # wildcard for development
    
    group = os.environ['GROUP']
    controller_version = os.environ['CONTROLLER_VERSION']
    twin_name = os.environ['TWIN_NAME']
    redis_host = os.environ['REDIS_HOST']
    redis_password = os.environ['REDIS_PASSWORD']
    prometheus_host = os.environ['PROMETHEUS_HOST']
    prometheus_password = os.environ['PROMETHEUS_PASSWORD']
    kubernetes_service_address = os.environ['KUBERNETES_SERVICE_ADDRESS']
    
    
    config = configuration.ConfigurationConnection(kubernetes_service_address, group, controller_version)
    experiment_metadata = config.get_experiment_metadata(experiment_names)
    
    
    for exp in experiment_metadata:
        print(exp)
        print(f"      Start time  {experiment_metadata[exp].start_time.isoformat()}")
        print(f"      End time  {experiment_metadata[exp].end_time.isoformat()}")
        print(f"      Load Duration  {experiment_metadata[exp].duration}")
        print(f"      Pipeline  {experiment_metadata[exp].pipeline_name}")
        print(f"      Load patterns  {','.join(experiment_metadata[exp].load_pattern_names)}")
        lp_upload = experiment_metadata[exp].load_patterns["upload"]
        print(f"      1st Load pattern duration  {lp_upload.total_duration}")
        print(f"      1st Load pattern records sent  {lp_upload.total_records}")
    
    # Get metrics from Prometheus
    prom = metrics.Metrics(prometheus_host)
    
    for experiment_name in experiment_metadata:
        print(experiment_name)
        experiment_metadata[experiment_name].add_metrics(
            prom.get_metrics(experiment_metadata[experiment_name]))
        print(experiment_metadata[experiment_name].metrics)

    return experiment_metadata

