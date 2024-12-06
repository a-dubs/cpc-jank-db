
from datetime import datetime
from typing import List, Tuple, Optional, Union
import requests

import dotenv

from cpc_jank_db.models import MatrixJobRun, TestMatrixJobRun, Job, JobRun, TestJobRun

dotenv.load_dotenv()
import os


auth = (os.getenv("JENKINS_API_USERNAME"), os.getenv("JENKINS_API_PASSWORD"))

JENKINS_API_URL = os.getenv("JENKINS_API_URL")
JENKINS_SSO_URL = os.getenv("JENKINS_SSO_URL")

print(f"JENKINS_API_URL: {JENKINS_API_URL}")
print(f"JENKINS_SSO_URL: {JENKINS_SSO_URL}")

if JENKINS_API_URL is None:
    raise ValueError("JENKINS_API_URL not set in .env file")

if JENKINS_SSO_URL is None:
    raise ValueError("JENKINS_SSO_URL not set in .env file")

import diskcache
cache = diskcache.Cache(".disk-cache")


from cpc_jank_db import db

suites = {
    "14.04": "trusty",
    "16.04": "xenial",
    "18.04": "bionic",
    "20.04": "focal",
    "22.04": "jammy",
    "24.04": "noble",
    "24.10": "oracular",
    "25.04": "plucky",
}

def _append_tree_query_param(url: str, fields_to_fetch: list[str]) -> str:
    """
    Returns a url with the tree query parameter appended to it so that only the specified fields are fetched from the
    API.
    
    Args:
        url (str): The url to append the tree query parameter to.
        fields_to_fetch (list[str]): A list of fields to fetch from the API.
    
    Returns:
        str: The url with the tree query parameter appended to it.
    """
    tree_query = "tree=" + ",".join(fields_to_fetch)
    url = url.removesuffix("/")
    if "?" in url:
        return url + "&" + tree_query
    else:
        return url + "?" + tree_query

# DO NOT CACHE - jobs are not immutable like job runs
def _get_job_from_api(url: str) -> dict:
    """
    Fetch job data from the Jenkins API.

    Uses tree query parameter to only fetch the fields we need.
    """

    url = _convert_to_api_url(url)
    url = _append_tree_query_param(
        url,
        [
            "url",
            "fullDisplayName",
            "description",
            "lastCompletedBuild[number]",
            "builds[number]",
        ],
    )
    r = requests.get(url, auth=auth)
    if r.status_code == 200:
        return r.json()
    else:
        print(r.status_code)
        print(r.text)
        raise Exception(f"Failed to fetch job from {url}")

@cache.memoize()
def _get_job_run_from_api(url: str) -> dict:
    """
    Fetch job run data from the Jenkins API.

    Uses tree query parameter to only fetch the fields we need.
    """

    url = _convert_to_api_url(url)
    url = _append_tree_query_param(
        url,
        [
            "url",
            "actions[_class,parameters[name,value]]",
            "fullDisplayName",
            "number",
            "description",
            "timestamp",
            "duration",
            "result",
            "runs[url]",
        ],
    )
    r = requests.get(url, auth=auth)
    if r.status_code == 200:
        return r.json()
    else:
        print(r.status_code)
        print(r.text)
        raise Exception(f"Failed to fetch job run from {url}")

# @cache.memoize()
def _fetch_test_job_results(job_name: str, build_number: int):
    url = f"{JENKINS_API_URL}/job/{job_name}/{build_number}/testReport"
    url = _convert_to_api_url(url)
    r = requests.get(url, auth=auth)
    if r.status_code == 200:
        data = r.json()
        return data
    else:
        print(r.status_code)
        print(r.text)
        print("tried url:", url)
        raise Exception(f"Failed to fetch test job results from {url}")

def _fetch_env_vars(job_name: str, build_number: Optional[int] = None) -> dict:
    if build_number is None:
        build_number = "lastCompletedBuild"
    url = f"{JENKINS_API_URL}/job/{job_name}/{build_number}/injectedEnvVars"
    url = _convert_to_api_url(url)
    r = requests.get(url, auth=auth)
    if r.status_code == 200:
        return r.json()["envMap"]
    else:
        print(r.status_code)
        print(r.text)
        raise Exception(f"Failed to fetch env vars from {url}")
    

def _get_build_parameters_from_actions(actions: list) -> dict:
    for action in actions:
        if action.get("_class") == "hudson.model.ParametersAction" or action.get("_class") == "hudson.matrix.MatrixChildParametersAction":
            return {param["name"]: str(param["value"]) for param in action["parameters"]}
        if action.get("_class") == "hudson.model.ParametersDefinitionProperty":
            return {param["name"]: str(param["defaultParameterValue"]["value"]) for param in action["parameterDefinitions"]}
        
    return {}

