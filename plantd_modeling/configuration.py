from dataclasses import dataclass
import os
import requests
import json
from datetime import timedelta, datetime
from dateutil.parser import parse
import re
from typing import Any, List, Dict
from pandas import DataFrame
import pandas as pd
import io
import humanfriendly

def parse_duration(s : str) -> timedelta:
    # Extract hours, minutes, and seconds
    hours, minutes, seconds = 0, 0, 0
    if "h" in s:
        hours = int(re.search(r'(\d+)h', s).group(1))
    if "m" in s:
        minutes = int(re.search(r'(\d+)m', s).group(1))
    if "s" in s:
        seconds = int(re.search(r'(\d+)s', s).group(1))
    
    return timedelta(hours=hours, minutes=minutes, seconds=seconds)


@dataclass
class KubernetesName:
    dotted_name: str 
    def __post_init__(self):
        self.namespace = self.dotted_name.split('.')[0]
        self.name = self.dotted_name.split('.')[1]

    @classmethod
    def from_json(cls, json_rec) -> 'KubernetesName':
        return cls(json_rec['namespace'] + "." + json_rec['name'])
    
    # make hashable
    def __hash__(self):
        return hash(self.dotted_name)
    
    def __str__(self) -> str:
        return self.dotted_name


class NetCost:
    def __init__(self, nc):
        self.raw_k8s_defn = nc
        self.net_cost_per_mb = float(nc["spec"]["netCostPerMB"])
        self.processed_data_retention_policy_months = nc["spec"]["processedDataRetentionPolicyMonths"]
        self.processed_data_store_cost_per_mb_month = float(nc["spec"]["processedDataStoreCostPerMBMonth"])
        self.raw_data_retention_policy_months = nc["spec"]["rawDataRetentionPolicyMonths"]
        self.raw_data_store_cost_per_mb_month = float(nc["spec"]["rawDataStoreCostPerMBMonth"])
        
    
    def serialize(self):
        return {
            "net_cost_per_mb": self.net_cost_per_mb,
            "processed_data_retention_policy_months": self.processed_data_retention_policy_months,
            "processed_data_store_cost_per_mb_month": self.processed_data_store_cost_per_mb_month,
            "raw_data_retention_policy_months": self.raw_data_retention_policy_months,
            "raw_data_store_cost_per_mb_month": self.raw_data_store_cost_per_mb_month
        }
    
    @classmethod
    def xdeserialize(cls, json_rec):
        nc = cls({})
        nc.net_cost_per_mb = json_rec["spec"]["net_cost_per_mb"]
        nc.processed_data_retention_policy_months = json_rec["spec"]["processed_data_retention_policy_months"]
        nc.processed_data_store_cost_per_mb_month = json_rec["spec"]["processed_data_store_cost_per_mb_month"]
        nc.raw_data_retention_policy_months = json_rec["spec"]["raw_data_retention_policy_months"]
        nc.raw_data_store_cost_per_mb_month = json_rec["spec"]["raw_data_store_cost_per_mb_month"]
        return nc
    
    def apply(self, traffic_model):
        if "bandwidth_min" in traffic_model.traffic.columns:
            self.monthly_totals = traffic_model.traffic.groupby(["Year","Month"])[["bandwidth_min","bandwidth_max"]].sum()
        else:
            self.monthly_totals = traffic_model.traffic.groupby(["Year","Month"])[["hourly"]].sum()
            self.monthly_totals.columns = ["bandwidth_min"]
            self.monthly_totals["bandwidth_max"] = self.monthly_totals["bandwidth_min"]
            
        self.monthly_totals["net_cost_per_month_min"] = self.monthly_totals["bandwidth_min"] / 1024000.0 * self.net_cost_per_mb
        self.monthly_totals["net_cost_per_month_max"] = self.monthly_totals["bandwidth_max"] / 1024000.0 * self.net_cost_per_mb
        self.monthly_totals["raw_data_store_cost_per_month_min"] = self.monthly_totals["bandwidth_min"] / 1024000.0 \
            * self.processed_data_store_cost_per_mb_month * self.processed_data_retention_policy_months
        self.monthly_totals["raw_data_store_cost_per_month_max"] = self.monthly_totals["bandwidth_max"] / 1024000.0 \
            * self.processed_data_store_cost_per_mb_month * self.processed_data_retention_policy_months
        self.monthly_totals["cloud_processing_cost"] = 0

    def serialize_monthly_totals(self):
        return self.monthly_totals.reset_index().to_csv()
    



