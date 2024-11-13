from cpc_jank_db.naming import PipelineConfig, generate_pipeline_configs, generate_all_job_names
from cpc_jank_db.jenkins import collect_all_job_runs
from cpc_jank_db import db

########################################## Oracle ##########################################

# Oracle pipeline configurations
pipeline_key = "Oracle"
releases = ["20.04", "22.04", "24.04", "25.04"]
families = ["Base", "Minimal"]
upload_types = ["Daily"]
oracle_job_name_templates = [
    "{release}-{family}-Oracle-Build-Images",
    "{release}-{family}-Oracle-{upload_type}-Register-Image",
    "{release}-{family}-Oracle-{upload_type}-Test",
]

# generate pipeline configurations using above parameters
oracle_configs = generate_pipeline_configs(
    pipeline_key, releases, families, upload_types, oracle_job_name_templates
)

# generate all job names using the generated pipeline configurations
oracle_job_names = generate_all_job_names(oracle_configs)

print("job_names:", oracle_job_names)

# collect job runs for each job
for job_name in oracle_job_names:
    print("Collecting job runs for", job_name)
    job, job_runs = collect_all_job_runs(job_name)
    print(f"Collected {len(job_runs)} job runs for {job_name}")

# query db to verify that the job runs were saved
for job_name in oracle_job_names:
    runs = db.get_job_runs_for_job(job_name)
    print(f"Found {len(runs)} job runs for {job_name}")

########################################## IBM-Guest ##########################################

# IBM-Guest pipeline configurations
pipeline_key = "IBM-Guest"
releases = ["20.04", "22.04", "24.04", "25.04"]
families = ["Base"]
upload_types = ["Daily"]
ibm_job_name_templates = [
    "{release}-{family}-{pipeline_key}-Build-Images",
    "{release}-{family}-{pipeline_key}-{upload_type}-Upload-Image",
    "{release}-{family}-{pipeline_key}-{upload_type}-Test",
]

# generate pipeline configurations using above parameters
ibm_configs = generate_pipeline_configs(
    pipeline_key, releases, families, upload_types, ibm_job_name_templates
)

# generate all job names using the generated pipeline configurations
ibm_job_names = generate_all_job_names(ibm_configs)

print("ibm_job_names:", ibm_job_names)

# collect job runs for each job
for job_name in ibm_job_names:
    print("Collecting job runs for", job_name)
    job, job_runs = collect_all_job_runs(job_name)
    print(f"Collected {len(job_runs)} job runs for {job_name}")

# query db to verify that the job runs were saved
for job_name in ibm_job_names:
    runs = db.get_job_runs_for_job(job_name)
    print(f"Found {len(runs)} job runs for {job_name}")

########################################## OKE ##########################################

# OKE pipeline configurations
pipeline_keys = ["OKE-1.27", "OKE-1.29"]
releases = ["20.04", "22.04", "24.04"]
families = ["Minimal"]
upload_types = ["Daily"]

oke_job_name_templates = [
    "{release}-{family}-{pipeline_key}-{upload_type}-Register-Image",
    "{release}-{family}-{pipeline_key}-{upload_type}-CTF-Test",
    "{release}-{family}-{pipeline_key}-{upload_type}-Sonobuoy-Test-Run",
]

# generate pipeline configurations using above parameters
oke_configs = [config
    for pipeline_key in pipeline_keys
    for config in generate_pipeline_configs(
        pipeline_key,
        releases,
        families,
        upload_types,
        oke_job_name_templates,
    )
]

# generate all job names using the generated pipeline configurations
oke_job_names = generate_all_job_names(oke_configs)

print("oke_job_names:", oke_job_names)

# collect job runs for each job
for job_name in oke_job_names:
    print("Collecting job runs for", job_name)
    job, job_runs = collect_all_job_runs(job_name)
    print(f"Collected {len(job_runs)} job runs for {job_name}")

# query db to verify that the job runs were saved
for job_name in oke_job_names:
    runs = db.get_job_runs_for_job(job_name)
    print(f"Found {len(runs)} job runs for {job_name}")
