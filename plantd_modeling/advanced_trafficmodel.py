import pandas as pd
import json
import os
from datetime import timedelta, datetime
from dateutil.parser import parse
import re
from plantd_modeling import configuration, metrics, twin
import io
from calendar import monthrange
import numpy as np



def normalize(col): return len(col) * col / col.sum()

def make_blank_frame(fromdate, todate):
    drix = pd.date_range(fromdate, todate, freq="60min")
    dr = pd.DataFrame()
    dr["date"] = drix
    dr["Year"] = dr["date"].dt.year
    dr["Day"] = dr["date"].dt.day
    dr["Month"] = dr["date"].dt.month
    dr["DOW"] = dr["date"].dt.day_name().str.upper().str.slice(stop=3)
    dr["Hour"] = dr["date"].dt.hour
    dr.set_index(["Year","Month","Day","DOW","Hour"], inplace=True)
    return dr

def serialize_series(series):
    return json.dumps({
        "data": series.tolist(),
        "index": series.index.tolist(),
        "index_name": series.index.name,
        "name": series.name
    })
    
def deserialize_series(json_str):
    deserialized = json.loads(json_str)
    series = pd.Series(deserialized["data"], index=pd.Index(deserialized["index"], name=deserialized["index_name"]))
    series.name = deserialized["name"]
    return series


def serialize_mi_series(series):
    return json.dumps({
        "data": series.tolist(),
        "index": series.index.tolist(),
        "index_names": series.index.names
    })
    
def deserialize_mi_series(json_str):
    deserialized = json.loads(json_str)
    new_index = pd.MultiIndex.from_tuples(deserialized["index"], names=deserialized["index_names"])
    return pd.Series(deserialized["data"], index=new_index)

def serialize_dataframe(df):
    # Convert DataFrame to JSON, including index names
    data = {
        "columns": df.columns.tolist(),
        "index": df.index.tolist(),
        "index_names": df.index.names,
        "data": df.values.tolist()
    }
    return json.dumps(data)
    
def deserialize_dataframe(json_str):
    # Load JSON data
    data = json.loads(json_str)

    # Reconstruct the DataFrame
    df = pd.DataFrame(data["data"], columns=data["columns"])
    df.index = pd.MultiIndex.from_tuples(data["index"], names=data["index_names"])
    return df

def adjust_by_matching_index(series, adjustment):
    # Ensure both inputs are Series
    if not isinstance(series, pd.Series):
        raise TypeError("First argument must be a pandas Series.")
    if not isinstance(adjustment, pd.Series):
        raise TypeError("Second argument must be a pandas Series.")

    # Convert series and adjustment to DataFrames
    series_df = series.to_frame(name='values')
    adjustment_df = adjustment.to_frame(name='adjustment')

    # Reset index to allow for merging
    series_df_reset = series_df.reset_index()
    adjustment_df_reset = adjustment_df.reset_index()

    # Perform a left merge on the indices
    merged_df = pd.merge(series_df_reset, adjustment_df_reset, on=adjustment.index.names, how='left')

    # Calculate the adjusted values
    # Use fillna(1) to handle cases where there's no matching adjustment
    merged_df['adjusted'] = merged_df['values'] * merged_df['adjustment'].fillna(1)

    # Set the original index back to the merged DataFrame
    merged_df.set_index(series.index.names, inplace=True)

    # Convert the result back to a Series
    adjusted_series = merged_df['adjusted']

    return adjusted_series

