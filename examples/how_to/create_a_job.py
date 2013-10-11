import logging
logging.basicConfig()

from jenkinsapi.jenkins import Jenkins
from pkg_resources import resource_string

JENKINS = 'http://localhost:8080'

def main():
    J = Jenkins(JENKINS)
    jobname = 'foo_job2'
    xml = resource_string('examples', 'addjob.xml')

    print xml

    j = J.create_job(jobname=jobname, config=xml)
    j2 = J[jobname]
    print j

    # Delete job
    J.delete_job(jobname)

if __name__ == '__main__':
    main()

