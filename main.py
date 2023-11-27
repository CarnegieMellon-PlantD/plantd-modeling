from plantd_modeling import build, trafficmodel, twin
import sys
from plantd_modeling import configuration, metrics
import json
import os

if sys.argv[1] == "sim_all":
    try:
        from_cached = False
        if len(sys.argv) >= 3 and sys.argv[2] == "from_cached":
            from_cached = True
        else:
            print("add 'from_cached' to use cached metrics")

        import pdb; pdb.set_trace()
        pmodel = build.build_twin(os.environ['MODEL_TYPE'], from_cached=from_cached)
        tmodel = trafficmodel.forecast(2025)
        twin.simulate(pmodel, tmodel)
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
    
elif sys.argv[1] == "build":
    build.build_twin(os.environ['MODEL_TYPE'])
elif sys.argv[1] == "forecast":
    # env will have forecast parameters, and a name for the forecast
    # this will write the forecast to a file named <name>.json
    trafficmodel.forecast(2025)
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
    print("End Detect (not implemented)")
elif sys.argv[1] == "test_write":
    exps = build.build_model()
    for e in exps:
        exps[e].save_file(f"{e.dotted_name}.json")
elif sys.argv[1] == "test_read":
    exp = configuration.Experiment.load_file(sys.argv[2])
    print(json.dumps(exp.serialize(), indent=4))
else:
    print("Unknown command")

