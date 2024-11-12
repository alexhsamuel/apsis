from   pathlib import Path
import pytest
import yaml

from   apsis.exc import JobsDirErrors
import apsis.jobs

#-------------------------------------------------------------------------------

def dump_yaml_file(obj, path):
    with path.open("w") as file:
        yaml.dump(obj, file)


def test_name_error(tmp_path):
    """
    Tests that a job with an unknown param in an expansion is not loaded.
    """
    jobs_path = tmp_path
    job_path = jobs_path / "job.yaml"

    job = {
        "params": ["date"],
        "schedule": {
            "type": "daily",
            "tz": "America/New_York",
            "calendar": "Mon-Fri",
            "daytime": "09:00:00",
        },
        "program": {
            "type": "procstar-shell",
            "command": "today is {{ date }} and my name is {{ name }}",
        },
    }
    dump_yaml_file(job, job_path)

    # The program's command has an invalid expansion 'name'.
    try:
        apsis.jobs.load_jobs_dir(jobs_path)
    except JobsDirErrors as exc:
        assert len(exc.errors) == 1
        assert "'name'" in str(exc.errors[0])
    else:
        assert False, "expected jobs dir error"

    # Add 'name' to the params and schedule args.  Now it should be fine.
    job["params"].append("name")
    job["schedule"]["args"] = {"name": "bob"}
    dump_yaml_file(job, job_path)
    apsis.jobs.load_jobs_dir(jobs_path)


def test_syntax_error(tmp_path):
    """
    Tests that a job with a syntax error inside an expanded expression is not
    loaded.
    """
    jobs_path = tmp_path
    job_path = jobs_path / "job.yaml"

    job = {
        "params": ["date"],
        "schedule": {
            "type": "interval",
            "interval": "1d",
        },
        "program": {
            "type": "procstar-shell",
            "command": "today is {{ date }} and also {{ date date }}",
        },
    }
    dump_yaml_file(job, job_path)

    # The program's command has an invalid expansion 'name'.
    try:
        apsis.jobs.load_jobs_dir(jobs_path)
    except JobsDirErrors as exc:
        assert len(exc.errors) == 1
        assert "expected token" in str(exc.errors[0])
    else:
        assert False, "expeceted jobs dir error"

    # Fix the command.  Now it should be fine.
    job["program"]["command"] = "today is {{ date }}"
    dump_yaml_file(job, job_path)
    apsis.jobs.load_jobs_dir(jobs_path)


def test_misspelled_param(tmp_path):
    """
    Tests that a job with a misspelled param name inside an expanded
    expression is not loaded.
    """
    jobs_path = tmp_path
    job_path = jobs_path / "job.yaml"

    # Create a dependency job.
    dump_yaml_file(
        {"params": ["date"], "program": {"type": "no-op"}},
        jobs_path / "dependency.yaml"
    )

    job = {
        "params": ["date"],
        "schedule": {
            "type": "interval",
            "interval": "1d",
        },
        "condition": {
            "type": "dependency",
            "job_id": "dependency",
            "args": {
                "date": "{{ get_calendar('Mon-Fri').before(data) }}",
            },
        },
        "program": {"type": "no-op"},
    }
    dump_yaml_file(job, job_path)

    # The program's command has an invalid expansion 'name'.
    try:
        apsis.jobs.load_jobs_dir(jobs_path)
    except JobsDirErrors as exc:
        for err in exc.errors:
            import traceback
            traceback.print_exception(exc, chain=True)

        assert len(exc.errors) == 1
        assert "'data' is not defined" in str(exc.errors[0])
    else:
        assert False, "expeceted jobs dir error"

    # Fix the command.  Now it should be fine.
    job["condition"]["args"]["date"] = "{{ get_calendar('Mon-Fri').before(date) }}"
    dump_yaml_file(job, job_path)
    apsis.jobs.load_jobs_dir(jobs_path)


