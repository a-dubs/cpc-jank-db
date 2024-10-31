
from datetime import datetime
import json
from pprint import pprint
from typing import List, Tuple, Optional, Union
import requests

from typing import Any
from pydantic import BaseModel

import dotenv

from models import TestMatrixJobRun, Job, JobRun

dotenv.load_dotenv()
import os

auth = (os.getenv("JENKINS_API_USERNAME"), os.getenv("JENKINS_API_PASSWORD"))

import diskcache

from db import *

cache = diskcache.Cache("cache")
@cache.memoize(expire=999999999999)  # Cache results for a long time
def fetch_test_job_results(job_name: str, build_number: int):
    url = f"http://stable-cloud-images-ps5-jenkins-be.internal:8080/job/{job_name}/{build_number}/testReport/api/json"
    print(f"Fetching test job results from {url}")
    r = requests.get(url, auth=auth)
    if r.status_code == 200:
        data = r.json()
        return data
    else:
        return None

def fetch_env_vars(job_name: str, build_number: Optional[int] = None) -> dict:
    if build_number is None:
        build_number = "lastCompletedBuild"
    url = f"http://stable-cloud-images-ps5-jenkins-be.internal:8080/job/{job_name}/{build_number}/injectedEnvVars/api/json"
    r = requests.get(url, auth=auth)
    if r.status_code == 200:
        return r.json()["envMap"]
    else:
        return None
    

"""
"actions": [
    {
        "_class": "hudson.model.ParametersAction",
        "parameters": [
            {
                "_class": "hudson.model.StringParameterValue",
                "name": "SERIAL",
                "value": "20241025"
            },
            {
                "_class": "hudson.model.StringParameterValue",
                "name": "SUITE",
                "value": "noble"
            },
            {
                "_class": "hudson.model.StringParameterValue",
                "name": "CUSTOM_IMAGE_NAME_SUFFIX",
                "value": ""
            }
        ]
    },
    ...
]
"""
def get_build_parameters_from_actions(actions: list) -> dict:
    for action in actions:
        if action.get("_class") == "hudson.model.ParametersAction" or action.get("_class") == "hudson.matrix.MatrixChildParametersAction":
            return {param["name"]: param["value"] for param in action["parameters"]}
        if action.get("_class") == "hudson.model.ParametersDefinitionProperty":
            return {param["name"]: param["defaultParameterValue"]["value"] for param in action["parameterDefinitions"]}
        
    return {}

def get_job_run_info(job_name: str, build_number: Optional[int] = None) -> dict:
    
    # url =
    # "http://stable-cloud-images-ps5-jenkins-be.internal:8080/job/24.04-Base-Oracle-Daily-Test/lastCompletedBuild/api/json"
    
    url = (
        "http://stable-cloud-images-ps5-jenkins-be.internal:8080/job/" + 
        f"{job_name}/{build_number if build_number is not None else 'lastCompletedBuild'}/api/json"
    )

    r = requests.get(url, auth=auth)

    if r.status_code == 200:
        data = r.json()
        build_params = get_build_parameters_from_actions(data.get("actions"))
        return {
            "serial": int(build_params.get("SERIAL")),
            "suite": build_params.get("SUITE"),
            "build_number": int(data.get("number")),
            "timestamp": int(data.get("timestamp")),
            "duration": int(data.get("duration")),
        }

    else:
        return None

def rreplace(s, old, new, count=-1):
    """
    Replace occurrences of 'old' with 'new' in the string 's', starting from the right.
    
    Parameters:
    - s (str): The original string.
    - old (str): The substring to be replaced.
    - new (str): The substring to replace with.
    - count (int): The number of occurrences to replace from the right. Default is -1, which replaces all occurrences.
    
    Returns:
    - str: The modified string with replacements made from the right.
    """
    if count == -1:
        return new.join(s.rsplit(old))
    else:
        return new.join(s.rsplit(old, count))

@cache.memoize(expire=999999999999)  # Cache results for a long time
def get_error_texts(matrix_child_url: str, test_case_class: str, test_case_name: str) -> Tuple[str, str]:
    test_case_class = rreplace(test_case_class, ".", "/", 1)
    url = matrix_child_url.rstrip("/") + f"/testReport/{test_case_class}/{test_case_name}/api/json"
    url = convert_to_api_url(url)
    print(f"Fetching error texts from {url}")
    r = requests.get(url, auth=auth)
    if r.status_code == 200:
        data = r.json()
        return data.get("errorDetails"), data.get("errorStackTrace")
    else:
        raise Exception(f"Failed to fetch error texts from {url}")

def make_url_from_job_name(job_name: str) -> str:
    """
    Creates url of job, not api url.
    """
    return f"https://stable-cloud-images-ps5.jenkins.canonical.com/job/{job_name}/"

