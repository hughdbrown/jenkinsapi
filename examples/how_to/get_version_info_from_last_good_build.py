"""
Extract version information from the latest build.
"""
from jenkinsapi.jenkins import Jenkins

JENKINS = 'http://localhost:8080'


def getSCMInfroFromLatestGoodBuild(url, jobname, username=None, password=None):
    J = Jenkins(url, username, password)
    job = J[jobname]
    lgb = job.get_last_good_build()
    return lgb.get_revision()

if __name__ == '__main__':
    print getSCMInfroFromLatestGoodBuild(JENKINS, 'fooJob')
