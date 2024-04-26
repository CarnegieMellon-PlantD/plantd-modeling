from plantd_modeling import build, trafficmodel, twin, advanced_trafficmodel, build_advanced
import sys
from plantd_modeling import configuration, metrics
import json
import os
import time

ARBITRARY_FUTURE_YEAR = 2030

if sys.argv[1] == "sim_all_old":
    try:
        from_cached = False
        if len(sys.argv) >= 3 and sys.argv[2] == "from_cached":
            from_cached = True
        else:
            print("add 'from_cached' to use cached metrics")
            #quit()

        #import pdb; pdb.set_trace()
        config = configuration.ConfigurationConnectionEnvVars()
        pmodel = build.build_twin(os.environ['MODEL_TYPE'], from_cached=from_cached)
        tmodel = trafficmodel.forecast(ARBITRARY_FUTURE_YEAR)
        netcost_results = config.netcosts.apply(tmodel)
        twin.simulate(pmodel, tmodel)
    except Exception as e:
        print("SIMULATION_STATUS: Failure")
        print(f"ERROR_REASON: {type(e)}: {e}")
        raise e
    print("SIMULATION_STATUS: Success")
elif sys.argv[1] == "advanced_net_cost_only":
    try:
        from_cached = False
        if len(sys.argv) >= 3 and sys.argv[2] == "from_cached":
            from_cached = True
        else:
            print("add 'from_cached' to use cached metrics")
            #quit()

        config = configuration.ConfigurationConnectionEnvVars()
        tmodel = advanced_trafficmodel.forecast(ARBITRARY_FUTURE_YEAR, config.scenario)
        netcost_results = config.netcosts.apply(tmodel)
        metrics.redis.save_str("netcost_predictions", os.environ["SCENARIO_NAME"], config.netcosts.serialize_monthly_totals())
    except Exception as e:
        print("SIMULATION_STATUS: Failure")
        print(f"ERROR_REASON: {type(e)}: {e}")
        raise e
    print("SIMULATION_STATUS: Success")
elif sys.argv[1] == "sim_all":
    try:
        from_cached = False
        if len(sys.argv) >= 3 and sys.argv[2] == "from_cached":
            from_cached = True
        else:
            print("add 'from_cached' to use cached metrics")
            #quit()

        config = configuration.ConfigurationConnectionEnvVars()

        if config.scenario is None:  # Could also check for schemaaware as DIGITAL_TWIN_TYPE, but redundant
            tmodel = trafficmodel.forecast(ARBITRARY_FUTURE_YEAR, from_cached=from_cached)
            pmodel = build.build_twin(os.environ['MODEL_TYPE'], from_cached=from_cached)
        else:
            tmodel = advanced_trafficmodel.forecast(ARBITRARY_FUTURE_YEAR, config.scenario, from_cached=from_cached)
            pmodel = build_advanced.build_advanced_twin(os.environ['MODEL_TYPE'], from_cached=from_cached)
        if config.netcosts:
            try:
                netcost_results = config.netcosts.apply(tmodel)
            except Exception as e:
                print("Netcosts not applied", e)
            #metrics.redis.save_str("netcost_predictions", os.environ["SCENARIO_NAME"], config.netcosts.serialize_monthly_totals())
        twin.simulate(pmodel, tmodel)
    

        #metrics.redis.save_str("simulation_results", os.environ["SCENARIO_NAME"], twin.serialize_simulation_results())
    except Exception as e:
        print("SIMULATION_STATUS: Failure")
        print(f"ERROR_REASON: {type(e)}: {e}")
        raise e
    print("SIMULATION_STATUS: Success")