@cache.memoize()
def _get_error_texts(individual_test_report_url: str) -> Tuple[str, str]:
    
    url = _convert_to_api_url(individual_test_report_url)
    url = _append_tree_query_param(
        url,
        [
            "errorDetails",
            "errorStackTrace",
        ],
    )
    r = requests.get(url, auth=auth)
    if r.status_code == 200:
        data = r.json()
        return data.get("errorDetails"), data.get("errorStackTrace")
    else:
        print(r.status_code)
        print(r.text)
        print("tried url:", url)
        raise Exception(f"Failed to fetch error texts from {url}")

def _make_url_from_job_name(job_name: str) -> str:
    """
    Creates url of job, not api url.
    """
    return f"{JENKINS_SSO_URL}/job/{job_name}/"

def _convert_to_api_url(url: str) -> str:
    r = str(url).replace(
        JENKINS_SSO_URL,
        JENKINS_API_URL,
    )
    r = r.removesuffix("/").removesuffix("/api/json")
    r += "/api/json"
    return r

def _fetch_json(url: str) -> dict:
    url = _convert_to_api_url(url)
    r = requests.get(url, auth=auth)
    if r.status_code == 200:
        return r.json()
    else:
        print(r.status_code)
        print(r.text)
        raise Exception(f"Failed to fetch run json from {url}")

# fetch plain text console output for job run using its url
@cache.memoize()
def _fetch_console_output(url: str) -> str:
    url = _convert_to_api_url(url)
    url = url.removesuffix("/api/json").removesuffix("/") + "/consoleText"
    r = requests.get(url, auth=auth)
    if r.status_code == 200:    
        return r.text
    else:
        print(r.status_code)
        print(r.text)
        raise Exception(f"Failed to fetch console output from {url}")

@cache.memoize()
def _fetch_matrix_child_runs(matrix_job_run_url: str) -> List[dict]:
    try:
        parent_job_data = _get_job_run_from_api(matrix_job_run_url)
        if parent_job_data:
            parsed_job_runs = [
                _parse_job_run_info(_get_job_run_from_api(run["url"]))
                for run in parent_job_data["runs"]
            ]
            for job_run_dict in parsed_job_runs:
                job_run_dict["consoleOutput"] = _fetch_console_output(job_run_dict["url"])
            return parsed_job_runs
    except Exception as e:
        raise Exception(f"Failed to fetch matrix child runs from {matrix_job_run_url}") from e

def _parse_job_run_info(data: dict) -> dict:
    """
    Parse job run info from the Jenkins API json object.
    
    Args:
        data (dict): The json object from the Jenkins API.

    Returns:
        dict: The parsed job run info that can be used to create a JobRun object.
    """
    build_params = _get_build_parameters_from_actions(data.get("actions"))
    # if "minimal" in data["fullDisplayName"].lower() or "base" in data["fullDisplayName"].lower():
    #     family = "Minimal" if "minimal" in data["fullDisplayName"].lower() else "Base"
    # else:
    #     family = None
    if data["fullDisplayName"].split("-")[0] not in suites:
        suite = next(iter([suite for suite in suites.values() if suite in data["fullDisplayName"]]), None)
    else:
        suite = suites.get(data["fullDisplayName"].split("-")[0])

    return {
        "url": data["url"],
        "fullDisplayName": data["fullDisplayName"],
        "buildNumber": data["number"],
        "serial": build_params.get("SERIAL"),
        "suite": suite,
        # "family": family,
        "description": data.get("description"),
        "timestamp_ms": data["timestamp"],
        "duration_ms": data["duration"],
        "result": data["result"],
        "buildParameters": build_params,
        "childRunsUrls": [run_info["url"] for run_info in data.get("runs", [])] or None,
    }

def _parse_job_run_object_from_api_json(api_data: dict) -> JobRun:
    """
    Create a JobRun object from the Jenkins API json object.

    Args:
        api_data (dict): The JSON data from the API to create the JobRun object from.

    Returns:
        JobRun: The JobRun object created from the API data.
    """
    data = _parse_job_run_info(api_data)
    return JobRun(
        **data
    )
    
def _fetch_job_run_json_from_name_and_build(job_name: str, build_number: int) -> dict:
    """
    Fetch job run json from the Jenkins API and return the full json object.
    
    Args:
        job_name (str): The name of the job.
        build_number (int): The build number of the job run.

    Returns:
        dict: The full json object of the job run from the Jenkins API.    
    """
    url = f"{JENKINS_API_URL}/job/{job_name}/{build_number}"
    return _get_job_run_from_api(url)

def collect_job(job_name: str) -> Job:
    print(f"Collecting job info from API: {job_name}")
    url = _make_url_from_job_name(job_name) + "api/json"
    
    data = _get_job_from_api(url)

    if data.get("lastCompletedBuild"):
        last_completed_build_number = data.get("lastCompletedBuild").get("number")
    else:
        last_completed_build_number = None
    return Job(
        url=url,
        fullDisplayName=data["fullDisplayName"],
        suite=suites.get(data["fullDisplayName"].split("-")[0]),
        description=data.get("description"),
        buildNumbers=[entry["number"] for entry in data.get("builds", [])],
        lastCompletedBuildNumber=last_completed_build_number,
    )

