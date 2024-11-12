"""
Module for generating pipeline configurations and job names.

Example:
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
"""


from typing import List
from pydantic import BaseModel, Field

# feel free to import this and extend it in your own code
class PipelineConfig(BaseModel):
    pipeline_key: str
    release: str
    family: str
    upload_type: str
    job_name_templates: List[str] = Field(
        description="List of job name templates to generate", 
        examples="['{release}-{family}-Oracle-Build-Images', '{release}-{family}-Oracle-{upload_type}-Upload-Image', '{release}-{family}-Oracle-{upload_type}-Test']"
    )

    @property
    def all_job_names(self):
        return [template.format(**self.model_dump()) for template in self.job_name_templates]

# this function is an example of how you could generate pipeline configurations
# this should work for all basic pipelines
def generate_pipeline_configs(
    pipeline_key: str,
    releases: List[str],
    families: List[str],
    upload_types: List[str],
    job_name_templates: List[str],
) -> List[PipelineConfig]:
    """
    Generates a list of pipeline configurations based on the provided parameters.

    Args:
        pipeline_key (str): The key identifying the pipeline.
        releases (List[str]): A list of release versions.
        families (List[str]): A list of family types.
        upload_types (List[str]): A list of upload types.
        job_name_templates (List[str]): A list of job name templates.

    Returns:
        List[PipelineConfig]: A list of generated pipeline configurations.

    Example:
        from cpc_jank_db.naming import generate_pipeline_configs

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
    """

    results = []
    for release in releases:
        for family in families:
            for upload_type in upload_types:
                results.append(PipelineConfig(
                    pipeline_key=pipeline_key,
                    release=release,
                    family=family,
                    upload_type=upload_type,
                    job_name_templates=job_name_templates,
                ))
    return results

def generate_all_job_names(
    pipeline_configs: List[PipelineConfig]
) -> List[str]:
    """
    Generates a list of all job names from a list of pipeline configurations.

    Args:
        pipeline_configs (List[PipelineConfig]): A list of pipeline configurations.

    Returns:
        List[str]: A list of all generated job names.
    """
    return [
        job_name
        for pipeline_config in pipeline_configs
        for job_name in pipeline_config.all_job_names
    ]
