from   apsis.jobs import Job
from   apsis.runs import Run, Instance
from   apsis.cond.dependency import Dependency

#-------------------------------------------------------------------------------

JOBS = {
    "testjob0": Job("testjob0", {"foo"}, (), None),
    "testjob1": Job("testjob1", {"foo", "bar"}, (), None),
}

def test_bind0():
    # testjob1 depends on testjob0 with explicit arg.
    dep = Dependency("testjob0", {"foo": "banana"})
    run = Run(Instance("testjob1", {"foo": "apple", "bar": "celery"}))
    bound = dep.bind(run, JOBS)

    assert bound.job_id == "testjob0"
    assert bound.args == {"foo": "banana"}
    assert bound.states == dep.states


def test_bind1():
    # testjob1 depends on testjob0 with inherited arg.
    dep = Dependency("testjob0", {})
    run = Run(Instance("testjob1", {"foo": "apple", "bar": "celery"}))
    bound = dep.bind(run, JOBS)

    assert bound.job_id == "testjob0"
    assert bound.args == {"foo": "apple"}
    assert bound.states == dep.states


def test_bind2():
    # testjob0 depends on testjob1 with one explicit, one inherited arg.
    dep = Dependency("testjob1", {"bar": "celery"})
    run = Run(Instance("testjob0", {"foo": "apple"}))
    bound = dep.bind(run, JOBS)

    assert bound.job_id == "testjob1"
    assert bound.args == {"foo": "apple", "bar": "celery"}
    assert bound.states == dep.states


def test_bind3():
    # testjob0 depends on testjob1 with one expanded, one inherited arg.
    dep = Dependency("testjob1", {"bar": "{{ foo }}s"})
    run = Run(Instance("testjob0", {"foo": "apple"}))
    bound = dep.bind(run, JOBS)

    assert bound.job_id == "testjob1"
    assert bound.args == {"foo": "apple", "bar": "apples"}
    assert bound.states == dep.states


