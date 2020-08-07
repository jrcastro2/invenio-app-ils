# -*- coding: utf-8 -*-
#
# Copyright (C) 2020 CERN.
#
# invenio-app-ils is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""ILS Patrons APIs."""

from functools import partial

from flask import current_app
from invenio_accounts.models import User
from invenio_pidstore.models import PIDStatus
from invenio_pidstore.providers.recordid_v2 import RecordIdProviderV2
from invenio_userprofiles.api import UserProfile

from invenio_app_ils.errors import PatronNotFoundError
from invenio_app_ils.fetchers import pid_fetcher
from invenio_app_ils.proxies import current_app_ils

PATRON_PID_TYPE = "patid"
PATRON_PID_MINTER = "patid"
PATRON_PID_FETCHER = "patid"

PatronIdProvider = type(
    "PatronIdProvider",
    (RecordIdProviderV2,),
    dict(pid_type=PATRON_PID_TYPE, default_status=PIDStatus.REGISTERED),
)
patron_pid_minter = None
patron_pid_fetcher = partial(
    pid_fetcher, provider_cls=PatronIdProvider, pid_field="id"
)


class Patron(dict):
    """Patron record class."""

    _index = "patrons-patron-v1.0.0"
    _doc_type = "patron-v1.0.0"
    # Fake schema used to identify pid type from ES hit
    _schema = "patrons/patron-v1.0.0.json"

    def __init__(self, id, revision_id=None):
        """Create a `Patron` instance.

        Patron instances are not stored in the database
        but are indexed in ElasticSearch.
        """
        _id = int(id)  # internally it is an int
        _datastore = current_app.extensions["security"].datastore
        # if not _id throw PatronNotFoundError(_id)
        user = _datastore.get_user(_id)
        if not user:
            raise PatronNotFoundError(_id)

        self._user = user
        self.id = self._user.id
        # set revision as it is needed by the indexer but always to the same
        # value as we don't need it
        self.revision_id = 1
        self._profile = UserProfile.get_by_userid(id)
        self.name = self._profile.full_name if self._profile else ""
        self.email = self._user.email

        # currently no support for patrons affiliated to different
        # locations, return only the default location
        pid_value, _ = current_app_ils.get_default_location_pid
        self.location_pid = pid_value

        # add all fields to the dict so they can be accessed as a dict too
        super().__init__(self.dumps())

    def dumps(self):
        """Return python representation of Patron metadata."""
        return {
            "$schema": self._schema,
            "id": str(self.id),  # expose it as a string
            "pid": str(self.id),
            "name": self.name,
            "email": self.email,
            "location_pid": self.location_pid,
        }

    def dumps_loader(self, **kwargs):
        """Return a simpler patron representation for loaders."""
        return {
            "id": str(self.id),
            "pid": str(self.id),
            "name": self.name,
            "email": self.email,
            "location_pid": self.location_pid,
        }

    @staticmethod
    def get_patron(patron_pid):
        """Return the patron object given the patron_pid."""
        if not patron_pid:
            raise PatronNotFoundError(patron_pid)

        if str(patron_pid) == str(SystemAgent.id):
            return SystemAgent()

        return Patron(patron_pid)


class SystemAgent(Patron):
    """Fake patron for storing changes performed by the system."""

    id = -1

    def __init__(self):
        """Constructor."""
        self._schema = ""
        self.name = "System"
        self.email = current_app.config["SUPPORT_EMAIL"]
        self.location_pid = ""


def patron_exists(patron_pid):
    """Return True if the Patron exists given a PID."""
    return User.query.filter_by(id=patron_pid).first() is not None


def get_anonymous_patron_dict(patron_pid):
    """Return dict with Unknown values for patron."""
    return {
        "id": "anonymous",
        "pid": patron_pid,
        "name": "anonymous",
        "email": "anonymous",
        "location_pid": "anonymous",
    }


def get_patron_or_unknown(patron_pid):
    """Resolve a Patron for a given field."""
    if not patron_pid:
        raise PatronNotFoundError
    try:
        cls = current_app_ils.patron_cls
        return cls.get_patron(patron_pid).dumps_loader()
    except PatronNotFoundError:
        return get_anonymous_patron_dict(patron_pid)
