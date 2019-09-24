import os
import pwd

#-------------------------------------------------------------------------------

def get_username():
    """
    Returns the username of the process owner.
    """
    return pwd.getpwuid(os.getuid()).pw_name