class AdvancedTrafficModel(dict):
    task_rph_set = set({})   # set of columns holding rph for tasks

    def __init__(self, model):
        for (k,v) in model.items(): super().__setitem__(k,v)

    def min_task_item_recs_per_hour_multiplier(self, task_item, year, month):
        days_in_month = pd.Series(zip(year, month)).apply(lambda r: monthrange(*r)[1])
        #import pdb; pdb.set_trace()
        return task_item.push_frequency_per_month_min * \
            task_item.sending_devices_min * (month.isin(task_item.months_relevant)) \
            / (24 * days_in_month) 
    
    def max_task_item_recs_per_hour_multiplier(self, task_item, year, month):
        days_in_month = pd.Series(zip(year, month)).apply(lambda r: monthrange(*r)[1])
        return task_item.push_frequency_per_month_max * \
            task_item.sending_devices_max * (month.isin(task_item.months_relevant)) \
            / (24 * days_in_month)
    
    def generate_traffic(self, fromdate, todate, scenario, min_or_max="max"):
        self.traffic = make_blank_frame(fromdate, todate)
        
        self.traffic["base_recs"] = self["start_row_cnt"]

        # Note: ignores the base rate and growth rate; these are inferred from the scenario now
        # Also ignores the monthly variation, since the scenario controls this as well
        # We only use daily variation to tweak what the scenario specifies
        self.traffic["monthly"] = self.traffic["base_recs"]
            #adjust_by_matching_index(self.traffic["base_recs"]/self.traffic["base_recs"],  self["corrections_monthly"])
        self.traffic["hourly"] = adjust_by_matching_index(self.traffic["monthly"], self["corrections_hourly"])
        self.traffic["bandwidth"] = 0  # 0 for now; we'll add each schema to this
        self.scenario = scenario
        
        for task in scenario.tasks:
            if "task_" + task.name + "_lambda" not in self.traffic.columns:
                self.traffic["task_" + task.name + "_lambda"] = 0
                self.traffic["task_" + task.name + "_rph"] = 0
            if min_or_max == "min":
                self.traffic["task_" + task.name + "_lambda"] += self.traffic["hourly"] * \
                    self.min_task_item_recs_per_hour_multiplier(task, self.traffic.index.get_level_values("Year"), self.traffic.index.get_level_values("Month")).values
                # for each row, choose from poisson distribution given lambda value
            else:
                self.traffic["task_" + task.name + "_lambda"] += self.traffic["hourly"] * \
                    self.max_task_item_recs_per_hour_multiplier(task, self.traffic.index.get_level_values("Year"), self.traffic.index.get_level_values("Month")).values

            self.traffic["task_" + task.name + "_rph"] += np.random.poisson(self.traffic["task_" + task.name + "_lambda"])
            self.traffic["bandwidth"] += self.traffic["task_" + task.name + "_rph"] * task.size
            self.task_rph_set.add("task_" + task.name + "_rph")
        return self.traffic

    def serialize_forecast_to_file(self, filename):
        self.traffic.reset_index().to_csv(filename)

    def serialize_forecast(self):
        return self.traffic.reset_index().to_csv()

    def deserialize_forecast_from_file(self, filename):
        if os.path.exists(filename):
            self.traffic = pd.read_csv(filename).set_index(["Year","Month","Day","DOW","Hour"], inplace=False)
        else:
            raise Exception(f"File {filename} does not exist")
        
    def deserialize_forecast(self, serialized):
        self.traffic = pd.read_csv(io.StringIO(serialized)).set_index(["Year","Month","Day","DOW","Hour"], inplace=False)
        
    def serialize_parameters(self):
        serialized = {
            "start_row_cnt": self["start_row_cnt"],
            "corrections_monthly": serialize_series(self["corrections_monthly"].squeeze()),
            "corrections_hourly": serialize_mi_series(self["corrections_hourly"].squeeze()),
            "yearly_growth_rate": self["yearly_growth_rate"],
            "model_name": self["model_name"]
        }
        #print(serialized)
        return json.dumps(serialized)
    
    @classmethod
    def deserialize_parameters(cls, jsonstr):
        params = json.loads(jsonstr)
        t = AdvancedTrafficModel({})
        t["start_row_cnt"] = params["start_row_cnt"]
        t["corrections_monthly"] = deserialize_series(params["corrections_monthly"])
        t["corrections_hourly"] = deserialize_mi_series(params["corrections_hourly"])
        t["yearly_growth_rate"] = params["yearly_growth_rate"]
        t["model_name"] = params["model_name"]
        return t
    
    def calculate(self, pipeline_model):
        self.pipeline_model = pipeline_model
        if type(pipeline_model) is twin.NullModel:
            print("No pipeline model set; cannot calculate throughput")
            return
        if not hasattr(self, "traffic"):
            raise "Run generate_traffic first"
        if "queue_len" in self.traffic.columns:   # already calculated!
            return
        
        self.traffic["queue_len"] = 0
        self.traffic["throughput"] = 0
        self.traffic["latency_lifo"] = 0
        self.traffic["latency_fifo"] = 0
        self.traffic["pipeline_cost_per_rec"] = 0.0
        self.traffic["pipeline_cost"] = 0
        self.traffic["cumu_pipeline_cost"] = 0
        self.traffic["scaleout"] = 0
        queue = 0
        queue_worstcase_age_s = 0
        thruloc = self.traffic.columns.get_loc('throughput')
        latency_fifo = self.traffic.columns.get_loc('latency_fifo')
        hourloc = self.traffic.columns.get_loc("hourly")
        queueloc = self.traffic.columns.get_loc("queue_len")
        latency_lifo = self.traffic.columns.get_loc("latency_lifo")
        pipeline_cost_per_rec = self.traffic.columns.get_loc("pipeline_cost_per_rec")
        pipeline_cost = self.traffic.columns.get_loc("pipeline_cost")
        cumu_pipeline_cost = self.traffic.columns.get_loc("cumu_pipeline_cost")
        scaleout = self.traffic.columns.get_loc("scaleout")
        self.pipeline_model.reset()
        for p in range(len(self.traffic.throughput)):
            if self.traffic.index.get_level_values('Hour')[p] == 0 and self.traffic.index.get_level_values('Day')[p] == 1:
                print(f"Simulating year {self.traffic.index.get_level_values('Year')[p]} month {self.traffic.index.get_level_values('Month')[p]}/12")

            self.pipeline_model.input(self.traffic[self.task_rph_set].iloc[p].to_dict()) 
            self.traffic.iloc[p,thruloc] = self.pipeline_model.throughput_rph
            self.traffic.iloc[p,latency_fifo] = self.pipeline_model.latency_fifo_s
            #self.traffic.iloc[p,latency_lifo] = self.pipeline_model.latency_lifo_s
            #import pdb; pdb.set_trace()
            self.traffic.iloc[p,queueloc] = len(self.pipeline_model.queue)
            self.traffic.iloc[p,pipeline_cost] = self.pipeline_model.hourcost
            self.traffic.iloc[p,cumu_pipeline_cost] = self.pipeline_model.cumu_pipeline_cost
            self.traffic.iloc[p,pipeline_cost_per_rec] = self.pipeline_model.hourcost / self.pipeline_model.throughput_rph
            #self.traffic.iloc[p,scaleout] = self.pipeline_model.numproc
            
    def sla_check(self, sla):
        if not hasattr(self, "pipeline_model"):
            raise "Wind tunnel pipeline_model not set"
        pct_latency_met = (100.0*self.traffic.latency_fifo.lt(sla["latency_sla_limit"]).sum()/len(self.traffic))
        if pct_latency_met < sla["latency_sla_percent"]:
            print(f"Latency SLA not met: latency was only less than {sla['latency_sla_limit']}s/record {pct_latency_met}% of the time; it needed to be {sla['latency_sla_percent']}%")
        if pct_latency_met >= sla["latency_sla_percent"]:
            print(f"Latency SLA is met: latency was less than {sla['latency_sla_limit']}s/record {pct_latency_met}% of the time; it only needed to be met {sla['latency_sla_percent']}%")
        return {"sla_met": str(pct_latency_met >= sla["latency_sla_percent"]), "pct_latency_met": pct_latency_met}
            
