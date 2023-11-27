import os
import requests
import json
from datetime import timedelta, datetime
from dateutil.parser import parse
import re
from plantd_modeling import configuration, twin
from plantd_modeling import metrics, cost

def describe_experiment(config, experiment_name, from_cached=False):
    

    prometheus_host = os.environ['PROMETHEUS_HOST']
    prometheus_password = os.environ['PROMETHEUS_PASSWORD']
    prom = metrics.Metrics(prometheus_host)
    
    print(experiment_name)
    ex_info = {}
    try:
        config.experiments[experiment_name].add_metrics(
            prom.get_metrics(config.experiments[experiment_name], from_cached=from_cached, also_latency=True))
    except requests.exceptions.HTTPError as e:
        print(f"Error getting metrics for {experiment_name}: {e.response.text}")
    mex = config.experiments[experiment_name].metrics

    
    total_span = (mex.index[-1]-mex.index[0]).total_seconds() 
    span = total_span / (len(mex)-1)
    #print(span, mex)

    # Spot check: are records processed the same as records injected?

    records_injected = config.experiments[experiment_name].load_patterns[config.experiments[experiment_name].upload_endpoint].total_records
    records_sent_time = config.experiments[experiment_name].duration.total_seconds()

    print(f"In experiment {experiment_name}, records injected = {records_injected}")
    earliest = {}
    mean_latencies = {}
    median_latencies = {}
    for phase in mex.columns:
        if not phase.endswith("_latency"): 
            recs_processed = mex[phase].sum() * span
            print(f"  {phase} records processed = {recs_processed.sum()} (percentage of injected = {recs_processed.sum() / records_injected * 100}%)")
            earliest[phase] = mex[phase][mex[phase] != 0].first_valid_index()
        else:
            #import pdb; pdb.set_trace()
            mean_latencies[phase] = mex[phase].mean()
            median_latencies[phase] = mex[phase].median()

    mean_latency = sum([mean_latencies[phase] for phase in mean_latencies]) /1000
    median_latency = sum([median_latencies[phase] for phase in median_latencies])/1000


    
    # Latest earliest time is the first time a packet has made it all the way through the pipeline; this is the 
    # time we'll use to calculate latency
    first_complete_pass = max(earliest.values())

    #import pdb; pdb.set_trace()
    if "good" in config.experiments[experiment_name].pipeline_name.dotted_name:
        pipeline_resource_namespace = "ubi"
    elif "bad" in config.experiments[experiment_name].pipeline_name.dotted_name:
        pipeline_resource_namespace = "ubi-2"
    elif "fixed" in config.experiments[experiment_name].pipeline_name.dotted_name:
        pipeline_resource_namespace = "ubi-3"
    else:
        raise Exception("Unknown pipeline resource namespace")

    cost_info = cost.get_cost("opencost",
        experiment_name,
        pipeline_resource_namespace,
        config.experiments[experiment_name].start_time, config.experiments[experiment_name].end_time,
        from_cached=from_cached)
    
    #import pdb; pdb.set_trace()
    total_cost = sum([cost_info[phase]["total_cost"] for phase in cost_info])

    # I can't reconcile the counts here for a few reasons:
    #   - each phase may process a variable number of records (in UBI, its 10x as many in phases 2 and 3)
    #   - for the first phase, 30-second intervals are too wide. I should at least interpolate, or maybe gather finer data

    # However, for building the d-twin here, all I really care about is end-to-end throughput and latency.  So I can just
    # use the duration, and the total records sent.

    print(f"Total cost: {total_cost}, total span: {total_span}, resulting cost per hour {total_cost/(total_span/3600.0)}")
    print(f"Latency calculations: difference {(first_complete_pass - config.experiments[experiment_name].start_time.replace(tzinfo=None)).total_seconds()}, phase summed mean {mean_latency}, median {median_latency}")
        
    return {
        "records_injected": records_injected,
        "total_span": total_span,
        "mean_latency": mean_latency,
        "median_latency": median_latency,
        "net_throughput": records_injected / total_span,
        "total_cost": total_cost,
        "cost_per_hour": total_cost/(total_span/3600.0),
    }

def build_twin(model_type, from_cached=False):
    twin_name = os.environ['TWIN_NAME']

    config = configuration.ConfigurationConnectionEnvVars()

    for exp in config.experiments:
        print(exp)
        print(f"      Start time  {config.experiments[exp].start_time.isoformat()}")
        print(f"      End time  {config.experiments[exp].end_time.isoformat()}")
        print(f"      Load Duration  {config.experiments[exp].duration}")
        print(f"      Pipeline  {config.experiments[exp].pipeline_name}")
        print(f"      Load patterns  {','.join(config.experiments[exp].load_pattern_names)}")
        print(f"      Name for the upload endpoint appears to be {config.experiments[exp].upload_endpoint}")
        lp_upload = config.experiments[exp].load_patterns[config.experiments[exp].upload_endpoint]
        print(f"      1st Load pattern duration  {lp_upload.total_duration}")
        print(f"      1st Load pattern records sent  {lp_upload.total_records}")
    
    
    if len(config.experiments) == 0:
        print("No experiments found")
        
        return

    # This breaks if there is more than one experiment; the simplemodel should be built out of multiple experiments
    for experiment_name in config.experiments:
        ex_info = describe_experiment(config, experiment_name, from_cached=from_cached)

        metrics.redis.save_str("temp:experiment_summary", experiment_name, json.dumps(ex_info))
        metrics.redis.save_str("temp:experiment_cr", experiment_name, json.dumps(config.experiments[experiment_name].serialize()))
        metrics.redis.save_str("temp:experiment_loadpatterns", experiment_name, 
                               json.dumps({lp: config.experiments[experiment_name].load_patterns[lp].serialize() 
                                           for lp in config.experiments[experiment_name].load_patterns}))

        sm = twin.SimpleModel(maxrate_rph = ex_info["records_injected"]/ex_info["total_span"],
                                  per_vm_hourcost = ex_info["cost_per_hour"],
                                  avg_latency_s = ex_info["mean_latency"],
                                  policy="fifo")
        if model_type == "simple":
            metrics.redis.save_str("twinmodel", twin_name, sm.serialize())
            return sm
        elif model_type == "quickscaling":
            qm = twin.QuickscalingModel(fixed_hourcost = 0, basemodel = sm, policy="fifo")

            metrics.redis.save_str("twinmodel", twin_name, qm.serialize()  )              
            return qm
        elif model_type == "autoscaling":
            am = twin.AutoscalingModel(fixed_hourcost = 0,
                                      upPctTrigger = 80.0, upDelay_h = 2, dnPctTrigger = 20.0, 
                                      dnDelay_h = 2, basemodel = sm, policy="fifo")
            metrics.redis.save_str("twinmodel", twin_name, am.serialize())
            return am
        

    #return config.experiments