elif sys.argv[1] == "convert":
    # list all files in directory fakeredis. For each of them, load the file, and save it to redis
    for f in os.listdir("fakeredis"):
        if f.startswith("trafficmodel_"):
            print(f)
            trafficmodel.deserialize_parameters(open(f"fakeredis/{f}").read())
            metrics.redis.save_type("trafficmodel", f[13:-5],trafficmodel.serialize_parameters())
        #elif f.startswith("experiment_"):
        #    print(f)
        #    configuration.Experiment.deserialize(open(f"fakeredis/{f}").read())
        #    metrics.redis.save_type("experiment", f[11:-5],configuration.Experiment.serialize())
        else:
            print(f"Unknown file type {f}")
    
elif sys.argv[1] == "scenario_sim_all":
    try:
        from_cached = True
        if len(sys.argv) >= 3 and sys.argv[2] == "from_cached":
            from_cached = True
        else:
            print("add 'from_cached' to use cached metrics")
            #quit()

        pmodel = build.build_twin(os.environ['MODEL_TYPE'], from_cached=from_cached)
       
        tmodel = advanced_trafficmodel.forecast(ARBITRARY_FUTURE_YEAR, configuration.scenario)
        netcost_results = configuration.netcosts.apply(tmodel)
        print("TO DO -- SIMULATE")
    except Exception as e:
        print("SIMULATION_STATUS: Failure")
        print(f"ERROR_REASON: {type(e)}: {e}")
        raise e
    print("SIMULATION_STATUS: Success")
    
elif sys.argv[1] == "build":
    build.build_twin(os.environ['MODEL_TYPE'])
elif sys.argv[1] == "forecast":
    # env will have forecast parameters, and a name for the forecast
    # this will write the forecast to a file named <name>.json
    trafficmodel.forecast(ARBITRARY_FUTURE_YEAR)
elif sys.argv[1] == "simulate":
    # env will have forecast *name* and a twin name
    # Output will go into a file 
    # output several traces called <twin name>-<forecast name>-<trace type>.json
    #   - <trace type> is one of "load", "latency", "throughput", "cost", "queue_length"
    # output statistics about the simulation
    #   - total cost
    #   - average throughput, latency, queue length
    #   - worst case latency, queue length
    twin.simulate()
elif sys.argv[1] == "end_detect":
    config = configuration.ConfigurationConnectionEnvVars()
    DEBOUNCE_PERIOD = os.environ['DEBOUNCE_PERIOD']
    POD_DETACH_ADJUSTMENT = os.environ['POD_DETACH_ADJUSTMENT']
    experiment = list(config.experiments.keys())[0]   # Should just be one experiment

    baseline = metrics.get_stages_levels(experiment, DEBOUNCE_PERIOD, before_start = DEBOUNCE_PERIOD*2)
    in_progress = False
    while True:
        time.sleep(DEBOUNCE_PERIOD)
        recent_pd = metrics.get_stages_levels(experiment, DEBOUNCE_PERIOD)
        
        if in_progress == False:
            crossing_info = metrics.detect_crossing(baseline, recent_pd)
            if crossing_info is not None and  crossing_info["transition_direction"] == "upwards":
                in_progress = True
        else:
            crossing_info = metrics.detect_crossing(baseline, recent_pd)
            if crossing_info is not None and  crossing_info["transition_direction"] == "downwards":
                now = time.time()
                wait_time = POD_DETACH_ADJUSTMENT - (now - crossing_info["transition_time"])
                print("PROCESS ENDED AT ", crossing_info["transition_time"], " waiting ", )
                time.sleep (wait_time)
                print ('PROCESS STOPPED AT {crossing_info["transition_time"]}; waiting until {POD_DETACH_ADJUSTMENT - (now - crossing_info["transition_time"])}')
                exit()
elif sys.argv[1] == "test_write":
    exps = build.build_model()
    for e in exps:
        exps[e].save_file(f"{e.dotted_name}.json")
elif sys.argv[1] == "test_read":
    exp = configuration.Experiment.load_file(sys.argv[2])
    print(json.dumps(exp.serialize(), indent=4))
else:
    print("Unknown command")

