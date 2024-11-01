from pprint import pprint
from models import *
import db
import results_parser
from results_parser import FailedTestDetails, FailedTestRun
from pydantic import BaseModel
from typing import List, Optional

# for each job in the job database, keep all that have "Test" in the name
jobs = db.get_all_jobs_matching_name("Test")

# for each job, get the most recent job run
job_runs = [db.get_most_recent_job_run(job.name) for job in jobs]

# create function that creates list of tests that failed and the number of times it failed out of the total number of times it ran
# i.e. "- test1 (1/5)"
def make_test_failures_list(job_run: TestMatrixJobRun) -> List[str]:
    stats = results_parser.get_test_stats(job_run)
    failed_tests = []
    for test_name, test_stats in stats.items():
        if test_stats["failed"] > 0:
            failed_tests.append(f"- {test_name} ({test_stats['failed']}/{test_stats['succeeded'] + test_stats['skipped'] + test_stats['failed']})")
    return failed_tests

target_job_name = "24.04-Base-Oracle-Daily-Test"
# Get the job from the database
target_job = db.get_most_recent_job_run(target_job_name)

class BuildJobInfo(BaseModel):
    result: str

    @classmethod
    def from_job_run(cls, matrix_job_run: MatrixJobRun):
        return cls(result=matrix_job_run.result)

class UploadJobInfo(BaseModel):
    result: str

    @classmethod
    def from_job_run(cls, matrix_job_run: MatrixJobRun):
        return cls(result=matrix_job_run.result)

class MatrixResults(BaseModel):
    failure: int
    success: int
    unstable: int
    aborted: int

    @classmethod
    def from_job_run(cls, matrix_job_run: MatrixJobRun):
        results = results_parser.get_matrix_job_results_stats(matrix_job_run)
        return cls(
            failure=results["FAILURE"],
            success=results["SUCCESS"],
            unstable=results["UNSTABLE"],
            aborted=results["ABORTED"],
        )

class TestJobInfo(BaseModel):
    result: str
    matrix_results: MatrixResults

    @classmethod
    def from_job_run(cls, matrix_job_run: MatrixJobRun):
        return cls(
            result=matrix_job_run.result,
            matrix_results=MatrixResults.from_job_run(matrix_job_run),
        )

class PipelineRunInformation(BaseModel):
    suite: str
    family: str
    serial: str
    build_job_info: BuildJobInfo
    upload_job_info: UploadJobInfo
    test_job_info: TestJobInfo
    test_failures: List[FailedTestDetails]

    @classmethod
    def from_job_run(
        cls,
        *,
        build_job_run: MatrixJobRun, 
        upload_job_run: MatrixJobRun,
        test_job_run: TestMatrixJobRun,
    ):
        return cls(
            family="Base" if "base" in test_job_run.name.lower() else "Minimal",
            suite=test_job_run.suite,
            serial=test_job_run.serial,
            build_job_info=BuildJobInfo(result="SUCCESS"),
            upload_job_info=UploadJobInfo(result="SUCCESS"),
            test_job_info=TestJobInfo.from_job_run(test_job_run),
            test_failures=results_parser.get_failed_test_details(test_job_run),
        )

class ProjectInformation(BaseModel):
    name: str
    pipeline_runs: List[PipelineRunInformation]

class PipelineConfig(BaseModel):
    pipeline_key: str
    release: str
    family: str
    upload_type: str

class JobNamer(BaseModel):
    build_name_template: str
    upload_name_template: str
    test_name_template: str

    def build_job_name(self, pipeline_config: PipelineConfig):
        return self.build_name_template.format(**pipeline_config.model_dump())
    
    def upload_job_name(self, pipeline_config: PipelineConfig):
        return self.upload_name_template.format(**pipeline_config.model_dump())
    
    def test_job_name(self, pipeline_config: PipelineConfig):
        return self.test_name_template.format(**pipeline_config.model_dump())



