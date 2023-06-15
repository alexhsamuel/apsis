import ora
import random

from   apsis.runs import Instance, Run, RunStore

#-------------------------------------------------------------------------------

class MockRunDb:

    def query(self, min_timestamp=None):
        return iter(())


    def upsert(self, run):
        pass



class MockRunIdDb:

    def __init__(self):
        self.i = 0


    def get_next_run_id(self):
        self.i += 1
        return f"r{self.i:06d}"



class MockDb:

    def __init__(self):
        self.run_db = MockRunDb()
        self.next_run_id_db = MockRunIdDb()



#-------------------------------------------------------------------------------

def test_runs_by_job():
    rnd = random.Random(0)
    n = 10000

    job_ids = [ f"job{i:02d}" for i in range(100) ]
    rnd.shuffle(job_ids)

    # Create a random run store and add a bunch of runs.
    run_store = RunStore(MockDb(), min_timestamp=ora.now())
    for _ in range(n):
        run = Run(Instance(rnd.choice(job_ids), {}), expected=True)
        run_store.add(run)

    query = lambda *a, **k: run_store.query(*a, **k)[1]
    get = lambda r: run_store.get(r)[1]

    run_ids = [ r.run_id for r in query() ]
    assert len(run_ids) == n

    # Confirm that they are all available by job.
    runs = query()
    for run in runs:
        assert run in query(job_id=run.inst.job_id)

    # Now remove some runs.
    for run_id in rnd.sample(run_ids, len(run_ids) // 5):
        run_store.remove(run_id)
        run_ids.remove(run_id)

    assert set( r.run_id for r in query() ) == set(run_ids)

    # Confirm that they are all available by job.
    for run_id in run_ids:
        _, run = run_store.get(run_id)
        assert run in query(job_id=run.inst.job_id)

    # Confirm that no extraneous jobs are left.
    r = set.union(*(
        set( r.run_id for r in query(job_id=j) )
        for j in job_ids 
    ))
    assert r == set(run_ids)

    # Now remove some more runs.
    for run_id in rnd.sample(run_ids, len(run_ids) // 4):
        run_store.remove(run_id)
        run_ids.remove(run_id)

    assert set( r.run_id for r in query() ) == set(run_ids)

    # Confirm that they are all available by job.
    for run_id in run_ids:
        _, run = run_store.get(run_id)
        assert run in query(job_id=run.inst.job_id)

    # Confirm that no extraneous jobs are left.
    r = set.union(*(
        set( r.run_id for r in query(job_id=j) )
        for j in job_ids 
    ))
    assert r == set(run_ids)


