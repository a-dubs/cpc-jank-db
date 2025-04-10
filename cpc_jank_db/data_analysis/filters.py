from datetime import datetime
from typing import Literal, Optional, Tuple

import pandas as pd
from pydantic import BaseModel


class NumericalFilterParam(BaseModel):
    value: int | float | datetime | str
    op: Literal["eq", "gt", "lt", "ge", "le"] = "eq"

    @property
    def comparator_function(self):
        if self.op == "eq":
            return lambda x: x == self.value
        elif self.op == "gt":
            return lambda x: x > self.value
        elif self.op == "lt":
            return lambda x: x < self.value
        elif self.op == "ge":
            return lambda x: x >= self.value
        elif self.op == "le":
            return lambda x: x <= self.value
        else:
            raise ValueError(f"Invalid op: {self.op}")

    def __str__(self):
        symbols = {
            "eq": "==",
            "gt": ">",
            "lt": "<",
            "ge": ">=",
            "le": "<=",
        }
        return f"{symbols[self.op]}{self.value}"


class DatetimeFilterParam(NumericalFilterParam):
    value: datetime
    op: Literal["eq", "gt", "lt", "ge", "le"] = "eq"
    # TODO: implement roughly equal to i.e. same day or maybe even make the interval configurable

class FloatFilterParam(NumericalFilterParam):
    value: float


class IntegerFilterParam(NumericalFilterParam):
    value: int


class StringFilterParam(NumericalFilterParam):
    value: str


def filter_param_factory(
    value: int | float | datetime | str, op: Optional[str] = None
):
    if isinstance(value, int):
        return IntegerFilterParam(value=value, op=op)
    elif isinstance(value, float):
        return FloatFilterParam(value=value, op=op)
    elif isinstance(value, str):
        return StringFilterParam(value=value)
    elif isinstance(value, datetime):
        return DatetimeFilterParam(value=value, op=op)
    else:
        raise ValueError(f"Invalid value type: {type(value)}")


class TestFailureFilter(BaseModel):
    """
    Available values to filter on:
        - test_case_name: Name of the test case
        - test_case_class_name: Name of the test case class
        - error_text: Error text for the test case
        - error_stack_trace: Error stack trace for the test case
        - job_name: Name of the job run
        - build_number: Build number of the job run
        - job_run_url: URL of the job run
        - test_case_url: URL of the test case
        - timestamp: Timestamp that the test was run (as pandas datetime64[ns])

    Each filter param is optional and supports proper regex matching (case insensitive).
    Note: don't use "*", use ".*" instead for regex matching.

    A filter represents a logical AND such that all filter params must match for a test case to match this filter.

    """

    test_case_name: Optional[str] = None
    test_case_class_name: Optional[str] = None
    error_text: Optional[str] = None
    error_stack_trace: Optional[str] = None
    suite: Optional[str] = None
    job_name: Optional[str] = None
    build_number: Optional[IntegerFilterParam] = None
    job_run_url: Optional[str] = None
    test_case_url: Optional[str] = None
    timestamp: Optional[DatetimeFilterParam] = None

    filter_name: str = "Unnamed Filter"
    filter_description: str = "No description provided"
    filter_operator: Literal["AND", "OR"] = "AND"

    def __str__(self):
        return type(self).__name__ + str(
            [f"{k}={v}" for k, v in self.model_dump().items() if v is not None]
        )

    def display(self) -> str:
        r = self.filter_name + ":\n"
        r += self.filter_description
        for field, value in self.model_dump().items():
            if value is not None:
                r += f"\n  {field}: {value}"
        return r

    @property
    def filter_params(self) -> dict[str, str | NumericalFilterParam]:
        d = {
            field_name: (
                filter_param_factory(**value)
                if isinstance(value, dict)
                else value
            )
            for field_name, value in self.model_dump().items()
            if field_name
            not in ["filter_name", "filter_description", "filter_operator"]
            and value is not None
        }
        for field, value in d.items():
            # if a value is a dictionary, turn it back into the proper pydantic model
            if isinstance(value, dict):
                d[field] = filter_param_factory(**value)
        return d

    def apply_filter_to_df(
        self, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Apply this filter to a DataFrame of test failures.

        This does not modify the original DataFrame, but instead returns two new DataFrames:
            - DataFrame of test failures that match this filter
            - DataFrame of test failures that do not match this filter

        Args:
            df: DataFrame of test failures

        Returns:
            Tuple: tuple will contain two DataFrames:
                - DataFrame of test failures that match this filter
                - DataFrame of test failures that do not match this filter
        """

        if self.filter_operator == "AND":
            filtered_df = df.copy()
            for field, value in self.filter_params.items():
                if value is not None:
                    if isinstance(value, NumericalFilterParam):
                        filtered_df = filtered_df[
                            filtered_df[field].apply(value.comparator_function)
                        ]
                    else:
                        filtered_df = filtered_df[
                            filtered_df[field].str.contains(
                                value, case=False, na=False
                            )
                        ]
            return filtered_df, df[~df.index.isin(filtered_df.index)]
        elif self.filter_operator == "OR":
            unfiltered_df = df.copy()
            for field, value in self.filter_params.items():
                if value is not None:
                    if isinstance(value, NumericalFilterParam):
                        unfiltered_df = unfiltered_df[
                            ~unfiltered_df[field].apply(
                                value.comparator_function
                            )
                        ]
                    else:
                        unfiltered_df = unfiltered_df[
                            ~unfiltered_df[field].str.contains(
                                value, case=False, na=False
                            )
                        ]
            return df[~df.index.isin(unfiltered_df.index)], unfiltered_df
        else:
            raise ValueError(
                f"Invalid operator for filter: {self.filter_operator}"
            )


class CITestFailureFilter(TestFailureFilter):
    """
    Filter meant specifically for cloud-init jenkins test failures.

    Available TestFailureFilter filters:
        - test_case_name: Name of the test case
        - test_case_class_name: Name of the test case class
        - error_text: Error text for the test case
        - error_stack_trace: Error stack trace for the test case
        - job_name: Name of the job run
        - build_number: Build number of the job run
        - job_run_url: URL of the job run
        - test_case_url: URL of the test case
        - timestamp: Timestamp that the test was run (as pandas datetime64[ns])

    Supplemental CiTestFailureFilter filters:
        - image_type: Type of the image ("generic" or "minimal")
        - suite: Suite of the job run
        - cloud_name: Name of the cloud
        - cloud_init_version: Version of cloud-init used in the test run
    """

    suite: Optional[str] = None
    cloud_name: Optional[str] = None
    image_type: Optional[str] = None
    cloud_init_version: Optional[str | NumericalFilterParam] = None


def apply_all_filters_to_df(
    df: pd.DataFrame, filters: list[TestFailureFilter]
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Apply all filters in the list to a DataFrame of test failures.

    Uses logical OR for the filters because each filter itself is a logical AND.

    This does not modify the original DataFrame, but instead returns two new DataFrames:
        - DataFrame of test failures that match any of the filters
        - DataFrame of test failures that do not match all filters

    Args:
        df: DataFrame of test failures
        filters: List of TestFailureFilter instances

    Returns:
        Tuple: tuple will contain two DataFrames:
            - DataFrame of test failures that match all filters
            - DataFrame of test failures that do not match all filters
    """
    if len(df) == 0:
        return df, df
    og_df = df.copy()
    result = pd.DataFrame()
    for filter in filters:
        filtered, _ = filter.apply_filter_to_df(og_df)
        result = pd.concat([result, filtered])
    return result, df[~df.index.isin(result.index)]
