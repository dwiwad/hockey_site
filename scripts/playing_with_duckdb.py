import duckdb
import configparser
import os

# Create connection and set up S3 access
con = duckdb.connect()
con.execute("INSTALL httpfs; LOAD httpfs;")
con.execute("SET s3_region='us-east-2';")  # adjust if different region

# Read from ~/.aws/credentials
config = configparser.ConfigParser()
config.read(os.path.expanduser('~/.aws/credentials'))

con.execute(f"""
    SET s3_region='us-east-2';
    SET s3_access_key_id='{config['default']['aws_access_key_id']}';
    SET s3_secret_access_key='{config['default']['aws_secret_access_key']}';
""")

# Peek at structure (just first 100 rows)
df_sample = con.execute("""
    SELECT * 
    FROM read_json_auto('s3://hockey-decoded/static-ds-analyses/total-depth-index/all-seasons/all_pbp_20102025.ndjson')
    LIMIT 100
""").df()

print(df_sample.columns.tolist())
df_sample.head()


con.execute("""
      COPY (
          SELECT *
          FROM read_json_auto(
              's3://hockey-decoded/static-ds-analyses/total-depth-index/all-seasons/all_pbp_20102025.ndjson',
              sample_size=-1,
              union_by_name=true
          )
      )
      TO 's3://hockey-decoded/parquet/all_pbp_20102025.parquet' (FORMAT PARQUET)
  """)