@dataclass
class ScenarioTask():
    months_relevant: List[int]
    name: str
    push_frequency_per_month_min: float
    push_frequency_per_month_max: float
    sending_devices_min: int
    sending_devices_max: int
    size: int


class Scenario():
    dataset_config_compress_per_schema: bool
    dataset_config_compressed_file_format: str
    dataset_config_file_format: str
    pipeline_ref: KubernetesName
    tasks: List[ScenarioTask]
        
    # Serialize and deserialize as json
    def serialize(self):
        return json.dumps({
            "spec": {
                "dataSetConfig": {
                    "compressPerSchema": self.dataset_config_compress_per_schema,
                    "compressedFileFormat": self.dataset_config_compressed_file_format,
                    "fileFormat": self.dataset_config_file_format
                },
                "pipelineRef": self.pipeline_ref.serialize(),
                "tasks": [{
                    "monthsRelevant": task.months_relevant,
                    "name": task.name,
                    "pushFrequencyPerMonth": {
                        "min": task.push_frequency_per_month_min,
                        "max": task.push_frequency_per_month_max
                    },
                    "sendingDevices": {
                        "min": task.sending_devices_min,
                        "max": task.sending_devices_max
                    },
                    "size": humanfriendly.format_size(task.size)
                } for task in self.tasks]
            }
        })
    
    @classmethod
    def deserialize(cls, jsonstr):
        params = json.loads(jsonstr)["spec"]
        
        scen = cls()
        scen.dataset_config_compress_per_schema = params["dataSetConfig"]["compressPerSchema"],
        scen.dataset_config_compressed_file_format = params["dataSetConfig"]["compressedFileFormat"],
        scen.dataset_config_file_format = params["dataSetConfig"]["fileFormat"],
        scen.pipeline_ref = KubernetesName.from_json(params["pipelineRef"]),
        scen.tasks = [ScenarioTask(
                months_relevant = task["monthsRelevant"],
                name = task["name"],
                push_frequency_per_month_min = task["pushFrequencyPerMonth"]["min"],
                push_frequency_per_month_max = task["pushFrequencyPerMonth"]["max"],
                sending_devices_min = task["sendingDevices"]["min"],
                sending_devices_max = task["sendingDevices"]["max"],
                size = humanfriendly.parse_size(task["size"])
            ) for task in params["tasks"]]
        return scen
    


class LoadPattern:
    def __init__(self, lp):
        if len(lp) == 0:
            return
        self.raw_k8s_defn = lp
        self.load_pattern_name = KubernetesName.from_json(lp["metadata"])
        self.spec = lp["spec"]   # stages=[{duration:3m, target=30}], startRate=10, timeUnit=1s
        self.total_duration = 0
        self.total_records = 0
        rate = int(self.spec["startRate"])
        #print(f"Start rate: {rate}")
        for stage in self.spec["stages"]:
            this_stage_duration = parse_duration(stage["duration"]).total_seconds()
            target_rate = int(stage["target"])
            this_stage_records = this_stage_duration * (min(rate, target_rate) + abs(rate - target_rate) / 2)
            self.total_duration += this_stage_duration
            self.total_records += this_stage_records
            #print(f"Stage: {stage['duration']} {stage['target']}: adding {this_stage_records} recs over {this_stage_duration} secs")
            #print(f"   -> {self.total_records} recs {self.total_duration} secs")
            rate = target_rate

    def serialize(self):
        return {
            "load_pattern_name": self.load_pattern_name.dotted_name,
            "spec": self.spec,
            "total_duration": self.total_duration,
            "total_records": self.total_records
        }
    
    @classmethod
    def deserialize(cls, json_rec):
        lp = cls({})
        lp.load_pattern_name = KubernetesName(json_rec["load_pattern_name"])
        lp.spec = json_rec["spec"]
        lp.total_duration = json_rec["total_duration"]
        lp.total_records = json_rec["total_records"]
        return lp

