import sys
import json
import boto3
from awsglue.utils import getResolvedOptions
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.context import SparkContext
from pyspark.sql import Row
from pyspark.sql.types import *
from delta.tables import DeltaTable
from pyspark.sql.functions import col, lit, to_date, from_json

# ---------- Glue boiler-plate ----------
args = getResolvedOptions(sys.argv, ["JOB_NAME"])
sc = SparkContext()
glue_ctx = GlueContext(sc)
spark = glue_ctx.spark_session
job = Job(glue_ctx)
logger = glue_ctx.get_logger()
job.init(args["JOB_NAME"], args)

# Set the logging level for the root logger to WARN
sc.setLogLevel("INFO")

# Set the logging level for specific loggers to ERROR
log4j = sc._jvm.org.apache.log4j
# log4j.LogManager.getLogger("org.apache.spark.sql.gluestreaming").setLevel(log4j.Level.ERROR)
# log4j.LogManager.getLogger("org.apache.spark.sql.execution.streaming").setLevel(log4j.Level.ERROR)
# log4j.LogManager.getLogger("com.amazon.ws.emr.hadoop.fs.s3n").setLevel(log4j.Level.ERROR)
# log4j.LogManager.getLogger("com.amazonaws.services.glue").setLevel(log4j.Level.ERROR)


# ---------- Kinesis stream configuration ----------
stream_name = "sample_mcp_stream"
partition_key = "mcpId"
checkpoint_location = "s3://azuga-udpdp-iceberg/checkpoint/sample_mcp_stream_checkpoint/"

# Define the schema for the data in the Kinesis stream
context_schema = StructType([
    StructField("ruleId",        StringType(), True),
    StructField("operation",     StringType(), True),
    StructField("fetch_time",    StringType(), True),
    StructField("processed_time",StringType(), True),
    StructField("retry_count",   IntegerType(), True),
    StructField("schema", StructType([
        StructField("registryName", StringType(), True),
        StructField("schemaName",   StringType(), True),
        StructField("version",      StringType(), True)
    ]), True),
    StructField("s3Path", StringType(), True),
    StructField("partitionKey", StringType(), True)
])

payload_schema = StructType([
    StructField("data", MapType(StringType(), StringType()), True)
])

full_schema = StructType([
    StructField("mcpId",      StringType(), True),
    StructField("mcpContext", context_schema, True),
    StructField("payload",    payload_schema, True)
])

# ---------- helper: JSON-Schema → Spark ----------
def convert_type(type_def):
    t = type_def.get("type")
    if isinstance(t, list):           # ["integer", "null"]
        t = next(x for x in t if x != "null")
    if t == "string":
        return StringType()
    elif t == "integer":
        return IntegerType()
    elif t == "number":
        return DoubleType()
    elif t == "boolean":
        return BooleanType()
    elif t == "object":
        return StructType([
            StructField(k, convert_type(v), True)
            for k, v in type_def.get("properties", {}).items()
        ])
    elif t == "array":
        return ArrayType(convert_type(type_def.get("items")))
    return StringType()

def json_schema_to_struct(schema):
    return StructType([
        StructField(k, convert_type(v), True)
        for k, v in schema.get("properties", {}).items()
    ])

# ---------- helper: cast dict values to exact types ----------
def cast_values_to_schema(raw_dict, json_schema):
    typed = {}
    for col_name, spec in json_schema.get("properties", {}).items():
        val = raw_dict.get(col_name)
        type_info = spec.get("type")

        # handle "type": ["integer", "null"]  or  "type": "integer"
        if isinstance(type_info, list):
            primitive_type = next(t for t in type_info if t != "null")
            nullable = "null" in type_info
        else:
            primitive_type = type_info
            nullable = True

        if val is None and nullable:
            typed[col_name] = None
            continue

        try:
            if primitive_type == "integer":
                typed[col_name] = int(val)
            elif primitive_type == "number":
                typed[col_name] = float(val)
            elif primitive_type == "boolean":
                typed[col_name] = val if isinstance(val, bool) else (str(val).lower() == "true")
            else:                           # string
                typed[col_name] = str(val)
        except (ValueError, TypeError):
            typed[col_name] = str(val)      # fallback
    return typed

