
from typing import Optional
from pydantic import BaseModel
from pymongo import MongoClient

from models import Job, JobRun, MatrixJobRun, TestMatrixJobRun

client = MongoClient("mongodb://localhost:27017/")
db = client["test_jenkins_observability_db"]
job_collection = db["jenkins_job_collection"]
job_run_collection = db["jenkins_job_run_collection"]

def save_to_mongo(pydantic_model: BaseModel):
    """Convert pydantic model to a dict and insert into MongoDB."""

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
        raise ValueError("pydantic_model must be either a Job or JobRun instance")
    pass

def get_job_from_db(job_name: str) -> Optional[Job]:
    result = job_collection.find_one({"fullDisplayName": {"$regex": job_name}})
    if result:
        return Job(**result)
    return None

def get_job_run_from_db(job_name: str, build_number: int) -> Optional[JobRun]:
    result = job_run_collection.find_one({"fullDisplayName": {"$regex": job_name}, "buildNumber": build_number})
    if result:
        return create_job_run_from_data(result)
    return None

def job_already_exists(job_name: str) -> bool:
    return get_job_from_db(job_name=job_name) is not None

def job_run_already_exists(job_name: str, build_number: int) -> bool:
    return get_job_run_from_db(job_name, build_number) is not None

def create_job_run_from_data(data: dict):
    try:
        if data["self_class"] == "JobRun":
            return JobRun(**data)
        elif data["self_class"] == "MatrixJobRun":
            return MatrixJobRun(**data)
        elif data["self_class"] == "TestMatrixJobRun":
            return TestMatrixJobRun(**data)
        else:
            raise ValueError(f"Unknown class: {data['self_class']}")
    except Exception as e:
        print(f"Error creating job run from data: {e}")
        print(data.keys())

def get_job_runs_for_job(job_name: str) -> list[JobRun]:
    # each job run has a name that contains the job name substring 
    result =  job_run_collection.find({"fullDisplayName": {"$regex": job_name}})
    return [create_job_run_from_data(doc) for doc in result]

# clear all jobs run from db
def clear_db():
    job_run_collection.delete_many({})
    job_collection.delete_many({})

    
job_run_already_exists("20.04-Base-Oracle-Daily-Test", 1)