class Experiment:
    def __init__(self, experiment):
        if len(experiment) == 0:
            return
        self.raw_k8s_defn = experiment
        self.experiment_name = KubernetesName.from_json(experiment['metadata'])
        self.start_time = parse(experiment['status']['startTime'])
        self.upload_endpoint = list(experiment['status']['duration'].keys())[0]
        self.end_time = parse_duration(experiment['status']['duration'][self.upload_endpoint]) + self.start_time
        self.duration = self.end_time - self.start_time
        self.load_pattern_names = {lp["endpointName"]: KubernetesName.from_json(lp["loadPatternRef"]) 
                                   for lp in experiment['spec']['loadPatterns']}
        self.pipeline_name = KubernetesName.from_json(experiment["spec"]["pipelineRef"]) 
        self.load_patterns : Dict[KubernetesName] = {}
        self.pipeline : Pipeline = None
        self.metrics : DataFrame = None

    def add_metrics(self, metrics):
        self.metrics = metrics

    def serialize(self):
        return {
            "experiment_name": self.experiment_name.dotted_name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "duration": self.duration.total_seconds(),
            "load_pattern_names": {k: str(v) for k,v in self.load_pattern_names.items()},
            "pipeline_name": str(self.pipeline_name),
            "load_patterns": { lp: self.load_patterns[lp].serialize() for lp in self.load_patterns },
            "pipeline": self.pipeline.serialize() if self.pipeline else None,
            "metrics": self.metrics.to_csv()
        }
    
    @classmethod
    def deserialize(cls, json_rec):
        exp = cls({})
        exp.experiment_name = KubernetesName(json_rec["metadata"])
        exp.start_time = parse(json_rec["start_time"])
        exp.end_time = parse(json_rec["end_time"])
        exp.duration = timedelta(seconds=json_rec["duration"])
        exp.load_pattern_names = {k: KubernetesName(v) for k,v in json_rec["load_pattern_names"].items()}
        exp.pipeline_name = KubernetesName(json_rec["pipeline_name"])
        exp.load_patterns = {lp : LoadPattern.deserialize(json_rec["load_patterns"][lp]) for lp in json_rec["load_patterns"]}
        exp.pipeline = Pipeline.deserialize(json_rec["pipeline"]) if json_rec["pipeline"] else None
        exp.metrics = reconstructed_df = pd.read_csv(io.StringIO(json_rec["metrics"]), index_col=0, parse_dates=True)
        return exp
    
    def save_file(self, fname):
        with open(fname, "w") as f:
            json.dump(self.serialize(), f)

    @classmethod
    def load_file(cls, fname):
        with open(fname, "r") as f:
            return cls.deserialize(json.load(f))

class Pipeline:
    """Pipeline info: don't know what I'll need just yet"""
    def __init__(self, pipeline_rec):
        self.pipeline_name = KubernetesName.from_json(pipeline_rec["metadata"])
        self.details = pipeline_rec

    def serialize(self):
        return {
            "pipeline_name": self.pipeline_name.dotted_name,
            "details": self.details
        }
    
    @classmethod
    def deserialize(cls, json_rec):
        p = cls({})
        p.pipeline_name = KubernetesName(json_rec["pipeline_name"])
        p.details = json_rec["details"]
        return p

class ConfigurationConnectionEnvVars:
    def __init__(self):
        self.experiments  = {}
        self.load_patterns = {}
        experiment_names = os.environ["EXPERIMENT_NAMES"].split(",")
        load_pattern_names = os.environ["LOAD_PATTERN_NAMES"].split(",")
        exp_raw = json.loads(os.environ[f"EXPERIMENT_METADATA"])
        lp_raw = json.loads(os.environ[f"LOAD_PATTERN_METADATA"])
        for item in exp_raw["items"]:
            experiment_name = KubernetesName.from_json(item["metadata"])
            self.experiments[experiment_name] = Experiment(item)
        for item in lp_raw["items"]:
            load_pattern_name = KubernetesName.from_json(item["metadata"])
            self.load_patterns[load_pattern_name] = LoadPattern(item)
        for exp in self.experiments.values():
            exp.load_patterns = {k:self.load_patterns[v] for k,v in exp.load_pattern_names.items()}
            #exp.pipeline = self.get_pipeline_metadata(exp.pipeline_name)
        self.scenario = None
        self.netcosts = None
        if "SCENARIO" in os.environ:
            self.scenario = Scenario.deserialize(os.environ["SCENARIO"])
        if "NETCOSTS" in os.environ:
            self.netcosts = NetCost(json.loads(os.environ["NETCOSTS"]))
        
    def get_experiment_metadata(self):
        return self.experiments

    def get_load_pattern_metadata(self, loadpattern_name: KubernetesName):
        return self.load_patterns[loadpattern_name]   

