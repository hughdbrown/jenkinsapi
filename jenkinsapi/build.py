"""
Build API methods
"""

import time
from time import sleep
import pytz
import datetime
import logging

from jenkinsapi.artifact import Artifact
from jenkinsapi import config
from jenkinsapi.jenkinsbase import JenkinsBase
from jenkinsapi.custom_exceptions import NoResults
from jenkinsapi.constants import STATUS_SUCCESS
from jenkinsapi.result_set import ResultSet


log = logging.getLogger(__name__)


class Build(JenkinsBase):
    """
    Represents a jenkins build, executed in context of a job.
    """

    STR_TOTALCOUNT = "totalCount"
    STR_TPL_NOTESTS_ERR = "%s has status %s, and does not have any test results"

    def __init__(self, url, buildno, job):
        assert type(buildno) == int
        self.buildno = buildno
        self.job = job
        JenkinsBase.__init__(self, url)

    def _poll(self):
        #For build's we need more information for downstream and upstream builds
        #so we override the poll to get at the extra data for build objects
        url = self.python_api_url(self.baseurl) + '?depth=2'
        return self.get_data(url)

    def __str__(self):
        return self._data['fullDisplayName']

    @property
    def name(self):
        return str(self)

    def get_number(self):
        return self._data["number"]

    def get_status(self):
        return self._data["result"]

    def get_revision(self):
        vcs = self._data['changeSet']['kind'] or 'git'
        return getattr(self, '_get_%s_rev' % vcs, lambda: None)()

    def _get_svn_rev(self):
        src = self._data["changeSet"]["revisions"]
        return max(repoPathSet["revision"] for repoPathSet in src) if src else 0

    def _get_git_rev(self):
        # Sometimes we have None as part of actions. Filter those actions
        # which have lastBuiltRevision in them
        _actions = [x for x in self._data['actions']
                    if x and "lastBuiltRevision" in x]
        # FIXME So this code returns the first item found in the filtered
        # list. Why not just:
        #     `return _actions[0]["lastBuiltRevision"]["SHA1"]`
        for item in _actions:
            revision = item["lastBuiltRevision"]["SHA1"]
            return revision

    def _get_hg_rev(self):
        src = self._data['actions']
        return src['mercurialNodeName']

    def get_duration(self):
        return datetime.timedelta(milliseconds=self._data["duration"])

    def get_artifacts(self):
        for afinfo in self._data["artifacts"]:
            url = "%s/artifact/%s" % (self.baseurl, afinfo["relativePath"])
            yield Artifact(afinfo["fileName"], url, self)

    def get_artifact_dict(self):
        return dict(
            (af.filename, af) for af in self.get_artifacts()
        )

    def get_upstream_job_name(self):
        """
        Get the upstream job name if it exist, None otherwise
        :return: String or None
        """
        try:
            return self.get_actions()['causes'][0]['upstreamProject']
        except KeyError:
            return None

    def get_upstream_job(self):
        """
        Get the upstream job object if it exist, None otherwise
        :return: Job or None
        """
        upstream = self.get_upstream_job_name()
        return self.get_jenkins_obj().get_job(upstream) if upstream else None

    def get_upstream_build_number(self):
        """
        Get the upstream build number if it exist, None otherwise
        :return: int or None
        """
        try:
            return int(self.get_actions()['causes'][0]['upstreamBuild'])
        except KeyError:
            return None

    def get_upstream_build(self):
        """
        Get the upstream build if it exist, None otherwise
        :return Build or None
        """
        upstream_job = self.get_upstream_job()
        return upstream_job.get_build(self.get_upstream_build_number()) if upstream_job else None

    def get_master_job_name(self):
        """
        Get the master job name if it exist, None otherwise
        :return: String or None
        """
        try:
            return self.get_actions()['parameters'][0]['value']
        except KeyError:
            return None

    def get_master_job(self):
        """
        Get the master job object if it exist, None otherwise
        :return: Job or None
        """
        master_job = self.get_master_job_name()
        return self.get_jenkins_obj().get_job(master_job) if master_job else None

    def get_master_build_number(self):
        """
        Get the master build number if it exist, None otherwise
        :return: int or None
        """
        try:
            return int(self.get_actions()['parameters'][1]['value'])
        except KeyError:
            return None

    def get_master_build(self):
        """
        Get the master build if it exist, None otherwise
        :return Build or None
        """
        master_job = self.get_master_job()
        return master_job.get_build(self.get_master_build_number()) if master_job else None

    def get_downstream_jobs(self):
        """
        Get the downstream jobs for this build
        :return List of jobs
        """
        try:
            names = self.get_downstream_job_names()
            obj = self.get_jenkins_obj()
            return [obj.get_job(name) for name in names]
        except (IndexError, KeyError):
            return []

    def get_downstream_job_names(self):
        """
        Get the downstream job names for this build
        :return List of string
        """
        downstream_jobs_names = self.job.get_downstream_job_names()
        base = self.python_api_url(self.baseurl)
        url = "%s?depth=2&tree=fingerprint[usage[name]]" % base
        fingerprint_data = self.get_data(url)
        try:
            fingerprints = fingerprint_data['fingerprint'][0]
            name_iter = (f['name'] for f in fingerprints['usage'])
            return [name for name in name_iter if name in downstream_jobs_names]
        except (IndexError, KeyError):
            return []

    def get_downstream_builds(self):
        """
        Get the downstream builds for this build
        :return List of Build
        """
        downstream_jobs_names = set(self.job.get_downstream_job_names())
        base = self.python_api_url(self.baseurl)
        url = "%s?depth=2&tree=fingerprint[usage[name,ranges[ranges[end,start]]]]" % base
        fingerprint_data = self.get_data(url)
        try:
            fingerprints = fingerprint_data['fingerprint'][0]
            name_range_iter = ((f['name'], f['ranges']) for f in fingerprints['usage'])
            obj = self.get_jenkins_obj()
            return [
                obj.get_job(name).get_build(ranges['ranges'][0]['start'])
                for name, ranges in name_range_iter
                if name in downstream_jobs_names
            ]
        except (IndexError, KeyError):
            return []

    def get_matrix_runs(self):
        """
        For a matrix job, get the individual builds for each
        matrix configuration
        :return: Generator of Build
        """
        for rinfo in self._data.get("runs", []):
            yield Build(rinfo["url"], rinfo["number"], self.job)

    def is_running(self):
        """
        Return a bool if running.
        """
        self.poll()
        return self._data["building"]

    def block(self):
        while self.is_running():
            time.sleep(1)

    def is_good(self):
        """
        Return a bool, true if the build was good.
        If the build is still running, return False.
        """
        return (not self.is_running()) and self._data["result"] == STATUS_SUCCESS

    def block_until_complete(self, delay=15):
        assert isinstance(delay, int)
        count = 0
        while self.is_running():
            total_wait = delay * count
            log.info(msg="Waited %is for %s #%s to complete" % (total_wait, self.job.name, self.name))
            sleep(delay)
            count += 1

    def get_jenkins_obj(self):
        return self.job.get_jenkins_obj()

    def get_result_url(self):
        """
        Return the URL for the object which provides the job's result summary.
        """
        url_tpl = r"%stestReport/%s"
        return url_tpl % (self._data["url"], config.JENKINS_API)

    def get_resultset(self):
        """
        Obtain detailed results for this build.
        """
        if self.has_resultset():
            raise NoResults("%s does not have any published results" % str(self))
        buildstatus = self.get_status()
        if not self.get_actions()[self.STR_TOTALCOUNT]:
            raise NoResults(self.STR_TPL_NOTESTS_ERR % (str(self), buildstatus))
        result_url = self.get_result_url()
        return ResultSet(result_url, build=self)

    def has_resultset(self):
        """
        Return a boolean, true if a result set is available. false if not.
        """
        return self.STR_TOTALCOUNT in self.get_actions()

    def get_actions(self):
        all_actions = {}
        for dct_action in self._data["actions"]:
            if dct_action is None:
                continue
            all_actions.update(dct_action)
        return all_actions

    def get_timestamp(self):
        '''
        Returns build timestamp in UTC
        '''
        # Java timestamps are given in miliseconds since the epoch start!
        naive_timestamp = datetime.datetime(*time.gmtime(self._data['timestamp'] / 1000.0)[:6])
        return pytz.utc.localize(naive_timestamp)

    def get_console(self):
        """
        Return the current state of the text console.
        """
        url = "%s/consoleText" % self.baseurl
        return self.job.jenkins.requester.get_url(url).content

    def stop(self):
        """
        Stops the build execution if it's running
        :return boolean True if succeded False otherwise or the build is not running
        """
        if self.is_running():
            url = "%s/stop" % self.baseurl
            self.job.jenkins.requester.post_and_confirm_status(url, data='')
            return True
        return False
