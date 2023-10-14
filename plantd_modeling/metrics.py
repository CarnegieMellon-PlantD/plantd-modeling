from plantd_modeling.configuration import Experiment
from datetime import timedelta, datetime
import requests
import json
import pandas as pd

class Metrics:
    def __init__(self, prometheus_host) -> None:
        self.prometheus_host = prometheus_host
        
    def get_metrics(self, experiment: Experiment):
        url = f"{self.prometheus_host}/api/v1/query_range"
        start_ts = experiment.start_time.timestamp()
        end_ts = experiment.end_time.timestamp()
        # Kluge for testing
        start_ts = datetime.now().timestamp() - 3600
        end_ts = datetime.now().timestamp()
        step_interval = 60
        query = f'calls_total{{job="{experiment.experiment_name.name}", namespace="{experiment.experiment_name.namespace}"}}'
        print(query, datetime.utcfromtimestamp(start_ts), datetime.utcfromtimestamp(end_ts), step_interval)
        # kluge for testing
        #query = f'calls_total'
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
            if result['metric']['status_code'] != 'STATUS_CODE_UNSET':
                span += f"_{result['metric']['status_code']}"
            df = pd.DataFrame(result['values'], columns=['time', span])
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df.set_index('time', inplace=True)
            dfs.append(df)

        if len(dfs) > 0:
            df = pd.concat(dfs, axis=1)
        else:
            df = pd.DataFrame()

        return df