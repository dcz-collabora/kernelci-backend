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

"""The RequestHandler for /test/suite URLs."""

try:
    import simplejson as json
except ImportError:
    import json

import bson
import datetime
import types

import handlers.base as hbase
import handlers.common as hcommon
import handlers.response as hresponse
import models
import models.test_suite as mtsuite
import utils.db
import utils.validator as validator


# pylint: disable=too-many-public-methods
class TestSuiteHandler(hbase.BaseHandler):
    """The test suite request handler."""

    def __init__(self, application, request, **kwargs):
        super(TestSuiteHandler, self).__init__(application, request, **kwargs)

    @property
    def collection(self):
        return models.TEST_SUITE_COLLECTION

    @staticmethod
    def _valid_keys(method):
        return hcommon.TEST_SUITE_VALID_KEYS.get(method, None)

    @staticmethod
    def _token_validation_func():
        return hcommon.valid_token_tests

    def _post(self, *args, **kwargs):
        response = hresponse.HandlerResponse()
        suite_id = kwargs.get("id", None)

        if suite_id:
            response.status_code = 400
            response.reason = "To update a test suite, use a PUT request"
        else:
            test_suite_json = kwargs.get("json_obj", None)
            suite_pop = test_suite_json.pop
            test_set = suite_pop(models.TEST_SET_KEY, [])
            test_case = suite_pop(models.TEST_CASE_KEY, [])

            test_suite = mtsuite.TestSuiteDocument.from_json(test_suite_json)
            test_suite.created_on = datetime.datetime.now(tz=bson.tz_util.utc)

            ret_val, doc_id = utils.db.save(self.db, test_suite)

            if ret_val == 201:
                response.status_code = ret_val
                response.reason = (
                    "Test suite '%s' created with ID: %s" %
                    (test_suite.name, doc_id))

                if all([test_set, isinstance(test_set, types.ListType)]):
                    response.status_code = 202
                    response.messages = (
                        "Associated test sets will be parsed and imported")
                    # TODO: import async the test sets.

                if all([test_case, isinstance(test_case, types.ListType)]):
                    response.status_code = 202
                    response.messages = (
                        "Associated test cases will be parsed and imported")
                    # TODO: import async the test cases.
            else:
                response.status_code = 500
                response.reason = (
                    "Error saving test set '%s'" % test_suite.name)

        return response

    def execute_put(self, *args, **kwargs):
        """Execute the PUT pre-operations."""
        response = None

        if self.validate_req_token("PUT"):
            if kwargs and kwargs.get("id", None):
                valid_request = self._valid_post_request()

                if valid_request == 200:
                    try:
                        json_obj = json.loads(self.request.body.decode("utf8"))

                        valid_json, j_reason = validator.is_valid_json(
                            json_obj, self._valid_keys("PUT")
                        )
                        if valid_json:
                            kwargs["json_obj"] = json_obj
                            kwargs["db_options"] = self.settings["dboptions"]
                            kwargs["reason"] = j_reason
                            response = self._put(*args, **kwargs)
                        else:
                            response = hresponse.HandlerResponse(400)
                            if j_reason:
                                response.reason = (
                                    "Provided JSON is not valid: %s" % j_reason
                                )
                            else:
                                response.reason = "Provided JSON is not valid"
                            response.result = None
                    except ValueError, ex:
                        self.log.exception(ex)
                        error = "No JSON data found in the PUT request"
                        self.log.error(error)
                        response = hresponse.HandlerResponse(422)
                        response.reason = error
                        response.result = None
                else:
                    response = hresponse.HandlerResponse(valid_request)
                    response.reason = (
                        "%s: %s" %
                        (
                            self._get_status_message(valid_request),
                            "Use %s as the content type" % self.content_type
                        )
                    )
                    response.result = None
            else:
                response = hresponse.HandlerResponse(400)
                response.reason = "No ID specified"
        else:
            response = hresponse.HandlerResponse(403)
            response.reason = hcommon.NOT_VALID_TOKEN

        return response

    def _put(self, *args, **kwargs):
        response = hresponse.HandlerResponse()
        update_doc = kwargs.get("json_obj")
        doc_id = kwargs.get("id")

        try:
            suite_id = bson.objectid.ObjectId(doc_id)
            if utils.db.find_one2(self.collection, suite_id):
                update_val = utils.db.update(
                    self.collection, suite_id, update_doc)

                if update_val == 200:
                    response.reason = "Resource '%s' updated" % doc_id
                else:
                    response.status_code = update_val
                    response.reason = "Error updating resource '%s'" % doc_id
            else:
                response.status_code = 404
                response.reason = self._get_status_message(404)
        except bson.errors.InvalidId, ex:
            self.log.exception(ex)
            self.log.error("Invalid ID specified: %s", doc_id)
            response.status_code = 400
            response.reason = "Wrong ID specified"
        return response

    def _delete(self, doc_id):
        response = hresponse.HandlerResponse()
        response.result = None

        try:
            suite_id = bson.objectid.ObjectId(doc_id)
            if utils.db.find_one2(self.collection, suite_id):
                response.status_code = utils.db.delete(
                    self.collection, suite_id)

                if response.status_code == 200:
                    response.reason = "Resource '%s' deleted" % doc_id

                    test_set_canc = utils.db.delete(
                        self.db[models.TEST_SET_COLLECTION],
                        {models.TEST_SUITE_ID_KEY: {"$in": [suite_id]}}
                    )

                    test_case_canc = utils.db.delete(
                        self.db[models.TEST_CASE_COLLECTION],
                        {models.TEST_SUITE_ID_KEY: {"$in": [suite_id]}}
                    )

                    if test_case_canc != 200:
                        response.errors = (
                            "Error deleting test cases with "
                            "test_suite_id '%s'" %
                            doc_id
                        )
                    if test_set_canc != 200:
                        response.errors = (
                            "Error deleting test sets with "
                            "test_suite_id '%s'" %
                            doc_id
                        )
                else:
                    response.reason = "Error deleting resource '%s'" % doc_id
            else:
                response.status_code = 404
                response.reason = self._get_status_message(404)
        except bson.errors.InvalidId, ex:
            self.log.exception(ex)
            self.log.error("Invalid ID specified: %s", doc_id)
            response.status_code = 400
            response.reason = "Wrong ID specified"

        return response