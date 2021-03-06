# vim:tw=0:expandtab:autoindent:tabstop=4:shiftwidth=4:filetype=python:

  #############################################################################
  #
  # Copyright (c) 2005 Dell Computer Corporation
  # Dual Licenced under GNU GPL and OSL
  #
  #############################################################################
"""
package module
"""

import rpm
from gettext import gettext as _

from firmwaretools.trace_decorator import decorate, traceLog, getLog

class InternalError(Exception): pass
class InstallError(Exception): pass
class NoInstaller(Exception): pass

def defaultCompareStrategy(ver1, ver2):
    return rpm.labelCompare( ("0", str(ver1), "0"), ("0", str(ver2), "0"))

packageStatusEnum = {
    "unknown": _("The package status is not known."),
    "not_installed": _("The device has not been updated to this version."),
    "in_progress":   _("The device is being updated now"),
    "failed":        _("Device update failed."),
    "success":       _("Device update was successful."),
    "disabled":       _("Device update is disabled for this device."),
    "warm_reboot_needed":       _("Update complete. You must perform a warm reboot for the update to take effect."),
    }

# Package public API:
#   pkg.name
#   pkg.version
#   str(pkg) == display name
#   pkg.compareVersion(otherPkg)
class Package(object):
    def __init__(self, *args, **kargs):
        self.name = None
        self.version = None
        self.compareStrategy = defaultCompareStrategy
        for key, value in kargs.items():
            setattr(self, key, value)

        assert(hasattr(self, "name"))
        assert(hasattr(self, "version"))
        assert(hasattr(self, "displayname"))
        assert(len(self.name))
        assert(len(self.version))
        assert(len(self.displayname))

        status = "unknown"

    def __str__(self):
        if hasattr(self, "displayname"):
            return self.displayname
        return self.name

    def compareVersion(self, otherPackage):
        return self.compareStrategy(self.version, otherPackage.version)

class RepositoryPackage(Package):
    mainIni = None
    def __init__(self, *args, **kargs):
        self.installFunction = None
        self.path = None
        super(RepositoryPackage, self).__init__(*args, **kargs)

        self.capabilities = {
            # if package is capable of downgrading
            'can_downgrade': False,

            # if package is capable of reflashing same version
            'can_reflash': False,

            # if package has/updates .percent_done member var
            # GUI can use progress bar if this is set.
            # otherwise, GUI should just use a spinner or something
            'accurate_update_percentage': False,

            # if update has .update_status_text member var
            # GUI should use for 'view log' function
            'update_log_string': False,

            # if update has .update_status_logfile member var
            # GUI should use for 'view log' function
            'update_log_filename': False,
            }

        self.progressPct = 0
        self.status = "not_installed"
        self.deviceList = []
        self.currentInstallDevice = None

    def getProgress(self):
        # returns real number between 0-1, or -1 for "not supported"
        if self.capabilities['accurate_update_percentage']:
            return self.progressPct
        else:
            return -1

    def install(self):
        self.status = "in_progress"
        if self.installFunction is not None:
            return self.installFunction(self)

        self.status = "failed"
        raise NoInstaller(_("Attempt to install a package with no install function. Name: %s, Version: %s") % (self.name, self.version))

    def getCapability(self, capability):
        return self.capabilities.get(capability, None)

    def attachToDevice(self, device):
        self.deviceList.append(device)

    def getDeviceList(self):
        return self.deviceList

    def setCurrentInstallDevice(self, device):
        self.currentInstallDevice = device

    def getCurrentInstallDevice(self):
        return self.currentInstallDevice

    def getStatusStr(self):
        return packageStatusEnum.get(self.status, _("Programming error: status code not found."))


# Base class for all devices on a system
# required:
#   displayname
#   name
#   version
# optional:
#   compareStrategy
class Device(Package):
    def __init__(self, *args, **kargs):
        self.name = None
        self.version = None
        self.compareStrategy = defaultCompareStrategy
        for key, value in kargs.items():
            setattr(self, key, value)

        if not hasattr(self, "uniqueInstance"):
            self.uniqueInstance = self.name

        assert(hasattr(self, "name"))
        assert(hasattr(self, "version"))
        assert(hasattr(self, "displayname"))

        status = "unknown"

    def __str__(self):
        if hasattr(self, "displayname"):
            return self.displayname
        return self.name

    def compareVersion(self, otherPackage):
        return self.compareStrategy(self.version, otherPackage.version)


# required:  (in addition to base class)
#   pciDbdf
class PciDevice(Device):
    def __init__(self, *args, **kargs):
        super(Device, self).__init__(*args, **kargs)
        assert(hasattr(self, "pciDbdf"))
        self.uniqueInstance = "pci_dev_at_domain_0x%04x_bus_0x%02x_dev_0x%02x_func_0x%01x" % self.pciDbdf


