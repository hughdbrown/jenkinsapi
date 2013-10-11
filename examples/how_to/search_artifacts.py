from jenkinsapi.api import search_artifacts

JENKINS = "http://localhost:8080/jenkins"


def main():
    jobid = "test1"
    # I need a build that contains all of these
    artifact_ids = ["test1.txt", "test2.txt"]
    result = search_artifacts(JENKINS, jobid, artifact_ids)
    print(repr(result))

if __name__ == '__main__':
    main()

