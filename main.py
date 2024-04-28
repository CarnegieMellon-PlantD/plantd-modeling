from plantd_modeling import build, trafficmodel, twin, advanced_trafficmodel, build_advanced
import sys
from plantd_modeling import configuration, metrics
import json
import os
import time

ARBITRARY_FUTURE_YEAR = 2030

if sys.argv[1] == "sim_all":
    try:
        from_cached = False
        if len(sys.argv) >= 3 and sys.argv[2] == "from_cached":
            from_cached = True
        else:
            print("add 'from_cached' to use cached metrics")
            #quit()

        config = configuration.ConfigurationConnectionEnvVars()

        if len(config.experiments) == 0:
            if config.scenario is None: raise Exception("CONFIGURATION ERROR: To simulate without a digital twin, you need a scenario")
        
        if config.scenario is None:  # Could also check for schemaaware as DIGITAL_TWIN_TYPE, but redundant
            tmodel = trafficmodel.forecast(ARBITRARY_FUTURE_YEAR, from_cached=from_cached)
            pmodel = build.build_twin(os.environ('MODEL_TYPE','simple'), from_cached=from_cached)
        else:
            tmodel = advanced_trafficmodel.forecast(ARBITRARY_FUTURE_YEAR, config.scenario, from_cached=from_cached)
            pmodel = build_advanced.build_advanced_twin(os.environ('MODEL_TYPE','simple'), from_cached=from_cached)
        if config.netcosts:
            try:
                netcost_results = config.netcosts.apply(tmodel)
            except Exception as e:
                print("Netcosts not applied", e)
            #metrics.redis.save_str("netcost_predictions", os.environ["SCENARIO_NAME"], config.netcosts.serialize_monthly_totals())
        pmodel.simulate(tmodel)
    

        #metrics.redis.save_str("simulation_results", os.environ["SCENARIO_NAME"], twin.serialize_simulation_results())
    except Exception as e:
        print("SIMULATION_STATUS: Failure")
        print(f"ERROR_REASON: {type(e)}: {e}")
        raise e
    print("SIMULATION_STATUS: Success")
else:
    print("Unknown command")

