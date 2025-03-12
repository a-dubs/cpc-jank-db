from cpc_jank_db.models import MatrixJobRun


def get_matrix_job_results(matrix_job: MatrixJobRun):
    # take in a matrix job and get statuses for each child run (matrix_runs field)
    # return a dictionary that contains the string representation of the matrix run config as the key
    # and the value is the run status (PASSED, FAILED, etc.)
    matrix_job_statuses = {}
    for child_run in matrix_job.matrix_runs:
        matrix_job_statuses[child_run.config_string] = child_run.result
    return matrix_job_statuses


def get_matrix_job_results_stats(matrix_job: MatrixJobRun) -> dict[str, int]:
    # take in a matrix job and get statuses for each child run (matrix_runs field)
    # Literal["SUCCESS", "FAILURE", "UNSTABLE", "ABORTED"]

    results = {"SUCCESS": 0, "FAILURE": 0, "UNSTABLE": 0, "ABORTED": 0}

    for child_run in matrix_job.matrix_runs:
        if child_run.result in results:
            results[child_run.result] += 1
    return results
