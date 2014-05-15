# Copyright (C) 2014 Linaro Ltd.
#
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

# The default mongodb database name.
DB_NAME = 'kernel-ci'

# The default ID key for mongodb documents.
ID_KEY = '_id'

# Job and/or build status.
BUILD_STATUS = 'BUILD'
FAIL_STATUS = 'FAIL'
PASS_STATUS = 'PASS'
UNKNOWN_STATUS = 'UNKNOWN'

# Build file names.
DONE_FILE = '.done'
BUILD_META_FILE = 'build.meta'
BUILD_FAIL_FILE = 'build.FAIL'
BUILD_PASS_FILE = 'build.PASS'
