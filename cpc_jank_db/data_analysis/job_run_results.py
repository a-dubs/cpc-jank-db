from pprint import pprint
from typing import Dict, Literal, Set, Tuple
from cpc_jank_db import db
from cpc_jank_db.models import Job, JobRun, MatrixJobRun, MatrixTestReport, MatrixTestRunConfig, TestCase, TestMatrixJobRun, OracleMatrixTestRunConfig
import pandas as pd

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

