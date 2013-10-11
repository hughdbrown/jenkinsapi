"""
An example of how to use JenkinsAPI to fetch the config XML of a job.
"""
from jenkinsapi.jenkins import Jenkins

JENKINS = 'http://localhost:8080'

def main():
    J = Jenkins(JENKINS)
    jobname = 'create_fwrgmkbbzk'

    config = J[jobname].get_config()

    print config

if __name__ == '__main__':
    main()

