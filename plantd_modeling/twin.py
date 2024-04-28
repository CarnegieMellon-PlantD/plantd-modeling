from dataclasses import dataclass  
import json
import os
import pandas as pd
from plantd_modeling import trafficmodel, metrics
import math

@dataclass
class PipelineModel:
    def simulate(self, traffic):
        #twin_name = os.environ['TWIN_NAME']
        sim_name = os.environ['SIM_NAME']
        #traffic_model_name = os.environ['TRAFFIC_MODEL_NAME']
        
        twin = self
        #twin = SimpleModel.deserialize(open(f"fakeredis/twinmodel_{twin_name}.json").read())
        #traffic = trafficmodel.TrafficModel.deserialize_parameters(open(f"fakeredis/trafficmodel_{traffic_model_name}.json").read())
        #traffic.deserialize_forecast(f"fakeredis/trafficmodel_{traffic_model_name}.csv")
        traffic.calculate(twin)
        
        metrics.redis.save_str("simulation_traffic", sim_name, traffic.traffic.to_csv(index=True))
        
        # TO DO: add SLA checks to the kubernetes objects, so they can be checked here.
        # This sample code does the check, but it's not configurable by the user.
        #sla_check = traffic.sla_check({"latency_sla_percent": 99.0, "latency_sla_limit": 70.0})

        if "latency_fifo" in traffic.traffic.columns:
            totals = {"total_pipeline_cost": float(traffic.traffic.pipeline_cost.sum()), 
                    "avg_latency_s": float(traffic.traffic.latency_fifo.mean()),
                    "max_latency_s": float(traffic.traffic.latency_fifo.max()), 
                    "avg_queue": float(traffic.traffic.queue_len.mean()),
                    "max_queue": float(traffic.traffic.queue_len.max()), 
                    "avg_throughput_rph": float(traffic.traffic.throughput.mean()),
                    "max_throughput_rph": float(traffic.traffic.throughput.max())}

            month_aggregations = {
                'latency_fifo': 'mean',
                'pipeline_cost': 'sum',
                'queue_len': 'mean',
                'hourly': 'sum',
            }
        else:
            month_aggregations = {}
            totals = {}

        for schema in traffic.traffic.columns:
            if schema.startswith("task_") and schema.endswith("_rph"):
                month_aggregations[schema] = 'sum'
        
        if "hourly_network_cost" in traffic.traffic.columns:
            month_aggregations['bandwidth'] = 'sum'
            month_aggregations['hourly_network_cost'] = 'sum'
            month_aggregations['hourly_raw_data_store_cost'] = 'sum'
        
        df_monthly = traffic.traffic.groupby('Month').agg(month_aggregations).reset_index()
        df_monthly.rename(columns={
            "hourly_network_cost": "network_cost",
            "hourly_raw_data_store_cost": "storage_cost"
        }, inplace=True)

        metrics.redis.save_str("simulation_monthly", sim_name, 
            df_monthly.to_csv(index=True))

        if "hourly_network_cost" in traffic.traffic.columns:
            totals["network_cost"] = float(traffic.traffic.hourly_network_cost.sum())
            totals["storage_cost"] = float(traffic.traffic.hourly_raw_data_store_cost.sum())
            if "pipeline_cost" in traffic.traffic.columns:
                totals["pipeline_cost"] = float(traffic.traffic.pipeline_cost.sum())
                totals["total_cost"] = totals["network_cost"] + totals["storage_cost"] + totals["pipeline_cost"]

        metrics.redis.save_str("simulation_summary", sim_name, 
            json.dumps(totals))
        