def generate_ibm_guest_pipeline_configs() -> List[PipelineConfig]:
    releases = ["20.04", "22.04", "24.04", "24.10", "25.04"]
    families = ["Base"]
    upload_types = ["Daily"]

    results = []
    for release in releases:
        for family in families:
            for upload_type in upload_types:
                results.append(PipelineConfig(
                    pipeline_key="IBM-Guest",
                    release=release,
                    family=family,
                    upload_type=upload_type,
                ))
    return results

def generate_oracle_pipeline_configs() -> List[PipelineConfig]:
    releases = ["20.04", "22.04", "24.04", "24.10", "25.04"]
    families = ["Base", "Minimal"]
    upload_types = ["Daily"]

    results = []
    for release in releases:
        for family in families:
                for upload_type in upload_types:
                    results.append(PipelineConfig(
                        pipeline_key="Oracle",
                        release=release,
                        family=family,
                        upload_type=upload_type,
                    ))
    return results


ibm_guest_job_namer = JobNamer(
    build_name_template="{release}-{family}-IBM-Guest-Build-Images",
    upload_name_template="{release}-{family}-IBM-Guest-{upload_type}-Upload-Image",
    test_name_template="{release}-{family}-IBM-Guest-{upload_type}-Test",
)

oracle_job_namer = JobNamer(
    build_name_template="{release}-{family}-Oracle-Build-Images",
    upload_name_template="{release}-{family}-Oracle-{upload_type}-Upload-Image",
    test_name_template="{release}-{family}-Oracle-{upload_type}-Test",
)

class ProjectConfig(BaseModel):
    name: str
    pipeline_configs: List[PipelineConfig]
    job_namer: JobNamer


ORACLE_PROJECT_CONFIG = ProjectConfig(
    name="Oracle",
    pipeline_configs=generate_oracle_pipeline_configs(),
    job_namer=oracle_job_namer,
)

IBM_GUEST_PROJECT_CONFIG = ProjectConfig(
    name="IBM-Guest",
    pipeline_configs=generate_ibm_guest_pipeline_configs(),
    job_namer=ibm_guest_job_namer,
)

def get_current_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

class HTMLReportInformation(BaseModel):
    timestamp: str = Field(default_factory=get_current_timestamp)
    projects: List[ProjectInformation]

    @classmethod
    def fetch_from_db(cls, project_configs: List[ProjectConfig]):
        project_info = []
        for project_config in project_configs:
            
            pipeline_runs = []
            for pipeline_config in project_config.pipeline_configs:
                # build_job = db.get_most_recent_job_run(project_config.job_namer.build_job_name(pipeline_config))
                # upload_job = db.get_most_recent_job_run(project_config.job_namer.upload_job_name(pipeline_config))
                test_job = db.get_most_recent_job_run(project_config.job_namer.test_job_name(pipeline_config))
                if not test_job:
                    print(f"no jobs ran for {project_config.name}: {pipeline_config}")
                    continue
                # print(f"test job for {project_config.name} {pipeline_config.model_dump()}: {test_job}")
                print(f"getting pipeline run info / results for {project_config.name} {pipeline_config}")
                pipeline_runs.append(PipelineRunInformation.from_job_run(
                    build_job_run=None,
                    upload_job_run=None,
                    test_job_run=test_job,
                ))
            project_info.append(ProjectInformation(
                name=project_config.name,
                pipeline_runs=pipeline_runs
            ))

        return cls(projects=project_info)

from fetcher import fetch_all_job_runs

def fetch_job_runs(projects: List[ProjectConfig]):
    for project in projects:
        for pipeline_config in project.pipeline_configs:
            # fetch_all_job_runs(project.job_namer.build_job_name(pipeline_config))
            # fetch_all_job_runs(project.job_namer.upload_job_name(pipeline_config))
            fetch_all_job_runs(project.job_namer.test_job_name(pipeline_config))

PROJECTS = [IBM_GUEST_PROJECT_CONFIG, ORACLE_PROJECT_CONFIG]


# then create a list of PipelineRunInformation objects
html_report = HTMLReportInformation.fetch_from_db(PROJECTS)

