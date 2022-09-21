from   .base import Condition
from   .dependency import Dependency
from   .file import FileExists
from   .max_running import MaxRunning

Condition.TYPE_NAMES.set(Dependency, "dependency")
Condition.TYPE_NAMES.set(MaxRunning, "max_running")
Condition.TYPE_NAMES.set(FileExists, "file_exists")

