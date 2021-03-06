# -*- coding: utf-8 -*-
#
# Copyright (C) 2018-2020 CERN.
#
# invenio-app-ils is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Test ILS APIs."""

from invenio_accounts.models import User
from tests.helpers import get_test_record

from invenio_app_ils.documents.api import Document
from invenio_app_ils.patrons.api import patron_exists
from invenio_app_ils.proxies import current_app_ils
from invenio_app_ils.records.api import IlsRecord
from invenio_app_ils.series.api import Series


def test_apis(testdata):
    """Test various APIs."""

    def test_patron_exists():
        """Test return True if item exists."""
        test_patron = User.query.all()[0]
        assert patron_exists(test_patron.id)
        assert not patron_exists("not-existing-patron-pid")

    def test_get_record_by_pid():
        """Test get_record_by_pid."""
        tests = [("docid-1", Document), ("serid-1", Series)]

        for pid, cls in tests:
            record = cls.get_record_by_pid(pid)

            assert isinstance(record, cls)
            assert record["pid"] == pid
            assert record._pid_type == cls._pid_type

    def test_get_record_by_pid_and_pid_type():
        """Test get_record_by_pid with pid_type."""
        tests = [("docid-1", "docid", Document), ("serid-1", "serid", Series)]

        for pid, pid_type, expected_cls in tests:
            record = IlsRecord.get_record_by_pid(pid, pid_type=pid_type)

            assert isinstance(record, expected_cls)
            assert record["pid"] == pid
            assert record._pid_type == pid_type

    def test_get_default_location_pid():
        """Asset that the default location is the first created."""
        first = get_test_record(testdata, "locations", "locid-1")
        pid_value, _ = current_app_ils.get_default_location_pid
        assert pid_value == first["pid"]

    test_patron_exists()
    test_get_record_by_pid()
    test_get_record_by_pid_and_pid_type()
    test_get_default_location_pid()
