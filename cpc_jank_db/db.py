"""
Module for interacting with the underlying MongoDB database.

This module provides functions for saving and retrieving Job and JobRun instances from the database.

Any processing of the data should be done elsewhere.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel
from pymongo import MongoClient

from cpc_jank_db.models import Job, JobRun, MatrixJobRun, TestMatrixJobRun, TestJobRun
from cpc_jank_db.naming import PipelineConfig, ProjectConfig
import tqdm

client = MongoClient("mongodb://localhost:27069/")
db = client["test_jenkins_observability_db"]
job_collection = db["jenkins_job_collection"]
job_run_collection = db["jenkins_job_run_collection"]

def save_to_mongo(pydantic_model: BaseModel):
    """Convert pydantic model to a dict and insert into MongoDB."""
    
    if pydantic_model is None:
        raise ValueError("pydantic_model must not be None")

    # if it is a Job, insert into job_collection
    if isinstance(pydantic_model, Job):
        pydantic_model: Job
        if job_already_exists(pydantic_model.name):
            print(f"Job: {pydantic_model.name} already exists in the database. Updating...")
            # update the job
            job_collection.update_one(
                {"fullDisplayName": pydantic_model.name},
                {"$set": pydantic_model.model_dump(by_alias=True, exclude_unset=False)}
            )
        else:
            print("Saving job to mongo")
            document = pydantic_model.model_dump(by_alias=True, exclude_unset=False)
            job_collection.insert_one(document)
    # if it is a JobRun, insert into job_run_collection
    elif isinstance(pydantic_model, JobRun):
        if job_run_already_exists(pydantic_model.name, pydantic_model.build_number):
            print(f"Job run: {pydantic_model.name} (#{pydantic_model.build_number}) already exists in the database. Updating...")
            # update the job run
            job_run_collection.update_one(
                {"fullDisplayName": pydantic_model.name, "buildNumber": pydantic_model.build_number},
                {"$set": pydantic_model.model_dump(by_alias=True, exclude_unset=False)}
            )
        else:
            print("Saving job run to mongo")
            document = pydantic_model.model_dump(by_alias=True, exclude_unset=False)
            job_run_collection.insert_one(document)
    else:
        raise ValueError(f"pydantic_model must be either a Job or JobRun instance, not: {pydantic_model} ({type(pydantic_model)})")
    pass

def get_job_from_db(job_name: str) -> Optional[Job]:
    result = get_job_dict(job_name)
    if result:
        return Job(**result)
    return None

def get_job_run_from_db(job_name: str, build_number: int) -> Optional[JobRun]:
    result = get_job_run_dict(job_name, build_number)
    if result:
        return create_job_run_from_data(result)
    return None

def job_already_exists(job_name: str) -> bool:
    return get_job_from_db(job_name=job_name) is not None

def job_run_already_exists(job_name: str, build_number: int) -> bool:
    return get_job_run_from_db(job_name, build_number) is not None

def get_job_dict(job_name: str) -> dict:
    return job_collection.find_one({"fullDisplayName": {"$regex": job_name}})

def get_job_run_dict(job_name: str, build_number: int) -> dict:
    return job_run_collection.find_one({"fullDisplayName": {"$regex": job_name}, "buildNumber": build_number})

def create_job_run_from_data(data: dict):
    try:
        if data["self_class"] == "JobRun":
            return JobRun(**data)
        elif data["self_class"] == "MatrixJobRun":
            return MatrixJobRun(**data)
        elif data["self_class"] == "TestMatrixJobRun":
            return TestMatrixJobRun(**data)
        elif data["self_class"] == "TestJobRun":
            return TestJobRun(**data)
        else:
            raise ValueError(f"Unknown class: {data['self_class']}")
    except Exception as e:
        print(f"[db] Error creating job run from data: {e}")
        print(data.keys())
        input("Press enter to continue...")

def get_job_runs_dict_for_job(job_name: str) -> List[Dict]:
    result =  job_run_collection.find({"fullDisplayName": {"$regex": job_name}})
    return [doc for doc in result]

def get_job_runs_for_job(job_name: str) -> List[JobRun]:
    return [create_job_run_from_data(doc) for doc in get_job_runs_dict_for_job(job_name)]

# clear all jobs run from db
def clear_db():
    job_run_collection.delete_many({})
    job_collection.delete_many({})

def delete_job_and_job_runs(job_name: str):
    """Delete all job runs and the job with the given name from the database."""
    job_result = job_collection.delete_one({"fullDisplayName": job_name})
    job_runs_result = job_run_collection.delete_many({"fullDisplayName": {"$regex": f"^{job_name} #[0-9]+"}})
    print(f"Deleted job: {job_name} ({job_result.deleted_count} documents) and {job_runs_result.deleted_count} job runs")
                                                        
def get_most_recent_job_run_dict(job_name: str) -> Optional[Dict]:
    return job_run_collection.find_one(
        {"fullDisplayName": {"$regex": job_name}},
        sort=[("buildNumber", -1)]
    )

def get_most_recent_job_run(job_name: str) -> Optional[JobRun]:
    result = get_most_recent_job_run_dict(job_name)
    if result:
        return create_job_run_from_data(result)
    return None

def get_all_jobs_matching_name(job_name: str) -> List[Job]:
    result = job_collection.find({"fullDisplayName": {"$regex": job_name}})
    return [Job(**doc) for doc in result]


# function to get job runs for a PipelineConfig
def get_job_runs_for_pipeline_config(pipeline_config: PipelineConfig) -> List[JobRun]:
    job_runs = []
    for job_name in pipeline_config.all_job_names:
        job_runs.extend(get_job_runs_for_job(job_name))
    return job_runs

def get_test_job_runs_for_pipeline_config(pipeline_config: PipelineConfig) -> List[TestMatrixJobRun]:
    test_job_name = pipeline_config.test_job_name
    if not test_job_name:
        raise ValueError(f"No test job name found for pipeline config: {pipeline_config}")
    return [job_run for job_run in get_job_runs_for_job(test_job_name) if isinstance(job_run, TestMatrixJobRun)]

def get_test_job_runs_for_project(project_config: ProjectConfig) -> List[TestMatrixJobRun]:
    test_job_runs = []
    for pipeline_config in tqdm.tqdm(project_config.pipeline_configs, desc="Downloading test job runs per pipeline"):
        test_job_runs.extend(get_test_job_runs_for_pipeline_config(pipeline_config))
    return test_job_runs

def get_job_runs_for_project(project_config: ProjectConfig) -> List[JobRun]:
    job_runs = []
    for pipeline_config in project_config.pipeline_configs:
        job_runs.extend(get_job_runs_for_pipeline_config(pipeline_config))
    return job_runs

def _update_existing_entries_with_family_field():
    """
    Update all job and job run documents in the database to add the family field if it doesn't already exist.
    """
    all_jobs = job_collection.find({})
    for job in all_jobs:
        name = job["fullDisplayName"]
        if "family" not in job:
            job["family"] = "Minimal" if "minimal" in name.lower() else "Base"
            job_collection.update_one(
                {"fullDisplayName": name},
                {"$set": job}
            )
            print(f"Updated job: {name} with family: {job['family']}")

    # get each job run document and update it to add the family field
    all_job_runs = job_run_collection.find({})
    for job_run in all_job_runs:
        if "family" not in job_run:
            name = job_run.get("fullDisplayName") or job_run.get("name")
            family = "Minimal" if "minimal" in name.lower() else "Base"
            job_run_collection.update_one(
                {"fullDisplayName": name},
                {"$set": {"family": family}}
            )
            print(f"Updated job run: {name} with family: {family}")

if __name__ == "__main__":
    # print out list of all job names in the db and then also print out the number of job runs stored for each job
    all_jobs = job_collection.find({})
    for job in all_jobs:
        job_name = job["fullDisplayName"]
        runs = get_job_runs_for_job(job_name)
        print(f"Job: {job_name} has {len(runs)} job runs stored")
