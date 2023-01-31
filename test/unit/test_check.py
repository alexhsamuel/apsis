from   pathlib import Path
import pytest
from   typing import List

from   apsis.cond.dependency import Dependency
import apsis.jobs
from   apsis.jobs import InMemoryJobs, Job

#-------------------------------------------------------------------------------

def check_job(jobs, job_id) -> List[str]:
    job = jobs.get_job(job_id)
    return list(apsis.jobs.check_job(jobs, job))


def test_dependency_no_job():
    """
    Check fails if a dependency on a nonexistent job.
    """
    jobs = InMemoryJobs((
        Job("job0"),
        Job("job1", conds=[Dependency("job0")]),
        Job("job2", conds=[Dependency("not-a-job")]),
    ))

    # No deps.
    assert check_job(jobs, "job0") == []
    # Valid dep job ID.
    assert check_job(jobs, "job1") == []
    # Invalid dep job ID.
    assert check_job(jobs, "job2") != []


