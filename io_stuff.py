from cpc_jank_db.naming import PipelineConfig, generate_pipeline_configs, generate_all_job_names
from cpc_jank_db.jenkins import collect_all_job_runs

pipeline_key = "Oracle"
releases = ["20.04", "22.04", "24.04", "25.04"]
families = ["Base"]
upload_types = ["Daily"]
job_name_templates = [
    "{release}-{family}-Oracle-Build-Images",
    "{release}-{family}-Oracle-{upload_type}-Upload-Image",
    "{release}-{family}-Oracle-{upload_type}-Test",
]

configs = generate_pipeline_configs(
    pipeline_key, releases, families, upload_types, job_name_templates
)

job_names = generate_all_job_names(configs)

for job_name in job_names:
    print("Collecting job runs for", job_name)
    job, job_runs = collect_all_job_runs(job_name)
    print(f"Collected {len(job_runs)} job runs for {job_name}")


