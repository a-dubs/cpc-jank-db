from pprint import pprint
from typing import Dict, Set, Tuple
from cpc_jank_db import db
from cpc_jank_db.models import Job, JobRun, MatrixJobRun, TestMatrixJobRun, OracleMatrixTestRunConfig

# Function to get the set of tests that exist from a TestMatrixJobRun
def get_test_set(test_job: TestMatrixJobRun) -> Set[str]:
    test_set = set()
    if not test_job.test_results:
        return test_set

    for test_report in test_job.test_results.matrix_test_reports:
        for suite in test_report.test_result.suites:
            for case in suite.cases:
                test_set.add(case.name)
    return test_set

# Function to get the tests that failed and their success, skip, and failure counts
def get_test_stats(test_job: TestMatrixJobRun) -> Dict[str, Dict[str, int]]:
    stats = {}

    if not test_job.test_results:
        return stats

    for test_report in test_job.test_results.matrix_test_reports:
        for suite in test_report.test_result.suites:
            for case in suite.cases:
                if case.name not in stats:
                    stats[case.name] = {
                        "succeeded": 0,
                        "skipped": 0,
                        "failed": 0
                    }
                
                if case.status == "PASSED":
                    stats[case.name]["succeeded"] += 1
                elif case.status == "SKIPPED":
                    stats[case.name]["skipped"] += 1
                elif case.status == "FAILED":
                    stats[case.name]["failed"] += 1

    return stats

def get_matrix_job_results(matrix_job: MatrixJobRun):
    # take in a matrix job and get statuses for each child run (matrix_runs field)
    # return a dictionary that contains the string representation of the matrix run config as the key
    # and the value is the run status (PASSED, FAILED, etc.)
    matrix_job_statuses = {}
    for child_run in matrix_job.matrix_runs:
        matrix_job_statuses[child_run.config_string] = child_run.result
    return matrix_job_statuses

def get_matrix_job_results_stats(matrix_job: MatrixJobRun) -> dict[str,int]:
    # take in a matrix job and get statuses for each child run (matrix_runs field)
    # Literal["SUCCESS", "FAILURE", "UNSTABLE", "ABORTED"]

    
    results = {
        "SUCCESS": 0,
        "FAILURE": 0,
        "UNSTABLE": 0,
        "ABORTED": 0
    }

    for child_run in matrix_job.matrix_runs:
        if child_run.result in results:
            results[child_run.result] += 1
    return results


# create pydantic model representing the data structure
from pydantic import BaseModel
from typing import List, Optional

class FailedTestRun(BaseModel):
    url: str
    config_string: str
    error_text: str

class FailedTestDetails(BaseModel):
    test_name: str
    fail_count: int
    ran_count: int
    runs: List[FailedTestRun]

def get_failed_test_details(test_job: TestMatrixJobRun) -> List[FailedTestDetails]:
    failed_tests = []

    for test_report in test_job.test_results.matrix_test_reports:
        for suite in test_report.test_result.suites:
            for case in suite.cases:
                if case.status == "FAILED":
                    test_name = case.name
                    fail_count = 1
                    ran_count = 1
                    test_case_report_url = test_report.generate_test_case_report_url(
                        job_url=test_job.url,
                        test_case_name=case.name,
                        test_case_class=case.class_name
                    )
                    runs = [
                        FailedTestRun(
                            url=test_case_report_url,
                            config_string=test_report.test_config.config_string,
                            error_text=case.error_details
                        )
                    ]

                    for failed_test in failed_tests:
                        if failed_test.test_name == test_name:
                            failed_test.fail_count += 1
                            failed_test.ran_count += 1
                            failed_test.runs.append(
                                FailedTestRun(
                                    url=test_case_report_url,
                                    config_string=test_report.test_config.config_string,
                                    error_text=case.error_details
                                )
                            )
                            break
                    else:
                        failed_tests.append(FailedTestDetails(
                            test_name=test_name,
                            fail_count=fail_count,
                            ran_count=ran_count,
                            runs=runs
                        ))

    return failed_tests


def print_failed_test_errors(
    test_job_runs: List[TestMatrixJobRun],
    arch: Optional[str] = None,
    instance_type: Optional[str] = None,
    test: Optional[str] = None,
    login_method: Optional[str] = None,  # oracle specific
    launch_mode: Optional[str] = None,  # oracle specific
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




