from plantd_modeling import build
import sys
from plantd_modeling import configuration
import json


if sys.argv[1] == "build":
    build.build_model()
elif sys.argv[1] == "simulate":
    print("Simulate (not implemented)")
elif sys.argv[1] == "forecast":
    print("Forecast (not implemented)")
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

