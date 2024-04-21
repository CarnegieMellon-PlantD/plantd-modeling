import pandas as pd
import json

# Create a MultiIndex Series
index = pd.MultiIndex.from_tuples([(2021, 4), (2021, 5), (2022, 6)], names=['Year', 'Month'])
x = pd.Series([1, 2, 3], index=index)

# Manually serialize data and index
serialized = json.dumps({
    "data": x.tolist(),
    "index": x.index.tolist(),
    "index_names": x.index.names
})




# Manually deserialize data and index
deserialized = json.loads(serialized)
new_index = pd.MultiIndex.from_tuples(deserialized["index"], names=deserialized["index_names"])
x_restored = pd.Series(deserialized["data"], index=new_index)

print(x_restored)