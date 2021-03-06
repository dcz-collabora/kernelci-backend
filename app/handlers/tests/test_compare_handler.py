# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Test module for the JobHandler handler."""

try:
    import simplejson as json
except ImportError:
    import json

import mock
import tornado

import urls

from handlers.tests.test_handler_base import TestHandlerBase


class TestCompareHandler(TestHandlerBase):

    def get_app(self):
        return tornado.web.Application(
            [urls._JOB_URL, urls._JOB_ID_URL], **self.settings)

    @mock.patch("utils.db.find")
    @mock.patch("utils.db.count")
    def test_get(self, mock_count, mock_find):
        mock_count.return_value = 0
        mock_find.return_value = []

        expected_body = (
            '{"count":0,"skip":0,"code":200,"limit":0,"result":[]}')

        headers = {"Authorization": "foo"}
        response = self.fetch("/job?date_range=5&job=job", headers=headers)

        self.assertEqual(response.code, 200)
        self.assertEqual(
            response.headers["Content-Type"], self.content_type)
        self.assertEqual(response.body, expected_body)

    @mock.patch("utils.db.find")
    @mock.patch("utils.db.count")
    def test_get_with_limit(self, mock_count, mock_find):
        mock_count.return_value = 0
        mock_find.return_value = []

        expected_body = (
            '{"count":0,"skip":0,"code":200,"limit":1024,"result":[]}')

        headers = {"Authorization": "foo"}
        response = self.fetch("/job?limit=1024", headers=headers)

        self.assertEqual(response.code, 200)
        self.assertEqual(
            response.headers["Content-Type"], self.content_type)
        self.assertEqual(response.body, expected_body)

    @mock.patch("bson.objectid.ObjectId")
    @mock.patch("handlers.job.JobHandler.collection")
    def test_get_by_id_not_found(self, collection, mock_id):
        mock_id.return_value = "job-kernel"
        collection.find_one = mock.MagicMock()
        collection.find_one.return_value = None

        headers = {"Authorization": "foo"}
        response = self.fetch("/job/job-kernel", headers=headers)

        self.assertEqual(response.code, 404)
        self.assertEqual(
            response.headers["Content-Type"], self.content_type)

    @mock.patch("bson.objectid.ObjectId")
    @mock.patch("handlers.job.JobHandler.collection")
    def test_get_by_id_not_found_empty_list(self, collection, mock_id):
        mock_id.return_value = "job-kernel"
        collection.find_one = mock.MagicMock()
        collection.find_one.return_value = []

        headers = {"Authorization": "foo"}
        response = self.fetch("/job/job-kernel", headers=headers)

        self.assertEqual(response.code, 404)
        self.assertEqual(
            response.headers["Content-Type"], self.content_type)

    @mock.patch("bson.objectid.ObjectId")
    @mock.patch("handlers.job.JobHandler.collection")
    def test_get_by_id_found(self, collection, mock_id):
        mock_id.return_value = "job-kernel"
        collection.find_one = mock.MagicMock()
        collection.find_one.return_value = {"_id": "foo"}

        expected_body = '{"code":200,"result":[{"_id":"foo"}]}'

        headers = {"Authorization": "foo"}
        response = self.fetch("/job/" + self.doc_id, headers=headers)

        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, expected_body)

    def test_post_without_token(self):
        body = json.dumps(dict(job="job", kernel="kernel"))

        response = self.fetch("/job", method="POST", body=body)

        self.assertEqual(response.code, 403)
        self.assertEqual(
            response.headers["Content-Type"], self.content_type)

    def test_post_not_json_content(self):
        headers = {"Authorization": "foo", "Content-Type": "application/json"}

        response = self.fetch(
            "/job", method="POST", body="", headers=headers)

        self.assertEqual(response.code, 422)
        self.assertEqual(
            response.headers["Content-Type"], self.content_type)

    def test_post_wrong_content_type(self):
        headers = {"Authorization": "foo"}

        response = self.fetch(
            "/job", method="POST", body="", headers=headers)

        self.assertEqual(response.code, 415)
        self.assertEqual(
            response.headers["Content-Type"], self.content_type)

    def test_post_wrong_json(self):
        headers = {"Authorization": "foo", "Content-Type": "application/json"}
        body = json.dumps(dict(foo="foo", bar="bar"))

        response = self.fetch(
            "/job", method="POST", body=body, headers=headers)

        self.assertEqual(response.code, 400)
        self.assertEqual(
            response.headers["Content-Type"], self.content_type)

    @mock.patch("taskqueue.tasks.build.create_build_logs_summary")
    @mock.patch("utils.db.find_and_update")
    def test_post_correct(self, mock_find, mock_task):
        mock_find.retur_value = 200
        mock_task.apply_async = mock.MagicMock()

        headers = {"Authorization": "foo", "Content-Type": "application/json"}
        body = json.dumps(dict(job="job", kernel="kernel"))

        response = self.fetch(
            "/job", method="POST", headers=headers, body=body)

        self.assertEqual(response.code, 200)
        self.assertEqual(
            response.headers["Content-Type"], self.content_type)

    def test_post_wrong_status(self):
        headers = {"Authorization": "foo", "Content-Type": "application/json"}
        body = json.dumps(dict(job="job", kernel="kernel", status="foo"))

        response = self.fetch(
            "/job", method="POST", headers=headers, body=body)

        self.assertEqual(response.code, 400)
        self.assertEqual(
            response.headers["Content-Type"], self.content_type)

    @mock.patch("utils.db.find_and_update")
    def test_post_internal_error(self, mock_find):
        mock_find.return_value = 500
        headers = {"Authorization": "foo", "Content-Type": "application/json"}
        body = json.dumps(dict(job="job", kernel="kernel", status="FAIL"))

        response = self.fetch(
            "/job", method="POST", headers=headers, body=body)

        self.assertEqual(response.code, 500)
        self.assertEqual(
            response.headers["Content-Type"], self.content_type)

    @mock.patch("utils.db.find_and_update")
    def test_post_not_found(self, mock_find):
        mock_find.return_value = 404
        headers = {"Authorization": "foo", "Content-Type": "application/json"}
        body = json.dumps(dict(job="job", kernel="kernel", status="FAIL"))

        response = self.fetch(
            "/job", method="POST", headers=headers, body=body)

        self.assertEqual(response.code, 404)
        self.assertEqual(
            response.headers["Content-Type"], self.content_type)

    def test_delete_no_token(self):
        response = self.fetch("/job/" + self.doc_id, method="DELETE")
        self.assertEqual(response.code, 403)

    @mock.patch("bson.objectid.ObjectId")
    def test_delete_with_token_no_job(self, mock_id):
        mock_id.return_value = "job"
        headers = {"Authorization": "foo"}

        response = self.fetch(
            "/job/job", method="DELETE", headers=headers)

        self.assertEqual(response.code, 404)
        self.assertEqual(
            response.headers["Content-Type"], self.content_type)

    @mock.patch("bson.objectid.ObjectId")
    def test_delete_with_token_with_job(self, mock_id):
        mock_id.return_value = "job"
        self.database["job"].insert(
            dict(_id="job", job="job", kernel="kernel"))
        headers = {"Authorization": "foo"}

        response = self.fetch(
            "/job/" + self.doc_id, method="DELETE", headers=headers)

        self.assertEqual(response.code, 200)
        self.assertEqual(
            response.headers["Content-Type"], self.content_type)

    def test_delete_no_id(self):
        headers = {"Authorization": "foo"}

        response = self.fetch(
            "/job", method="DELETE", headers=headers)

        self.assertEqual(response.code, 400)
        self.assertEqual(
            response.headers["Content-Type"], self.content_type)

    def test_delete_wrong_id(self):
        headers = {"Authorization": "foo"}

        response = self.fetch(
            "/job/abcdefghilmnopqrstuvwxyz", method="DELETE", headers=headers)

        self.assertEqual(response.code, 400)
        self.assertEqual(
            response.headers["Content-Type"], self.content_type)

    @mock.patch("utils.db.delete")
    @mock.patch("utils.db.find_one2")
    @mock.patch("bson.objectid.ObjectId")
    def test_delete_db_error(self, mock_id, mock_find, mock_delete):
        mock_id.return_value = "job"
        mock_find.return_value = "job"
        mock_delete.return_value = 500
        headers = {"Authorization": "foo"}

        response = self.fetch(
            "/job/" + self.doc_id, method="DELETE", headers=headers)

        self.assertEqual(response.code, 500)
        self.assertEqual(
            response.headers["Content-Type"], self.content_type)

    @mock.patch("handlers.base.BaseHandler._get_one")
    def test_get_wrong_handler_response(self, mock_get_one):
        mock_get_one.return_value = ""
        headers = {"Authorization": "foo"}

        response = self.fetch("/job/" + self.doc_id, headers=headers)

        self.assertEqual(response.code, 506)
        self.assertEqual(
            response.headers["Content-Type"], self.content_type)