def forecast(year, scenario, min_or_max="max",  from_cached=False):
    
    traffic_model_name = os.environ['TRAFFIC_MODEL_NAME']
    traffic_model = os.environ['TRAFFIC_MODEL']
    
    config = configuration.ConfigurationConnectionEnvVars()

    # if we're working from cache
    if from_cached:
        model = AdvancedTrafficModel.deserialize_parameters(metrics.redis.load_str("trafficmodel_params", traffic_model_name))
    else:
        model = AdvancedTrafficModel.deserialize_parameters(traffic_model)
        metrics.redis.save_str("trafficmodel_params", traffic_model_name, model.serialize_parameters())

    #model = TrafficModel.deserialize_parameters_from_file(open(f"fakeredis/trafficmodel_{traffic_model_name}.json").read())
    #model = AdvancedTrafficModel.deserialize_parameters(metrics.redis.load_str("trafficmodel_params", traffic_model_name))


    model.generate_traffic(datetime(year,1,1), datetime(year,12,31), scenario, min_or_max)

    #model.serialize_forecast(f"fakeredis/trafficmodel_{traffic_model_name}.csv")
    #print(f"Traffic model {traffic_model_name} saved to fakeredis/trafficmodel_{traffic_model_name}.csv")
    metrics.redis.save_str("advanced_trafficmodel_predictions_" + min_or_max, traffic_model_name, model.serialize_forecast())
    
    return model