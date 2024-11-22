from cpc_jank_db import utils
from pydantic import BaseModel, Field, HttpUrl
from typing import List, Literal, Optional, Dict
from datetime import datetime
import re


class TestCase(BaseModel):
    test_actions: List[Dict] = Field(alias="testActions")
    age: int
    class_name: str = Field(alias="className")
    duration: float
    # failed_since: Optional[int] = Field(alias="failedSince")
    name: str
    skipped: bool
    status: str  # e.g., "PASSED", "FAILED", "SKIPPED"
    # these will be be filled in later only if the test failed
    error_details: Optional[str] = Field(alias="errorDetails", default=None)
    error_stack_trace: Optional[str] = Field(alias="errorStackTrace", default=None)

    @classmethod
    def from_data(cls, data: dict):
        return cls(**data)

class TestSuite(BaseModel):
    cases: List[TestCase]
    duration: float
    # enclosing_block_names: List[str] = Field(alias="enclosingBlockNames")
    # enclosing_blocks: List[Dict] = Field(alias="enclosingBlocks")
    id: Optional[str]
    name: str
    node_id: Optional[str] = Field(alias="nodeId")
    timestamp: datetime

    @classmethod
    def from_data(cls, data: dict):
        cases = [TestCase.from_data(case) for case in data["cases"]]
        data["cases"] = cases
        return cls(**data)

class Job(BaseModel):
    url: str
    name: str = Field(alias="fullDisplayName")
    build_numbers: List[int] = Field(alias="buildNumbers")
    last_completed_build_number: Optional[int] = Field(alias="lastCompletedBuildNumber", default=None)
    suite: str
    family: Literal["Base", "Minimal"]
    description: Optional[str] = None
    last_updated: datetime = Field(alias="lastUpdated", default_factory=datetime.now)

    def __init__(self, **data):
        if "family" not in data:
            name = data.get("fullDisplayName") or data.get("name")
            data["family"] = "Minimal" if "minimal" in name.lower() else "Base"
        super().__init__(**data)

    @classmethod
    def from_data(cls, **data):
        return cls(**data)

class JobRun(BaseModel):
    self_class: str = Field(frozen=True, default="JobRun")
    url: str
    name: str = Field(alias="fullDisplayName")
    build_number: int = Field(alias="buildNumber")
    serial: str
    suite: str
    family: Literal["Base", "Minimal"]
    description: Optional[str] = None
    timestamp_ms: int = Field(description="Timestamp of the job run in ms since epoch")
    duration_ms: int = Field(description="Duration of the job run in milliseconds")
    build_parameters: Dict[str, str] = Field(alias="buildParameters")
    result: Literal["SUCCESS", "FAILURE", "UNSTABLE", "ABORTED"]
    child_runs_urls: Optional[List[str]] = Field(
        alias="childRunsUrls",
        default=None,
        description="If this is a matrix job, this will contain the URLs of the child runs."
            "Otherwise, it will be None to indicate that this is not a matrix job.", 
    )
    console_output: Optional[str] = Field(alias="consoleOutput", default=None)

    def __init__(self, **data):
        if "family" not in data:
            name = data.get("fullDisplayName") or data.get("name")
            data["family"] = "Minimal" if "minimal" in name.lower() else "Base"
        super().__init__(**data)

    @classmethod
    def from_data(cls, **data):
        return cls(**data)

    @property
    def unique_identifier(self):
        return f"{self.name}-{self.serial}-{self.build_number}"
    
    @property
    def job_name(self):
        return self.name.split("#")[0].strip()

class MatrixTestRunConfig(BaseModel):
    arch: Optional[str]
    instance_type: Optional[str]
    test: Optional[str]
    # debug_log_file_fetched: bool = Field(alias="debugLogFileFetched", default=False)

    @classmethod
    def parse_url(cls, url: str, ignore_keys: List[str] = ["node"]):
        # Parse the KEY=VALUE pairs in the URL path
        pattern = r"(?P<key>\w+?)=(?P<value>[\w\.\d\-]+)"
        matches = re.findall(pattern, url)
        url_params = {key.lower(): value for key, value in matches if key.lower() not in ignore_keys}
        return url_params

    @classmethod
    def from_data(cls, url: str, **data):
        url_params = cls.parse_url(url)
        # the build number is originally called "number"
        data["buildNumber"] = data.pop("number", None)
        return cls(url=url, **url_params, **data)
    
    @property
    def config_string(self):
        return " ".join([f"{key}={value}" for key, value in self.dict().items() if key not in ["url"]])

class OracleMatrixTestRunConfig(MatrixTestRunConfig):
    launch_mode: str = Field(alias="launchMode")
    login_method: str = Field(alias="loginMethod")

def getMatrixTestRunConfigClass(config: dict):
    if "launchMode" in config and "loginMethod" in config:
        return OracleMatrixTestRunConfig
    else:
        return MatrixTestRunConfig