class NullModel(PipelineModel):
    def reset(self):
        pass
    def input(self, recs_this_hour):
        pass
    def serialize(self):
        return json.dumps({"model_type": "null"})
    
    @classmethod
    def deserialize(cls, jsonstr):
        params = json.loads(jsonstr)
        if params["model_type"] != "null":
            raise Exception(f"Unknown model type {params['model_type']}")
        return NullModel()
    
    def simulate(self, traffic):

        sim_name = os.environ['SIM_NAME']
        traffic_model_name = os.environ['TRAFFIC_MODEL_NAME']
        
        #thru = traffic.calculate_throughput(twin)
        #queue = traffic.calculate_queue(twin)

        metrics.redis.save_str("simulation_traffic", sim_name, traffic.traffic.to_csv(index=True))
        
        # TO DO: add SLA checks to the kubernetes objects, so they can be checked here.
        # This sample code does the check, but it's not configurable by the user.
        #sla_check = traffic.sla_check({"latency_sla_percent": 99.0, "latency_sla_limit": 70.0})

        totals = {"total_pipeline_cost": 0.0, 
                "avg_latency_s": 0.0,
                "max_latency_s": 0.0,
                "avg_queue": 0.0,
                "max_queue": 0.0,
                "avg_throughput_rph": 0.0,
                "max_throughput_rph":0.0}

        #month_aggregations = {
        #    'latency_fifo': 'mean',
        #    'pipeline_cost': 'sum',
        #    'queue_len': 'mean',
        #    'hourly': 'sum',
        #}
        month_aggregations = {}

        for schema in traffic.traffic.columns:
            if schema.startswith("task_") and schema.endswith("_rph"):
                month_aggregations[schema] = 'sum'
        
        if "hourly_network_cost" in traffic.traffic.columns:
            month_aggregations['bandwidth'] = 'sum'
            month_aggregations['hourly_network_cost'] = 'sum'
            month_aggregations['hourly_raw_data_store_cost'] = 'sum'
        
        df_monthly = traffic.traffic.groupby('Month').agg(month_aggregations).reset_index()
        df_monthly.rename(columns={
            "hourly_network_cost": "network_cost",
            "hourly_raw_data_store_cost": "storage_cost"
        }, inplace=True)

        metrics.redis.save_str("simulation_monthly", sim_name, 
            df_monthly.to_csv(index=True))

        if "hourly_network_cost" in traffic.traffic.columns:
            totals["network_cost"] = float(traffic.traffic.hourly_network_cost.sum())
            totals["storage_cost"] = float(traffic.traffic.hourly_raw_data_store_cost.sum())
            totals["pipeline_cost"] = 0.0
            totals["total_cost"] = totals["network_cost"] + totals["storage_cost"] + totals["pipeline_cost"]

        metrics.redis.save_str("simulation_summary", sim_name, 
            json.dumps(totals))
        
@dataclass
class SimpleSchemaAwareModel(PipelineModel):
    policy: str
    per_vm_hourcost: float
    taskwise_params: dict
    
    def __post_init__(self):
        if not self.policy in ["fifo","lifo","random"]:
            raise Exception(f"Unknown scaling policy {self.policy}")

    @classmethod
    def deserialize(cls, jsonstr): 
        params = json.loads(jsonstr)
        if params["model_type"] != "simple-schema-aware":
            raise Exception(f"Unknown model type {params['model_type']}")
        return SimpleSchemaAwareModel(policy=params["policy"],
                                      per_vm_cost=params["per_vm_cost"],
                                      taskwise_params=params["taskwise_params"])          

    def serialize(self): 
        return json.dumps({
            "model_type": "simple-schema-aware",
            "taskwise_params": self.taskwise_params,
            "per_vm_hourcost": self.per_vm_hourcost,  #misnomer; this is per "nomimal pipeline", not per "vm".
            "policy": self.policy
        })

    def reset(self): 
        self.queue = []   # List of (task, timestamps) tuples
        self.time = 0   # current hour of year simulation (int)
        self.time_done = 0.0  # Exact time in detailed simulation (float)
        self.cumu_pipeline_cost = 0.0
    
    def input(self, detailed_traffic_this_hour): 
        #print(f"SimpleSchemaAwareModel.input: {detailed_traffic_this_hour}")
        
        newqueue = []
        for sch in detailed_traffic_this_hour:
            if detailed_traffic_this_hour[sch] > 0:
                if sch.startswith("task_") and sch.endswith("_rph"):
                    taskname = sch[5:-4]
                newqueue = newqueue + [
                    ({"task": taskname, "enqueued": self.time + 1.0/detailed_traffic_this_hour[sch]})
                ]
        self.queue = self.queue + newqueue
        proc_this_hour=0
        old_time_done = self.time_done
        sum_latency = 0.0
        while len(self.queue) > 0:
            nextpacket = self.queue[0]
            self.queue = self.queue[1:]
            proc_this_hour += 1
            nextpacket["start"] = self.time_done
            self.time_done += 1.0/self.taskwise_params[nextpacket["task"]]["maxrate_rph"]
            nextpacket["end"] = self.time_done
            nextpacket["latency"] = self.taskwise_params[nextpacket["task"]]["avg_latency_s"] + \
                nextpacket["start"] - nextpacket["enqueued"]
            sum_latency += nextpacket["latency"]
            
            if self.time_done > self.time + 1: break

        
        self.throughput_rph = proc_this_hour / (self.time_done - old_time_done)
        self.latency_fifo_s = sum_latency/proc_this_hour
        #self.queue_worstcase_age_s += 3600
       
        #self.latency_lifo = self.avg_latency_s + self.queue_worstcase_age_s
        self.hourcost = self.per_vm_hourcost
        self.cumu_pipeline_cost = self.cumu_pipeline_cost + self.hourcost


