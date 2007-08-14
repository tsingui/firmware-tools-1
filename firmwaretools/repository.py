# vim:expandtab:autoindent:tabstop=4:shiftwidth=4:filetype=python:tw=0

  #############################################################################
  #
  # Copyright (c) 2005 Dell Computer Corporation
  # Dual Licenced under GNU GPL and OSL
  #
  #############################################################################
"""
repository module
"""

from __future__ import generators

import os
import ConfigParser

import package
import pycompat
import dep_parser
import sys
import traceback
from trace_decorator import trace, dprint, decorateAllFunctions

class CircularDependencyError(Exception): pass

def makePackage(configFile):
    conf = ConfigParser.ConfigParser()
    conf.read(configFile)

    # make a standard package
    p = package.RepositoryPackage( 
        name=conf.get("package", "name"),
        version=conf.get("package", "version"),
        conf=conf, 
        path=os.path.dirname(configFile), 
        )

    try:
        pymod = conf.get("package","module")
        dprint("pymod: %s\n" % pymod)
        module = __import__(pymod, globals(),  locals(), [])
        for i in pymod.split(".")[1:]:
            module = getattr(module, i)

        packageTypeClass = conf.get("package", "type")
        type = getattr(module, packageTypeClass)
        if issubclass(type, package.Package):
            dprint("direct instantiate\n")
            # direct instantiate class (new style)
            p = type(
                name=conf.get("package", "name"),
                version=conf.get("package", "version"),
                conf=conf,
                path=os.path.dirname(configFile),
            )
        else:
            # just wrap it (old style)
            dprint("wrap\n")
            type(p)
    except (ConfigParser.NoOptionError, ConfigParser.NoSectionError, ImportError, AttributeError):
        dprint(traceback.format_exc())
        pass

    return p

# a null function that just eats args. Default callback
def nullFunc(*args, **kargs): pass

def generateInstallationOrder(packagesToUpdate, cb=(nullFunc, None)):
    # generate initial union inventory
    # we will start with no update packages and add them in one at a time
    # as we install them
    unionInventory = {}  # { 'pkgName': pkg, ... }
    for pkgName, details in packagesToUpdate.items():
        unionInventory[pkgName] = details["device"]
        
    updatePackageList = [] # [ pkg, pkg, pkg ]
    for pkgName, details in packagesToUpdate.items():
        if details["update"]:
            updatePackageList.append(details["update"])

    workToDo = 1
    while workToDo:
        workToDo = 0
        for candidate in updatePackageList:
            if checkRules(packagesToUpdate, candidate, unionInventory, cb=cb):
                yield candidate

                # move pkg from to-install list to inventory list
                updatePackageList.remove(candidate)
                unionInventory[candidate.name] = candidate

                # need another run-through in case this fixes deps for another package
                workToDo = 1

    if len(updatePackageList):
        raise CircularDependencyError("packages have circular dependency, or are otherwise uninstallable.")

# suppose we do this the slow way for now, then get somebody smarter to help later
def generateUpdateSet(repo, systemInventory, cb=(nullFunc, None)):
    packagesToUpdate = {}
    for device in systemInventory:
        packagesToUpdate[device.name] = { "device": device, "update": None, "available_updates": []}

    # generate union inventory. Union inventory is used by the rules processing engine.
    unionInventory = {}
    for pkgName, details in packagesToUpdate.items():
        unionInventory[pkgName] = details["device"]

    # for every device on system, attach a list of available updates for that device.
    for candidate in repo.iterPackages(cb=cb):
        if packagesToUpdate.has_key(candidate.name):
            available_updates = packagesToUpdate[candidate.name]['available_updates']
            available_updates.append(candidate)
            packagesToUpdate[candidate.name]['available_updates'] = available_updates

    # for every device, look at the available updates to see if one can be applied.
    # if we do any work, start over so that dependencies work themselves out over multiple iterations.
    workToDo = 1
    while workToDo:
        workToDo = 0
        for pkgName, details in packagesToUpdate.items():
            for candidate in details['available_updates']:
                if checkRules(packagesToUpdate, candidate, unionInventory, cb=cb):
                    packagesToUpdate[candidate.name]["update"] = candidate
                    # update union inventory
                    unionInventory[candidate.name] = candidate
                    # need another run-through in case this fixes deps for another package
                    workToDo = 1

    return packagesToUpdate


def checkRules(packagesToUpdate, candidate, unionInventory, cb=(nullFunc, None)):
    # check if candidate update even applies to this system
    if not packagesToUpdate.get(candidate.name):
        cb[0]( who="checkRules", what="package_not_present_on_system", package=candidate, cb=cb)
        return 0
        
    # is candidate newer than what is either installed or scheduled for install
    if unionInventory[candidate.name].compareVersion(candidate) >= 0:
        cb[0]( who="checkRules", what="package_not_newer", package=candidate, systemPackage=unionInventory[candidate.name], cb=cb)
        return 0

    #check to see if this package has specific system requirements
    # for now, check if we are on a specific system by checking for
    # a BIOS package w/ matching id. In future, may have specific 
    # system package.
    if candidate.conf.has_option("package", "limit_system_support"):
        systemVenDev = candidate.conf.get("package", "limit_system_support")
        if not unionInventory.get( "system_bios(%s)" % systemVenDev ):
            cb[0]( who="checkRules", what="fail_limit_system_check", package=candidate, cb=cb )
            return 0

    #check generic dependencies
    if candidate.conf.has_option("package", "requires"):
        requires = candidate.conf.get("package", "requires")
        if len(requires):
            d = dep_parser.DepParser(requires, unionInventory, packagesToUpdate)
            if not d.depPass:
                cb[0]( who="checkRules", what="fail_dependency_check", package=candidate, reason=d.reason, cb=cb )
                return 0
    return 1


class Repository(object):
    def __init__(self, *args):
        self.dirList = []
        for i in args:
            self.dirList.append(i)

    def iterPackages(self, cb=(nullFunc, None)):
        for dir in self.dirList:
            try:
                for (path, dirs, files) in pycompat.walkPath(dir):
                    if "package.ini" in files:
                        cb[0]( who="iterPackages", what="found_package_ini", path=os.path.join(path, "package.ini" ), cb=cb)
                        try:
                            p = makePackage( os.path.join(path, "package.ini" ))
                            cb[0]( who="iterPackages", what="made_package", package=p, cb=cb)
                            yield p
                        except:
                            dprint(traceback.format_exc())
                            pass
            except OSError:   # directory doesnt exist, so no repo packages. :-)
                pass

    iterPackages = trace(iterPackages)

    def iterLatestPackages(self, cb=(nullFunc, None)):
        latest = {}
        for candidate in self.iterPackages(cb=cb):
            pkgName = candidate.name
            if candidate.conf.has_option("package", "limit_system_support"):
                pkgName = pkgName + "_" + candidate.conf.get("package", "limit_system_support")

            p = latest.get(pkgName)
            if not p:
                latest[pkgName] = candidate
            elif p.compareVersion(candidate) < 0:
                latest[pkgName] = candidate

        cb[0]( who="iterLatestPackages", what="done_generating_list", cb=cb)
        keys = latest.keys()
        keys.sort()
        for package in keys:
            cb[0]( who="iterLatestPackages", what="made_package", package=latest[package], cb=cb)
            yield latest[package]

    iterLatestPackages = trace(iterLatestPackages)

decorateAllFunctions(sys.modules[__name__])