def convert_to_api_url(url: str) -> str:
    return str(url).replace(
        "https://stable-cloud-images-ps5.jenkins.canonical.com",
        "http://stable-cloud-images-ps5-jenkins-be.internal:8080",
    )

def fetch_run_json(url: str) -> dict:
    url = convert_to_api_url(url)
    if not url.endswith("/api/json") or not url.endswith("/api/json/"):
        url = url.rstrip("/") +  "/api/json"
    r = requests.get(url, auth=auth)
    if r.status_code == 200:
        return r.json()
    else:
        return {}

@cache.memoize(expire=999999999999)  # Cache results for a long time
def fetch_matrix_child_runs(matrix_job_run_url: str) -> List[dict]:
    url = convert_to_api_url(matrix_job_run_url)
    r = requests.get(convert_to_api_url(url), auth=auth)
    if r.status_code == 200:
        data = r.json()
        return [parse_job_run_info(fetch_run_json(run["url"])) for run in data["runs"]]
    else:
        return []


# import pickle

# if (os.path.exists("test_job_run.pkl")):
#     with open("test_job_run.pkl", "rb") as f:
#         test_job_run = pickle.load(f)
# else:
#     input("Press enter to fetch test job run info")
#     test_job_run = parse_all_info_from_test_job_run("24.04-Base-Oracle-Daily-Test")

#     # pickle the object 

#     with open("test_job_run.pkl", "wb") as f:
#         pickle.dump(test_job_run, f)

# with open("test_job_run.json", "w") as f:
#     f.write(test_job_run.model_dump_json(indent=2))



# lets fetch some jobs!

jobs_name_templates = [
    "{suite}-{family}-{cloud}-{release}-Test",
]

suites = ["20.04", "22.04", "24.04"]  # add 25.10 soon
families = ["Base", "Minimal"]
clouds = ["Oracle", "IBM-Guest"]
releases = ["Daily"]

# for any combination of suites, families, clouds, and releases, 
# if in the conflicts list, the job should not be fetched
conflicts = [
    {
        "cloud": "IBM-Guest",
        "family": "Minimal",
    },
]

def is_conflict(**args):
    for conflict in conflicts:
        if all(args.get(key) == value for key, value in conflict.items()):
            return True
    return False

def get_all_job_names_to_fetch() -> List[str]:
    job_names = []
    for suite in suites:
        for family in families:
            for cloud in clouds:
                for release in releases:
                    job_name = f"{suite}-{family}-{cloud}-{release}-Test"
                    if not is_conflict(suite=suite, family=family, cloud=cloud):
                        job_names.append(job_name)

    return job_names

JSON_DB_PATH = "test_results_db.json"

print(get_all_job_names_to_fetch())

def serialize_non_basic_values(object):
    if isinstance(object, datetime):
        return object.isoformat()  # Converts to ISO 8601 string format
    else:
        raise ValueError(f"unexpected object type trying to serialize ({object.__class__.__name__}): {object}")

# def fetch_all_jobs(num_recent_jobs_to_fetch: int = 1):
#     # read in the json db
#     json_db = {}
#     # if os.path.exists(JSON_DB_PATH):
#     #     with open(JSON_DB_PATH, "r") as f:
#     #         json_db = json.load(f)
#     # else:
#     #     json_db = {}

#     for job_name in get_all_job_names_to_fetch():
#         job_info = get_job_run_info(job_name)
#         last_build_no = job_info["build_number"]
#         for build_number in range(last_build_no, last_build_no - num_recent_jobs_to_fetch, -1):
#             if (check_if_job_exists(job_name, build_number)):
#                 print(f"Job: {job_name} (#{build_number}) already exists in the database")
#                 continue
#             print(f"Fetching job: {job_name} (#{build_number})")
#             try:
#                 test_job_run = parse_all_info_from_test_job_run(job_name, build_number=build_number)
#                 save_to_mongo(test_job_run)
#             except Exception as e:
#                 print(f"Failed to fetch job: {job_name} (#{build_number})")
#                 print(e)

# fetch_all_jobs(30)

def get_test_job_run(job_name: str, build_number: int) -> TestMatrixJobRun:
    print(f"Fetching full test job run: {job_name} (#{build_number})")
    job_run = fetch_job_run_from_api(job_name, build_number)

    result = TestMatrixJobRun.from_data(
        job_run_json=parse_job_run_info(fetch_job_run_json_from_api(job_name=job_name, build_number=build_number)),
        # job_run_json=job_run.model_dump(by_alias=True, exclude_unset=True),
        test_results_json=fetch_test_job_results(job_name, build_number),
        matrix_runs=fetch_matrix_child_runs(job_run.url),
    )

    result.fetch_error_texts_for_failed_tests(get_error_texts)

    return result

