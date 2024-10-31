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