# FUTURE WORK:
#    This just assumes the same cost per hour during the experiment as during real life.
#    but we should also gather cpu and ram utilization, and learn to infer those for future
#    traffic, then from that estimate cost.
    
@dataclass
class SimpleModel(PipelineModel):
    maxrate_rph: float    # max records per hour this pipe can process
    per_vm_hourcost: float   
    avg_latency_s: float  # average latency in seconds of whole pipeline, assuming no queueing
    policy: str
    numproc: int = 1

    def __post_init__(self):
        if not self.policy in ["fifo","lifo","random"]:
            raise Exception(f"Unknown scaling policy {self.policy}")
        
    # Serialize and deserialize as json
    def serialize(self):
        return json.dumps({
            "model_type": "simple",
            "maxrate_rph": self.maxrate_rph,
            "per_vm_hourcost": self.per_vm_hourcost,  #misnomer; this is per "nomimal pipeline", not per "vm".
            "avg_latency_s": self.avg_latency_s,
            "policy": self.policy
        })
    
    @classmethod
    def deserialize(cls, jsonstr):
        params = json.loads(jsonstr)
        if params["model_type"] != "simple":
            raise Exception(f"Unknown model type {params['model_type']}")
        return SimpleModel(params["maxrate_rph"], params["per_vm_hourcost"], params["avg_latency_s"], params["policy"])
        
    def reset(self):
        #self.upq = []
        #self.dnq = []
        #self.numproc = 1
        self.cumu_pipeline_cost = 0.0
        self.queue = 0
        self.queue_worstcase_age_s = 0
        self.throughput_rph = 0
        self.latency_fifo_s = 0
        self.latency_lifo_s = 0
        self.hourcost = 0
        
    def input(self, recs_this_hour):  
        self.throughput_rph = min(recs_this_hour + self.queue, self.maxrate_rph)
        self.latency_fifo_s = self.avg_latency_s + self.queue * 1.0 / self.maxrate_rph
        self.queue = self.queue + recs_this_hour - self.throughput_rph
        self.queue_worstcase_age_s += 3600
        if self.queue < 0: 
            self.queue = 0
        if self.queue == 0:
            self.queue_worstcase_age_s = 0
        self.latency_lifo = self.avg_latency_s + self.queue_worstcase_age_s
        self.hourcost = self.per_vm_hourcost
        self.cumu_pipeline_cost = self.cumu_pipeline_cost + self.hourcost
        
        
"""        
===> TO DO: 
    v copy the code that deals with queueing stuff to here.  That should be in the pipe model, not the traffic model!
    - simplemodel should have a second-by-second simulation mode for testing, and a pandas mode for the real bulk work
    - validate pandas mode against s-by-s
    - output a characterization and trace.
    -v maybe the traffic model shoudl take this as an object? Or vice versa?
   """