class ConfigurationConnectionDirect:
    def __init__(self, experiments, load_patterns, from_environment=False):
        self.experiments = {KubernetesName(n): Experiment(e) for (n,e) in experiments.items()}
        self.load_patterns = {KubernetesName(n): LoadPattern(e) for (n,e) in load_patterns.items()}
        
    def get_experiment_metadata(self):
        return self.experiments

    def get_load_pattern_metadata(self, loadpattern_name: KubernetesName):
        return self.load_patterns[loadpattern_name]

class ConfigurationConnectionKubernetes:
    def __init__(self, kubernetes_service_address, group, controller_version):
        self.kubernetes_service_address = kubernetes_service_address
        self.group = group
        self.controller_version = controller_version
        self.raw_experiments = {}
        self.raw_load_patterns = []

    def get_experiment_metadata(self, experiment_names: List[KubernetesName] = [], from_cached=False):
        # Get start and end times of experiments
        experiment_metadata  = {}
        query_url = f"{self.kubernetes_service_address}/apis/{self.group}/{self.controller_version}/experiments"
        response = requests.get(query_url, verify=False, stream=False)
        response.raise_for_status()
        experiments = response.json()
        self.raw_experiments = experiments
        for exp in experiments["items"]:
            try:
                exp_obj = Experiment(exp)
                
                if exp_obj.experiment_name in experiment_names or len(experiment_names) == 0:
                    experiment_metadata[exp_obj.experiment_name] = exp_obj
            except Exception as e:
                print(f"Error processing experiment {exp['metadata']['name']}: {e}")
                continue

        for exp in experiment_metadata.values():
            exp.load_patterns = {k:self.get_load_pattern_metadata(v) for k,v in exp.load_pattern_names.items()}
            #exp.pipeline = self.get_pipeline_metadata(exp.pipeline_name)

        return experiment_metadata

    def get_load_pattern_metadata(self, loadpattern_name: KubernetesName):
        query_url = f"{self.kubernetes_service_address}/apis/{self.group}/{self.controller_version}/namespaces/{loadpattern_name.namespace}/loadpatterns/{loadpattern_name.name}"
        response = requests.get(query_url, verify=False, stream=False)
        response.raise_for_status()
        lp = response.json()
        self.raw_load_patterns.append(lp)
        return LoadPattern(lp)

    def get_pipeline_metadata(self, pipeline_name: KubernetesName):
        query_url = f"{self.kubernetes_service_address}/apis/{self.group}/{self.controller_version}/namespaces/{pipeline_name.namespace}/pipelines/{pipeline_name.name}"
        response = requests.get(query_url, verify=False, stream=False)
        response.raise_for_status()
        p = response.json()
        return Pipeline(pipeline_name)
    
    def write_to_environment(self):
        with open("environment.env", "w") as f:
            f.write(f"EXPERIMENT_NAMES={','.join([str(e) for e in self.get_experiment_metadata().keys()])}\n")
            f.write(f"LOAD_PATTERN_NAMES={','.join([str(e) for e in self.get_load_pattern_metadata().keys()])}\n")
            # Write each experiment's metadata to the environment
            for e in self.get_experiment_metadata().values():
                f.write(f"EXPERIMENT_METADATA_{e.experiment_name.dotted_name}={json.dumps(e.serialize())}'\n")
            # Write each load pattern's metadata to the environment
            for lp in self.get_load_pattern_metadata().values():
                f.write(f"LOAD_PATTERN_METADATA_{lp.load_pattern_name.dotted_name}={json.dumps(lp.serialize())}'\n")
            


