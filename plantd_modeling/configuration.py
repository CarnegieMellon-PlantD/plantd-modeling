from dataclasses import dataclass
import os
import requests
import json
from datetime import timedelta, datetime
from dateutil.parser import parse
import re
from typing import Any, List, Dict
from pandas import DataFrame


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

#

class LoadPattern:
    def __init__(self, lp):
        if len(lp) == 0:
            return
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
        self.experiment_name = KubernetesName.from_json(experiment['metadata'])
        self.start_time = parse(experiment['status']['startTime'])
        self.end_time = parse_duration(experiment['status']['duration']['upload']) + self.start_time
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
            "metrics": self.metrics.to_json()
        }
    
    @classmethod
    def deserialize(cls, json_rec):
        exp = cls({})
        exp.experiment_name = KubernetesName(json_rec["experiment_name"])
        exp.start_time = parse(json_rec["start_time"])
        exp.end_time = parse(json_rec["end_time"])
        exp.duration = timedelta(seconds=json_rec["duration"])
        exp.load_pattern_names = {k: KubernetesName(v) for k,v in json_rec["load_pattern_names"].items()}
        exp.pipeline_name = KubernetesName(json_rec["pipeline_name"])
        exp.load_patterns = {lp : LoadPattern.deserialize(json_rec["load_patterns"][lp]) for lp in json_rec["load_patterns"]}
        exp.pipeline = Pipeline.deserialize(json_rec["pipeline"]) if json_rec["pipeline"] else None
        exp.metrics = DataFrame(json.loads(json_rec["metrics"]))
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
    



class ConfigurationConnection:
    def __init__(self, kubernetes_service_address, group, controller_version):
        self.kubernetes_service_address = kubernetes_service_address
        self.group = group
        self.controller_version = controller_version

    def get_experiment_metadata(self, experiment_names: List[KubernetesName] = []):
        # Get start and end times of experiments
        experiment_metadata  = {}
        query_url = f"{self.kubernetes_service_address}/apis/{self.group}/{self.controller_version}/experiments"
        response = requests.get(query_url, verify=False, stream=False)
        response.raise_for_status()
        experiments = response.json()
        for exp in experiments["items"]:
            exp_obj = Experiment(exp)
            if exp_obj.experiment_name in experiment_names or len(experiment_names) == 0:
                experiment_metadata[exp_obj.experiment_name] = exp_obj

        for exp in experiment_metadata.values():
            exp.load_patterns = {k:self.get_load_pattern_metadata(v) for k,v in exp.load_pattern_names.items()}
            #exp.pipeline = self.get_pipeline_metadata(exp.pipeline_name)

        return experiment_metadata

    def get_load_pattern_metadata(self, loadpattern_name: KubernetesName):
        query_url = f"{self.kubernetes_service_address}/apis/{self.group}/{self.controller_version}/namespaces/{loadpattern_name.namespace}/loadpatterns/{loadpattern_name.name}"
        response = requests.get(query_url, verify=False, stream=False)
        response.raise_for_status()
        lp = response.json()
        return LoadPattern(lp)

    def get_pipeline_metadata(self, pipeline_name: KubernetesName):
        query_url = f"{self.kubernetes_service_address}/apis/{self.group}/{self.controller_version}/namespaces/{pipeline_name.namespace}/pipelines/{pipeline_name.name}"
        response = requests.get(query_url, verify=False, stream=False)
        response.raise_for_status()
        p = response.json()
        return Pipeline(pipeline_name)


                
