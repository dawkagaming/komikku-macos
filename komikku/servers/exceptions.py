# SPDX-FileCopyrightText: 2019-2025 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from gettext import gettext as _


class ServerException(Exception):
    def __init__(self, message):
        self.message = _('Error: {}').format(message)
        super().__init__(self.message)


class ArchiveError(ServerException):
    def __init__(self):
        super().__init__(_('Local archive is corrupt.'))


class ArchiveUnrarMissingError(ServerException):
    def __init__(self):
        super().__init__(_("Unable to extract page. Maybe the 'unrar' tool is missing?"))


class ChallengerError(ServerException):
    def __init__(self):
        super().__init__(_('Failed to complete browser challenge. Please try again.'))


class NotFoundError(ServerException):
    def __init__(self):
        super().__init__(_('No longer exists.'))
