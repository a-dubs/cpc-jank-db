
# from pymongo import MongoClient
# from typing import Any, List
# from pydantic import BaseModel

# client = MongoClient("mongodb://localhost:27017/")
# db = client["test_jenkins_observability_db"]
# collection = db["jenkins_test_results_1"]

# def save_to_mongo(pydantic_model: BaseModel):
#     """Convert pydantic model to a dict and insert into MongoDB."""
#     document = pydantic_model.model_dump(by_alias=True, exclude_unset=True)
#     collection.insert_one(document)

# def check_if_job_exists(job_name: str, build_number: int) -> bool:
#     return collection.find_one({"name": job_name, "build_number": build_number}) is not None

# from models import TestJobRun

# # # for each unique job (based on TestJobRun.name), fetch get most recent one per job name from the database
# # for job in collection.distinct("name"):
# #     most_recent_job_dict : dict = collection.find_one(
# #         {"name": job},
# #         sort=[("build_number", -1)]
# #     )
# #     # convert from dict back into TestJobRun
# #     most_recent_job = TestJobRun(**most_recent_job_dict)
# #     print(most_recent_job.url, most_recent_job.test_results.fail_count)


# jobs_name_templates = [
#     "{suite}-{family}-{cloud}-{release}-Test",
# ]

# suites = ["20.04", "22.04", "24.04"]  # add 25.10 soon
# families = ["Base", "Minimal"]
# clouds = ["Oracle", "IBM-Guest"]
# releases = ["Daily"]

# # for any combination of suites, families, clouds, and releases, 
# # if in the conflicts list, the job should not be fetched
# conflicts = [
#     {
#         "cloud": "IBM-Guest",
#         "family": "Minimal",
#     },
# ]

# def is_conflict(**args):
#     for conflict in conflicts:
#         if all(args.get(key) == value for key, value in conflict.items()):
#             return True
#     return False

# def get_all_job_names_to_fetch() -> List[str]:
#     job_names = []
#     for suite in suites:
#         for family in families:
#             for cloud in clouds:
#                 for release in releases:
#                     job_name = f"{suite}-{family}-{cloud}-{release}-Test"
#                     if not is_conflict(suite=suite, family=family, cloud=cloud):
#                         job_names.append(job_name)

#     return job_names


from typing import Optional
from pydantic import BaseModel
from pymongo import MongoClient
from models import Job, JobRun, OracleMatrixTestRunConfig, TestMatrixJobRun

from db import *


from typing import List, Optional

def print_failed_test_errors(
    test_job_runs: List[TestMatrixJobRun],
    arch: Optional[str] = None,
    instance_type: Optional[str] = None,
    test: Optional[str] = None,
    login_method: Optional[str] = None,
    launch_mode: Optional[str] = None,
    test_name: Optional[str] = None,
):
    for job_run in test_job_runs:
        print(job_run)
        # Loop through matrix test reports in each job run
        if not job_run.test_results:
            continue  # Skip if there are no test results

        for test_report in job_run.test_results.matrix_test_reports:
            config = test_report.test_config
            
            # Apply MatrixTestRunConfig filters (AND condition for all provided filters)
            if (arch and config.arch != arch) or \
               (instance_type and config.instance_type != instance_type) or \
               (test and config.test != test) or \
               (login_method and isinstance(config, OracleMatrixTestRunConfig) and config.login_method != login_method) or \
               (launch_mode and isinstance(config, OracleMatrixTestRunConfig) and config.launch_mode != launch_mode):
                continue  # Skip this test report if any filter does not match

            # Loop through suites and test cases
            for suite in test_report.test_result.suites:
                for case in suite.cases:
                    # Check if test case status is FAILED and apply TestCase 'name' filter
                    if case.status == "FAILED" and (test_name is None or case.name == test_name):
                        print(f"Test Case: {case.name}")
                        print(f"Error Details: {case.error_details}\n")


# get all oracle test job runs 
oracle_runs = get_job_runs_for_job("24.04-Base-Oracle-Daily-Test")
print_failed_test_errors(
    test_job_runs=oracle_runs,
    test_name="test_snap_preseed_optimized",
)