def parse_job_run_info(data: dict) -> dict:
    build_params = get_build_parameters_from_actions(data.get("actions"))
    if "SERIAL" not in build_params or "SUITE" not in build_params:
        exit(1)
    return {
        "url": data["url"],
        "fullDisplayName": data["fullDisplayName"],
        "buildNumber": data["number"],
        "serial": build_params["SERIAL"],
        "suite": build_params["SUITE"],
        "description": data.get("description"),
        "timestamp_ms": data["timestamp"],
        "duration_ms": data["duration"],
        "result": data["result"],
        "buildParameters": build_params,
    }

@cache.memoize(expire=100000)  # Cache results for a long time
def fetch_job_run_from_api(job_name: str, build_number: int) -> JobRun:
    print(f"Fetching job run from API: {job_name} (#{build_number})")
    url = f"http://stable-cloud-images-ps5-jenkins-be.internal:8080/job/{job_name}/{build_number}/api/json"
    r = requests.get(url, auth=auth)

    if r.status_code == 200:
        data = r.json()
        build_params = get_build_parameters_from_actions(data.get("actions"))
        return JobRun(
            url=url,
            fullDisplayName=data["fullDisplayName"],
            buildNumber=build_number,
            serial=build_params["SERIAL"],
            suite=build_params["SUITE"],
            description=data.get("description"),
            timestamp_ms=data["timestamp"],
            duration_ms=data["duration"],
            result=data["result"],
            buildParameters=build_params,
        )
    else:
        return None
    
def fetch_job_run_json_from_api(job_name: str, build_number: int) -> dict:
    print(f"Fetching job run from API: {job_name} (#{build_number})")
    url = f"http://stable-cloud-images-ps5-jenkins-be.internal:8080/job/{job_name}/{build_number}/api/json"
    r = requests.get(url, auth=auth)

    if r.status_code == 200:
        return r.json()
    else:
        return None

def fetch_job_from_api(job_name: str) -> Job:
    print(f"Fetching job from API: {job_name}")
    url = make_url_from_job_name(job_name) + "api/json"
    r = requests.get(convert_to_api_url(url), auth=auth)
    if r.status_code == 200:
        data = r.json()
        params = get_build_parameters_from_actions(data.get("actions"))
        suite = params.get("SUITE")
        if data.get("lastCompletedBuild"):
            last_completed_build_number = data.get("lastCompletedBuild").get("number")
        else:
            last_completed_build_number = None
        return Job(
            url=url,
            fullDisplayName=data["fullDisplayName"],
            suite=suite,
            description=data.get("description"),
            buildNumbers=[entry["number"] for entry in data.get("builds", [])],
            lastCompletedBuildNumber=last_completed_build_number,
        ) 
    else:
        return None


def fetch_and_refresh_job(job_name: str) -> Job:
    """
    Get newest job data from API and update existing job in the database if it exists.
    """
    job = get_job_from_db(job_name)
    if job is None:
        job = fetch_job_from_api(job_name)
    else:  # update job
        new_job = fetch_job_from_api(job_name)
        if new_job is not None:
            # update job with new description and build numbers and update last_updated
            job.description = new_job.description
            job.build_numbers = new_job.build_numbers
            job.last_updated = datetime.now()
    save_to_mongo(job)
    return job


def fetch_all_job_runs(job_name: str):
    job = fetch_and_refresh_job(job_name)
    if job is None:
        raise ValueError(f"Failed to fetch job: {job_name}")
    
    if job.last_completed_build_number is None:
        print(f"Job {job_name} has no builds. No job runs to fetch...")
    
    for build_number in job.build_numbers:
        if build_number > job.last_completed_build_number:
            # skip if job has not completed
            continue
            
        if job_run_already_exists(job_name=job.name, build_number=build_number):
            print(f"Job run {job_name} (#{build_number}) already exists in the database")
            continue

        print(f"Fetching job run: {job_name} (#{build_number})")
        try:
            test_job_run = get_test_job_run(job_name, build_number=build_number)
            save_to_mongo(test_job_run)
        except Exception as e:
            print(f"Failed to fetch job run: {job_name} (#{build_number})")
            raise(e)

fetch_all_job_runs("25.04-Base-Oracle-Daily-Test")
fetch_all_job_runs("24.10-Base-Oracle-Daily-Test")
fetch_all_job_runs("24.04-Base-Oracle-Daily-Test")
fetch_all_job_runs("22.04-Base-Oracle-Daily-Test")
fetch_all_job_runs("20.04-Base-Oracle-Daily-Test")
