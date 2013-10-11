from jenkinsapi.api import search_artifact_by_regexp
import re

JENKINS = "http://localhost:8080/jenkins"


def main():
    jobid = "test1"
    artifact_regexp = re.compile(r"""test1\.txt""")  # A file name I want.
    result = search_artifact_by_regexp(JENKINS, jobid, artifact_regexp)
    print(repr(result))

if __name__ == '__main__':
    main()