# ---------- main processing ----------
def process_batch(df, batch_id):
    logger.info(f"=== Processing Batch ID: {batch_id} ===")
    if df.isEmpty():
        return

    for row in df.collect():
        mcp_id      = row["mcpId"]
        mcp_context = row["mcpContext"]
        mcp_context_store = row["mcpContext"].asDict()  # Convert Row to dictionary
        mcp_context_json = json.dumps(mcp_context_store)  # Serialize dictionary to JSON
         # Log the type and content of mcp_context
        logger.info(f"++++++++++++++++Type of mcp_context: {type(mcp_context_store)}")
        logger.info(f"++++++++++++++++Content of mcp_context: {mcp_context_store}")
        logger.info(f"++++++++++++++++Content of mcp_context_json: {mcp_context_json}")

        # Log the serialized JSON string
        logger.info(f"++++++++++++++++++++++++++++mcp_context_json is {mcp_context_json}")
        
        
        payload_raw = row["payload"]["data"]  # dict

        registry    = mcp_context["schema"]["registryName"]
        schema_name = mcp_context["schema"]["schemaName"]
        version     = str(mcp_context["schema"]["version"])
        s3_path     = mcp_context["s3Path"]
        op          = mcp_context["operation"]

        # download schema from Glue Schema Registry
        try:
            glue_client = boto3.client("glue", region_name="us-west-2")
            schema_resp = glue_client.get_schema_version(
                SchemaId={"SchemaName": schema_name, "RegistryName": registry},
                SchemaVersionNumber={"VersionNumber": int(version)}
            )
            schema_def   = json.loads(schema_resp["SchemaDefinition"])
            spark_schema = json_schema_to_struct(schema_def)
            logger.info(f"+++++++++++++++++schema_def is {schema_def}")
            logger.info(f"+++++++++++++++++spark_schema is {spark_schema}")
        except boto3.exceptions.Boto3Error as e:
            logger.error(f"+++++++++++++++++An error occurred with Boto3: {e}")
            continue
        except json.JSONDecodeError as e:
            logger.error(f"+++++++++++++++++Error decoding JSON: {e}")
            continue
        except ValueError as e:
            logger.error(f"+++++++++++++++++Value error: {e}")
            continue
        except Exception as e:
            logger.error(f"+++++++++++++++++An unexpected error occurred: {e}")
            continue
        
        
        # coerce every column to exact type defined in schema
        typed_dict = cast_values_to_schema(
                {k: v for k, v in payload_raw.items()},          # <— good
                schema_def
        )

        payload_json = json.dumps(typed_dict, separators=(',', ':'))
        logger.info(f"+++++++++++++++++++++++++payload_json is {payload_json}")
        payload_df   = spark.read.json(
            spark.sparkContext.parallelize([payload_json]),
            schema=spark_schema
        )

        enriched_df = payload_df \
            .withColumn("mcpId", lit(mcp_id)) \
            .withColumn("mcpContext", lit(mcp_context_json))

        logger.info(f"Writing to path: {s3_path} | Operation: {op} | Record count: {enriched_df.count()}")
        
        # Extract partition key and create a partition column
        partition_key = mcp_context_store.get("partitionKey", "createTime")
        if partition_key is None:
            logger.error("+++++++++++++++++++++++Partition key is missing or null")
            continue

        enriched_df = enriched_df.withColumn("partition_date", to_date(col(partition_key)))

        # write/merge into Delta
        if op in ("merge", "insert", "update", "load"):
            if DeltaTable.isDeltaTable(spark, s3_path):
                delta_table = DeltaTable.forPath(spark, s3_path)
                (delta_table.alias("tgt")
                 .merge(enriched_df.alias("src"), "tgt.id = src.id")
                 .whenMatchedUpdateAll()
                 .whenNotMatchedInsertAll()
                 .execute())
            else:
                enriched_df.coalesce(1).write.partitionBy("partition_date").format("delta").mode("overwrite").save(s3_path)

        elif op == "delete":
            if DeltaTable.isDeltaTable(spark, s3_path):
                delta_table = DeltaTable.forPath(spark, s3_path)
                for id_val in enriched_df.select("id").distinct().rdd.flatMap(lambda x: x).collect():
                    delta_table.delete(f"id = '{id_val}'")

# ---------- read from Kinesis stream ----------
kinesis_df = spark.readStream \
    .format("kinesis") \
    .option("streamName", stream_name) \
    .option("endpointUrl", "https://kinesis.us-west-2.amazonaws.com") \
    .option("startingposition", "LATEST") \
    .option("region", "us-west-2") \
    .load()

# Parse the JSON data from the Kinesis stream
parsed_df = kinesis_df.selectExpr("CAST(data AS STRING) as json_data") \
    .select(from_json(col("json_data"), full_schema).alias("data")) \
    .select("data.*")

# Process each batch of data with checkpointing
query = parsed_df.writeStream \
    .foreachBatch(process_batch) \
    .option("checkpointLocation", checkpoint_location) \
    .start()

query.awaitTermination()
job.commit()
