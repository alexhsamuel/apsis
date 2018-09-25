import random
import sqlalchemy as sa
import string
import time

SIZE = 1024
NUM = 1024

METADATA = sa.MetaData()

TABLE = sa.Table(
    "data", METADATA,
    sa.Column("id", sa.Integer(), primary_key=True),
    sa.Column("data", sa.String(), nullable=False),
)

url = "sqlite:///concat.db"
engine = sa.create_engine(url)
METADATA.create_all(engine)

with engine.begin() as con:
    con.execute(TABLE.insert().values(id=42, data=""))

data = "".join( random.choice(string.ascii_lowercase) for _ in range(SIZE) )

for i in range(NUM):
    t0 = time.perf_counter()
    with engine.begin() as con:
        con.execute("UPDATE data SET data = data || ?", (data, ))
    el = time.perf_counter() - t0
    print(el)


