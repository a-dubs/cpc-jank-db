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


import re
from typing import List, Literal
from pydantic import BaseModel, Field

suites = {
    "20.04": "focal",
    "22.04": "jammy",
    "24.04": "noble",
    "24.10": "oracular",
    "25.04": "plucky",
}

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
    def name(self):
        return f"{self.pipeline_key}-{self.release}-{self.family}-{self.upload_type}"

    @property
    def suite(self):
        return suites.get(self.release, None)

    @property
    def all_job_names(self):
        return [template.format(**self.model_dump()) for template in self.job_name_templates]
    
    def get_job_name(self, re_str: str):
        return next((job_name for job_name in self.all_job_names if re.findall(re_str, job_name.lower())), None)
    
    @property
    def test_job_name(self):
        return self.get_job_name(r"test")
    
    @property
    def build_job_name(self):   
        return self.get_job_name(r"build")
    
    @property
    def upload_job_name(self):
        return self.get_job_name(r"upload|register")


class CloudInitPipelineConfig(BaseModel):
    image_type: Literal["generic", "minimal"]
    suite: Literal["focal", "jammy", "noble", "oracular", "plucky"]
    cloud_name: Literal["azure", "gce", "ec2", "oci", "ibm", "lxd_vm", "lxd_container"]
    # cloud-init-integration-jammy-azure-generic
    job_name_template: str = "cloud-init-integration-{suite}-{cloud_name}-{image_type}"

    @classmethod
    def valid_image_types(cls):
        return ["generic", "minimal"]
    
    @classmethod
    def valid_suites(cls):
        return ["focal", "jammy", "noble", "oracular", "plucky"]
    
    @classmethod
    def valid_cloud_names(cls):
        return ["azure", "gce", "ec2", "oci", "ibm", "lxd_vm", "lxd_container"]

    @classmethod
    def generate_all_configs(cls) -> List["CloudInitPipelineConfig"]:
        results = []
        for image_type in cls.valid_image_types():
            for suite in cls.valid_suites():
                for cloud_name in cls.valid_cloud_names():
                    results.append(cls(image_type=image_type, suite=suite, cloud_name=cloud_name))
        return results

    @property
    def job_name(self):
        return self.job_name_template.format(**self.model_dump())

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

class ProjectConfig(BaseModel):
    name: str
    pipeline_configs: List[PipelineConfig]

    @property
    def all_job_names(self):
        return generate_all_job_names(self.pipeline_configs)
    
    @property
    def test_job_names(self):
        return [pipeline_config.test_job_name for pipeline_config in self.pipeline_configs]
    
    @property
    def build_job_names(self):
        return [pipeline_config.build_job_name for pipeline_config in self.pipeline_configs]
    
    @property
    def upload_job_names(self):
        return [pipeline_config.upload_job_name for pipeline_config in self.pipeline_configs]