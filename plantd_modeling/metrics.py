from plantd_modeling.configuration import Experiment
from datetime import timedelta, datetime
import requests
import json
import pandas as pd

REALTIME_CALLS_QUERY = 'calls_total{{job="{params.name}", namespace="{params.namespace}"}}'
REALTIME_THROUGHPUT_QUERY = 'sum by(span_name)(irate(calls_total{{status_code="STATUS_CODE_UNSET", job="{params.name}", namespace="{params.namespace}"}}[{step}s]))'
REALTIME_LATENCY_QUERY = 'irate(duration_milliseconds_sum{status_code="STATUS_CODE_UNSET", job="{params.name}", namespace="{params.namespace}"}[30s]) / irate(duration_milliseconds_count{status_code="STATUS_CODE_UNSET", job="{params.name}", namespace="{params.namespace}"}[30s])'

class Metrics:
    def __init__(self, prometheus_host) -> None:
        self.prometheus_host = prometheus_host
        
    def get_metrics(self, experiment: Experiment):
        url = f"{self.prometheus_host}/api/v1/query_range"
        step_interval = 30 # 180
        start_ts = experiment.start_time.timestamp() - step_interval*15
        #end_ts = experiment.end_time.timestamp()
        end_ts = datetime.now().timestamp()

        query = REALTIME_THROUGHPUT_QUERY.format(params=experiment.experiment_name, step={step_interval})
        print(query, datetime.utcfromtimestamp(start_ts), datetime.utcfromtimestamp(end_ts), step_interval)
        print(url)  
        print(query)
    
        response = requests.get(url, params={'query': query, 'start': start_ts, 'end': end_ts, 'step': step_interval}, 
            #auth=('prometheus', prometheus_password), 
            verify=False, stream=False)
        response.raise_for_status()
        #import pdb; pdb.set_trace()

        dfs = []
        for result in response.json()['data']['result']:
            span = result['metric']['span_name']
            df = pd.DataFrame(result['values'], columns=['time', span])
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df.set_index('time', inplace=True)
            dfs.append(df)

        if len(dfs) > 0:
            df = pd.concat(dfs, axis=1)
        else:
            df = pd.DataFrame()

        return df