@dataclass    
class QuickscalingModel(PipelineModel):
    fixed_hourcost: float
    basemodel: SimpleModel
    policy: str
        
    def __post_init__(self):
        if not self.policy in ["fifo","lifo","random"]:
            raise Exception(f"Unknown scaling policy {self.policy}")
        

    # Serialize and deserialize as json
    def serialize(self):
        return json.dumps({
            "model_type": "quickscaling",
            "fixed_hourcost": self.fixed_hourcost,
            "basemodel": self.basemodel.serialize(),
            "policy": self.policy
        })
    
    @classmethod
    def deserialize(cls, jsonstr):
        params = json.loads(jsonstr)
        if params["model_type"] != "quickscaling":
            raise Exception(f"Unknown model type {params['model_type']}")
        return AutoscalingModel(params["fixed_hourcost"], SimpleModel.deserialize(params["basemodel"]), params["policy"])

    def reset(self):
        self.numproc = 1
        self.cumu_pipeline_cost = 0.0
        self.queue = 0
        self.queue_worstcase_age_s = 0
        self.throughput_rph = 0
        self.latency_fifo_s = 0
        self.latency_lifo_s = 0
        self.hourcost = 0
        
    def input(self, recs_this_hour):  
        self.numproc = math.ceil(recs_this_hour / self.basemodel.maxrate_rph)
        self.throughput_rph = min(recs_this_hour + self.queue, self.basemodel.maxrate_rph * self.numproc)
        self.latency_fifo_s = self.basemodel.avg_latency_s + self.queue * 1.0 / (self.basemodel.maxrate_rph * self.numproc)
        self.queue = self.queue + recs_this_hour - self.throughput_rph
        self.queue_worstcase_age_s += 3600
        if self.queue < 0: 
            self.queue = 0
        if self.queue == 0:
            self.queue_worstcase_age_s = 0
        self.latency_lifo_s = self.basemodel.avg_latency_s + self.queue_worstcase_age_s
        self.hourcost = self.fixed_hourcost + self.basemodel.per_vm_hourcost * self.numproc
        self.cumu_pipeline_cost = self.cumu_pipeline_cost + self.hourcost  

@dataclass    
class AutoscalingModel(PipelineModel):
    fixed_hourcost: float
    upPctTrigger: float
    upDelay_h: int            # wait this long before scaling up
    dnPctTrigger: float
    dnDelay_h: float          # wait this long before scaling down
    basemodel: SimpleModel
    policy: str
        
    def __post_init__(self):
        if not self.policy in ["fifo","lifo","random"]:
            raise Exception(f"Unknown scaling policy {self.policy}")
        

    # Serialize and deserialize as json
    def serialize(self):
        return json.dumps({
            "model_type": "autoscaling",
            "fixed_hourcost": self.fixed_hourcost,
            "upPctTrigger": self.upPctTrigger,
            "upDelay_h": self.upDelay_h,
            "dnPctTrigger": self.dnPctTrigger,
            "dnDelay_h": self.dnDelay_h,
            "basemodel": self.basemodel.serialize(),
            "policy": self.policy
        })
    
    @classmethod
    def deserialize(cls, jsonstr):
        params = json.loads(jsonstr)
        if params["model_type"] != "autoscaling":
            raise Exception(f"Unknown model type {params['model_type']}")
        return AutoscalingModel(params["fixed_hourcost"], params["upPctTrigger"], params["upDelay_h"], params["dnPctTrigger"], params["dnDelay_h"], SimpleModel.deserialize(params["basemodel"]), params["policy"])

    def reset(self):
        self.upq_rph = []      # recs per hour processed for last upDelay_h hours
        self.dnq_rph = []      # recs per hour processed for last dnDelay_h hours
        self.numproc = 1
        self.cumu_pipeline_cost = 0.0
        self.queue = 0
        self.queue_worstcase_age_s = 0
        self.throughput_rph = 0
        self.latency_fifo_s = 0
        self.latency_lifo_s = 0
        self.hourcost = 0
        self.time_since_scale_h = 0   # hours since scaling last changed (scale up or down)
        
    def input(self, recs_this_hour):  
        self.throughput_rph = min(recs_this_hour + self.queue, self.basemodel.maxrate_rph * self.numproc)
        self.latency_fifo_s = self.basemodel.avg_latency_s + self.queue * 1.0 / (self.basemodel.maxrate_rph * self.numproc)
        self.queue = self.queue + recs_this_hour - self.throughput_rph
        self.queue_worstcase_age_s += 3600
        if self.queue < 0: 
            self.queue = 0
        if self.queue == 0:
            self.queue_worstcase_age_s = 0
        self.latency_lifo_s = self.basemodel.avg_latency_s + self.queue_worstcase_age_s
        self.hourcost = self.fixed_hourcost + self.basemodel.per_vm_hourcost * self.numproc
        self.cumu_pipeline_cost = self.cumu_pipeline_cost + self.hourcost  
        self.scale()
        
    def scale(self):
        def avg(x): return sum(x)/len(x)
        self.time_since_scale_h += 1
        self.upq_rph = (self.upq_rph + [self.throughput_rph])[-self.upDelay_h:]
        self.dnq_rph = (self.dnq_rph + [self.throughput_rph])[-self.dnDelay_h:]
        if self.time_since_scale_h >= self.upDelay_h \
          and avg(self.upq_rph) > self.basemodel.maxrate_rph * self.numproc * self.upPctTrigger/100.0:
            #print(f"Scale up from {self.numproc}: {avg(self.upq_rph)} > {self.basemodel.maxrate_rph} * {self.numproc} * {self.upPctTrigger/100.0}")
            #import pdb; pdb.set_trace()
            self.numproc += 1
            self.time_since_scale_h = 0
        elif self.time_since_scale_h >= self.dnDelay_h \
             and avg(self.dnq_rph) < self.basemodel.maxrate_rph * self.numproc * self.dnPctTrigger/100.0 \
             and self.numproc > 1:
            #print(f"Scale down from {self.numproc}: {avg(self.dnq_rph)} < {self.basemodel.maxrate_rph} * {self.numproc} * {self.dnPctTrigger/100.0}")
            self.numproc -= 1
            self.time_since_scale_h = 0



