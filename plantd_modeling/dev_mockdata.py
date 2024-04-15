import click
import redis
from pandas import pd
import io

@click.command()
@click.option('--redis-host', help='Redis host', default='localhost')
@click.option('--redis-password', help='Redis password', default='')
@click.option('--regex', help='Regex describing keys to list', default='*')
def characterize_redis(redis_host, redis_password, regex):
    # Connect to Redis
    r = redis.Redis.from_url(f'redis://{redis_host}', password=redis_password)

    # Get all keys matching the regex
    keys = r.keys(regex)

    # Iterate through the matching keys
    for key in keys:
        # Open and read the key
        value = r.get(key)

        # read value as a csv file and 
        # convert to a pandas dataframe
        df = pd.read_csv(io.StringIO(value), index_col=0, parse_dates=True)
        # summarize df
        print(df.describe())


if __name__ == '__main__':
    characterize_redis()
    #mockup_redis()
