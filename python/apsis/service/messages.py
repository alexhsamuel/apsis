from   apsis.lib.api import job_to_jso, run_to_summary_jso

#-------------------------------------------------------------------------------

def make_job(job):
    return {
        "type"          : "job",
        "job"           : job_to_jso(job),
    }


def make_job_add(job):
    return {
        "type"          : "job_add",
        "job"           : job_to_jso(job),
    }


def make_job_delete(job_id):
    return {
        "type"          : "job_delete",
        "job_id"        : job_id,
    }


def make_run_delete(run):
    return {
        "type"          : "run_delete",
        "run_id"        : run.run_id,
    }


def make_run_summary(run):
    return {
        "type"          : "run_summary",
        "run_summary"   : run_to_summary_jso(run),
    }