@dataclass    
class AutoscalingModelFine(PipelineModel):
    fixed_hourcost: float
    upPctTrigger: float
    upDelay_s: int
    dnPctTrigger: float
    dnDelay_s: float
    basemodel: SimpleModel
    policy: str
        
    def __post_init__(self):
        if not self.policy in ["fifo","lifo","random"]:
            raise Exception(f"Unknown scaling policy {self.policy}")
        
    def reset(self):
        self.upq_s = []
        self.dnq_s = []
        self.numproc = 1
        self.cumu_pipeline_cost = 0.0
        self.queue = 0
        self.queue_worstcase_age_s = 0
        self.throughput_rph = 0
        self.throughput_s = 0
        self.latency_fifo_s = 0
        self.latency_lifo_s = 0
        self.hourcost = 0
        self.time_since_scale_s = 0
        self.maxrate_s = self.basemodel.maxrate_rph/3600.0
        
    def input(self, recs_this_hour):
        
        slots = [0]*3600
        for i in range(int(recs_this_hour)):
            slots[int(i/3600.0)] += 1
        self.hourcost = 0
        self.throughput_rph = 0
        for recs_this_sec in slots:
            self.throughput_s = min(recs_this_sec + self.queue, self.maxrate_s * self.numproc)
            self.throughput_rph += self.throughput_s
            self.latency_fifo_s = self.basemodel.avg_latency_s + self.queue * 1.0 / (self.maxrate_s * self.numproc)
            self.queue = self.queue + recs_this_sec - self.throughput_s
            self.queue_worstcase_age_s += 1
            if self.queue < 0: 
                self.queue = 0
            if self.queue == 0:
                self.queue_worstcase_age_s = 0
            self.latency_lifo_s = self.basemodel.avg_latency_s + self.queue_worstcase_age_s
            self.hourcost += (self.fixed_hourcost/3600.0 + self.basemodel.per_vm_hourcost/3600.0 * self.numproc)
            self.scale()
        self.cumu_pipeline_cost += self.hourcost
        
        
    def scale(self):
        def avg(x): return sum(x)/len(x)
        self.time_since_scale_s += 1
        self.upq_s = (self.upq_s + [self.throughput_s])[-self.upDelay_s:]
        self.dnq_s = (self.dnq_s + [self.throughput_s])[-self.dnDelay_s:]
        if self.time_since_scale_s >= self.upDelay_s and avg(self.upq_s) > self.maxrate_s * self.numproc * self.upPctTrigger/100.0:
            #print(f"Scale up from {self.numproc}: {avg(self.upq_s)} > {self.maxrate_s} * {self.numproc} * {self.upPctTrigger/100.0}")
            self.numproc += 1
            self.time_since_scale_s = 0
        elif self.time_since_scale_s >= self.dnDelay_s \
             and avg(self.dnq_s) < self.maxrate_s * self.numproc * self.dnPctTrigger/100.0 \
             and self.numproc > 1:
            #print(f"Scale down from {self.numproc}: {avg(self.dnq_s)} < {self.maxrate_s} * {self.numproc} * {self.dnPctTrigger/100.0}")
            self.numproc -= 1
            self.time_since_scale_s = 0







# QUick refactoring:
#   Traffic model should go in a redis file, not in the environment. So, for now, manually put it in a file, and refer by name in the code
#   Traffic model will have optional generated runs as separate files.  The main model file will have key-value dictionary of these, identifying date range -> filename
#   Here in simulate, I'll use the traffic model name to load the traffic model object, which in turn loads all of its runs.  The first one is the default