class TestResult(BaseModel):
    test_actions: List[Dict] = Field(alias="testActions")
    duration: float
    empty: bool
    fail_count: int = Field(alias="failCount")
    pass_count: int = Field(alias="passCount")
    skip_count: int = Field(alias="skipCount")
    suites: List[TestSuite]

    @classmethod
    def from_data(cls, **data):
        suites = [TestSuite.from_data(suite) for suite in data["suites"]]
        data["suites"] = suites
        return cls(**data)

class MatrixTestReport(BaseModel):
    test_config: MatrixTestRunConfig = Field(alias="testConfig")
    test_result: TestResult = Field(alias="testResult")
    url: str

    @classmethod
    def from_data(cls, child: dict, result: dict):
        print("test_report_url", child["url"])
        config_class = getMatrixTestRunConfigClass(child)
        config_obj = config_class.from_data(**child)
        result = TestResult.from_data(**result)
        return cls(testConfig=config_obj, testResult=result, url=child["url"])
    
    def generate_test_case_report_url(self, test_case_name: str, test_case_class: str):
        test_case_class = utils.rreplace(test_case_class, ".", "/", 1)
        return f"{self.url.rstrip('/')}/testReport/junit/{test_case_class}/{test_case_name}"

class MatrixTestResults(BaseModel):
    fail_count: int = Field(alias="failCount")
    skip_count: int = Field(alias="skipCount")
    total_count: int = Field(alias="totalCount")
    matrix_test_reports: List[MatrixTestReport] = Field(alias="matrixTestReports")

    @classmethod
    def from_data(cls, **data):
        matrix_test_reports = [MatrixTestReport.from_data(**report) for report in data["childReports"]]
        return cls(matrixTestReports=matrix_test_reports, **data)

class MatrixChildRun(JobRun):
    self_class: str = Field(frozen=True, default="MatrixChildRun")
    matrix_run_config: dict = Field(alias="matrixRunConfig")

    def __init__(self, **data):
        if "family" not in data:
            name = data.get("fullDisplayName") or data.get("name")
            data["family"] = "Minimal" if "minimal" in name.lower() else "Base"
        super().__init__(**data)

    @classmethod
    def parse_url(cls, url: str, ignore_keys: List[str] = ["node"]):
        # Parse the KEY=VALUE pairs in the URL path
        pattern = r"(?P<key>\w+?)=(?P<value>[\w\.\d\-]+)"
        matches = re.findall(pattern, url)
        url_params = {key.lower(): value for key, value in matches if key.lower() not in ignore_keys}
        return url_params

    @classmethod
    def from_data(cls, **data):
        matrix_run_config = cls.parse_url(data["url"])
        return cls(matrixRunConfig=matrix_run_config, **data)

    @property
    def config_string(self):
        return ",".join([f"{key}={value}" for key, value in self.matrix_run_config.items()])
    
    @property
    def config_values_string(self):
        return " ".join([f"{value}" for value in self.matrix_run_config.values()])

class MatrixJobRun(JobRun):
    self_class: str = Field(frozen=True, default="MatrixJobRun")

    matrix_runs: List[MatrixChildRun] = Field(default_factory=list)

    @classmethod
    def from_data(cls, matrix_runs: List[dict], **data):
        matrix_run_objs = [MatrixChildRun.from_data(**run) for run in matrix_runs]
        job_run = super().from_data(**data)
        job_run.matrix_runs = matrix_run_objs
        return job_run

class TestMatrixJobRun(MatrixJobRun):
    self_class: str = Field(frozen=True, default="TestMatrixJobRun")
    
    test_results: Optional[MatrixTestResults] = Field(alias="testResults", default=None)

    @classmethod
    def from_data(cls, job_run_json: dict, test_results_json: dict, matrix_runs: List[dict]):
        test_results = MatrixTestResults.from_data(**test_results_json)
        result = super().from_data(matrix_runs=matrix_runs, **job_run_json)
        result.test_results = test_results
        return result


    def fetch_error_texts_for_failed_tests(self, fetch_error_texts: callable):
        """
        Fetches the error details and stack trace for failed
        
        Args:
            fetch_error_texts: callable that takes in the URL of the test report and returns a tuple of error details and stack trace
        """

        for test_report in self.test_results.matrix_test_reports:
            for suite in test_report.test_result.suites:
                for case in suite.cases:
                    if case.status == "FAILED":
                        try:
                            error_details, error_stack_trace = fetch_error_texts(
                                test_report.generate_test_case_report_url(
                                    test_case_name=case.name,
                                    test_case_class=case.class_name,
                                )
                            )
                        except Exception as e:
                            print(f"Failed to fetch error texts for {case.name}, {case.class_name}, {self.url}")
                            raise e
                        case.error_details = error_details
                        case.error_stack_trace = error_stack_trace

# full fetch involves getting the parent job, getting 