class TestJobDistinctHandler(TestHandlerBase):

    def get_app(self):
        return tornado.web.Application(
            [urls._JOB_DISTINCT_URL], **self.settings)

    def test_delete(self):
        headers = {"Authorization": "foo"}

        response = self.fetch(
            "/job/distinct/foo", method="DELETE", headers=headers)

        self.assertEqual(response.code, 501)
        self.assertEqual(
            response.headers["Content-Type"], self.content_type)

    def test_post(self):
        headers = {"Authorization": "foo", "Content-Type": "application/json"}

        response = self.fetch(
            "/job/distinct/foo", method="POST", headers=headers, body="body")

        self.assertEqual(response.code, 501)
        self.assertEqual(
            response.headers["Content-Type"], self.content_type)

    def test_put(self):
        headers = {"Authorization": "foo", "Content-Type": "application/json"}

        response = self.fetch(
            "/job/distinct/foo", method="PUT", headers=headers, body="body")

        self.assertEqual(response.code, 501)
        self.assertEqual(
            response.headers["Content-Type"], self.content_type)

    def test_get_no_auth(self):
        response = self.fetch("/job/distinct/foo", method="GET")

        self.assertEqual(response.code, 403)
        self.assertEqual(
            response.headers["Content-Type"], self.content_type)

    def test_get_no_field(self):
        headers = {"Authorization": "foo"}
        response = self.fetch(
            "/job/distinct/", headers=headers, method="GET")

        self.assertEqual(response.code, 404)
        self.assertEqual(
            response.headers["Content-Type"], self.content_type)

    def test_get_wrong_field(self):
        headers = {"Authorization": "foo"}
        response = self.fetch(
            "/job/distinct/foo", headers=headers, method="GET")

        self.assertEqual(response.code, 400)
        self.assertEqual(
            response.headers["Content-Type"], self.content_type)

    def test_get_correct(self):
        headers = {"Authorization": "foo"}
        response = self.fetch(
            "/job/distinct/job", headers=headers, method="GET")

        self.assertEqual(response.code, 200)
        self.assertEqual(
            response.headers["Content-Type"], self.content_type)

    def test_get_correct_with_query(self):
        headers = {"Authorization": "foo"}
        response = self.fetch(
            "/job/distinct/kernel?job=mainline", headers=headers, method="GET")

        self.assertEqual(response.code, 200)
        self.assertEqual(
            response.headers["Content-Type"], self.content_type)
