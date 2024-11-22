
# create pydantic model representing the data structure
import pandas as pd
from pydantic import BaseModel
from typing import Dict, List, Literal, Optional, Set

from cpc_jank_db.models import JobRun, MatrixTestReport, OracleMatrixTestRunConfig, TestCase, TestMatrixJobRun

class TestCaseFailure(BaseModel):
    test_case_name: str
    test_case_url: str
    config_string: str
    error_text: str
    # details from JobRun that we want to capture:
    job_name : str  # job run name without the " #build_number" suffix
    serial: str
    suite: str
    family: Literal["Base", "Minimal"]
    build_number: int
    job_run_url: str

    @classmethod    
    def from_data(
        cls,
        test_report: MatrixTestReport,
        test_case: TestCase,
        job_run: JobRun,
    ):
        return cls(
            test_case_name=test_case.name,
            config_string=test_report.test_config.config_string,
            error_text=test_case.error_details,
            job_name=job_run.job_name,
            serial=job_run.serial,
            suite=job_run.suite,
            family=job_run.family,
            build_number=job_run.build_number,
            job_run_url=job_run.url,
            test_case_url=test_report.generate_test_case_report_url(
                test_case_name=test_case.name,
                test_case_class=test_case.class_name
            )
        )


def get_failed_test_cases(test_job: TestMatrixJobRun) -> List[TestCaseFailure]:
    failed_test_cases = []

    for test_report in test_job.test_results.matrix_test_reports:
        for suite in test_report.test_result.suites:
            for case in suite.cases:
                if case.status == "FAILED":
                    failed_test_cases.append(
                        TestCaseFailure.from_data(
                            test_report=test_report,
                            test_case=case,
                            job_run=test_job
                        )
                    )

    return failed_test_cases


def compile_failed_test_cases(test_job_runs: List[TestMatrixJobRun]) -> List[TestCaseFailure]:
    failed_test_cases = []
    for test_job in test_job_runs:
        failed_test_cases.extend(get_failed_test_cases(test_job))
    return failed_test_cases

def create_pandas_dataframe_for_failing_tests(test_job_runs: List[TestMatrixJobRun]) -> pd.DataFrame:
    """
    Create a pandas dataframe for failing tests from the given list of TestMatrixJobRun objects

    Args:
        test_job_runs: List of TestMatrixJobRun objects to extract failing tests from

    Returns:
        DataFrame: A pandas DataFrame containing the following columns:
            - test_case_name: Name of the test case
            - config_string: Configuration string for the test case
            - error_text: Error text for the test case
            - job_name: Name of the job run
            - serial: Serial number of the job run
            - suite: Suite of the job run
            - family: Family type of the image ("Base" or "Minimal")
            - build_number: Build number of the job run
            - job_run_url: URL of the job run
            - test_case_url: URL of the test case
    """
    failed_test_cases = compile_failed_test_cases(test_job_runs)
    return pd.DataFrame([test_case.model_dump() for test_case in failed_test_cases])


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


def get_test_reports_for_failed_test(
    test_name: str,
    test_job_runs: List[TestMatrixJobRun],
    
) -> List[MatrixTestReport]:
    """
    We want to return the matrix test report for all failed tests with the given test name
    """
    results = []
    for job_run in test_job_runs:
        # Loop through matrix test reports in each job run
        if not job_run.test_results:
            continue  # Skip if there are no test results

        for test_report in job_run.test_results.matrix_test_reports:
            config = test_report.test_config
            
            # Loop through suites and test cases
            for suite in test_report.test_result.suites:
                for case in suite.cases:
                    # Check if test case status is FAILED and apply TestCase 'name' filter
                    if case.status == "FAILED" and case.name == test_name:
                        # print(f"Test Case: {case.name}")
                        # print(f"Error Details: {case.error_details}\n")
                        results.append(test_report)
                    
    return results

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