def collect_job_run(
        job_name: str, 
        build_number: int,
        job_run_type: Optional[type[JobRun]] = None,
) -> JobRun | MatrixJobRun | TestMatrixJobRun | TestJobRun:
    print(f"Collecting job run info from API: {job_name} (#{build_number})")
    job_run_api_json = _fetch_job_run_json_from_name_and_build(job_name=job_name, build_number=build_number)
    job_run = _parse_job_run_object_from_api_json(job_run_api_json)
    console_output = _fetch_console_output(job_run.url)
    # if runs list exists, it is a matrix job
    if job_run.child_runs_urls is not None:
        # if one of the actions has hudson.tasks.test.MatrixTestResult as its _class, then it is a TestMatrixJobRun
        if any(action.get("_class") == "hudson.tasks.test.MatrixTestResult" for action in job_run_api_json.get("actions")):
            result = TestMatrixJobRun.from_data(
                job_run_json=_parse_job_run_info(job_run_api_json),
                # job_run_json=job_run.model_dump(by_alias=True, exclude_unset=True),
                test_results_json=_fetch_test_job_results(job_name, build_number),
                matrix_runs=_fetch_matrix_child_runs(job_run.url),
            )
            result.console_output = console_output
            result.fetch_error_texts_for_failed_tests(_get_error_texts)
            return result
        # otherwise, it is a MatrixJobRun
        else:
            result = MatrixJobRun.from_data(
                matrix_runs=_fetch_matrix_child_runs(job_run.url),
                **job_run.model_dump(by_alias=True, exclude_unset=True),
            )
            result.console_output = console_output
            return result
    # otherwise, it is a JobRun or TestJobRun
    else:
        if job_run_type == TestJobRun:
            # try to fetch test results url 
            try:
                test_job_results = _fetch_test_job_results(job_name, build_number)
            except Exception as e:
                print(f"Failed to fetch test job results for {job_name} (#{build_number})")
                test_job_results = None
            if test_job_results and test_job_results.get("failCount") is not None:
                result = TestJobRun.from_data(
                    job_run_json=_parse_job_run_info(job_run_api_json),
                    test_results_json=test_job_results,
                )
                result.fetch_error_texts_for_failed_tests(_get_error_texts)
            # if test results do not exist or failCount is None, create a TestJobRun without test results
            else:
                result = TestJobRun.from_data(
                    job_run_json=_parse_job_run_info(job_run_api_json),
                    test_results_json=None,
                )
            result.console_output = console_output
            return result
        else:
            job_run.console_output = console_output
            return job_run

def _fetch_and_refresh_job(job_name: str) -> Job:
    """
    Get newest job data from API and update existing job in the database if it exists.
    """
    job = db.get_job_from_db(job_name)
    if job is None:
        job = collect_job(job_name)
    else:  # update job
        new_job = collect_job(job_name)
        if new_job is not None:
            # update job with new description and build numbers and update last_updated
            job.description = new_job.description
            job.build_numbers = new_job.build_numbers
            job.last_updated = datetime.now()
            job.last_completed_build_number = new_job.last_completed_build_number
    db.save_to_mongo(job)
    return job


def collect_all_job_runs(
    job_name: str,
    job_run_type: Optional[type[JobRun]] = None,
) -> Tuple[Job, List[JobRun]]:
    """
    Fetch all job runs for a job and save them to the database.
    
    Args:
        job_name (str): The name of the job to fetch job runs for.

        Example: "24.04-Base-Oracle-Daily-Test"
        Example: "24.04-Base-Oracle-Build-Images"
    
    Returns:
        Tuple[Job, List[JobRun]]: A tuple containing the job and a list of job runs.

            The job is the updated job object with the latest build numbers and description.

            The list of job runs are the job runs that were fetched from the API, and saved to the database.
            Any job runs that already existed in the database were not saved again and will not be in the list.
    """
    fetched_job_runs = []
    job = _fetch_and_refresh_job(job_name)
    if job is None:
        raise ValueError(f"Failed to fetch job: {job_name}")
    
    if job.last_completed_build_number is None:
        print(f"Job {job_name} has no builds. No job runs to fetch...")
    
    for build_number in job.build_numbers:
        if build_number > job.last_completed_build_number:
            # skip if job has not completed
            print(f"Skipping job run {job_name} (#{build_number}) because it has not completed")
            continue
            
        if db.job_run_already_exists(job_name=job_name, build_number=build_number):
            print(f"Job run {job_name} (#{build_number}) already exists in the database")
            continue

        print(f"Fetching job run: {job_name} (#{build_number})")
        try:
            test_job_run = collect_job_run(
                job_name=job_name,
                build_number=build_number,
                job_run_type=job_run_type,
            )
            db.save_to_mongo(test_job_run)
            fetched_job_runs.append(test_job_run)
        except Exception as e:
            print(f"Failed to fetch job run: {job_name} (#{build_number})")
            raise(e)

    return job, fetched_job_runs

if __name__ == "__main__":
    print("This module is not meant to be run directly. Import it into another module.")