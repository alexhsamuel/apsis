"""
Runs job instances.

This module is a placeholder.
"""

#-------------------------------------------------------------------------------

import subprocess

#-------------------------------------------------------------------------------

def start(job):
    proc = subprocess.Popen(job.command, shell=True)
    return proc


