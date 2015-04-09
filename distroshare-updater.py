#!/usr/bin/env python2.7

from parsers import DUConfigParser, DUManifestParser, DUReleaseParser
from updates import GitRepos
import subprocess, sys
import ConfigParser

def run_command(command):
    try:
        subprocess.check_output(command,
                                stderr=subprocess.STDOUT, shell=False)
    except subprocess.CalledProcessError as e:
        sys.stderr.write("Error running command: " + command[0] + "\n")

def update_release_version(base_version, machine_version):
    release_file = open("/etc/distroshare_release", 'w')
    release_file.truncate()
    release_file.write("base_version=" + base_version + "\n")
    release_file.write("machine_version=" + machine_version + "\n")
    release_file.close()

def main():
    try:
        config = DUConfigParser()
    except IOError:
        print "Error opening configuration file: /etc/default/distroshare-updater"
        sys.exit(1)
    except ConfigParser.NoOptionError:
        print "Incomplete config file: /etc/default/distroshare-updater"
        sys.exit(1)

    repos = GitRepos(config)
    repos.update_repos()
    manifest_base = DUManifestParser(config.get_git_common_dir())
    manifest_machine = DUManifestParser(config.get_git_machine_dir())
    release = DUReleaseParser()

    if manifest_base.get_version() == release.get_base_version() \
       and manifest_machine.get_version() == release.get_machine_version():
        print "Already at the latest version"
        sys.exit(0)

    #run rsync to copy the files to the proper locations
    print "Rsyncing common config files"
    run_command(["rsync","-a", config.get_git_common_dir() + "/files/", "/"])
    print "Rsyncing machine specific config files"
    run_command(["rsync","-a", config.get_git_machine_dir() + "/files/", "/"])

    #update package lists
    print "Running apt-get update"
    run_command(["apt-get", "-qq", "update"])

    print "Installing packages and putting packages on hold"
    for manifest in [manifest_base, manifest_machine]:
        #install packages
        for name in manifest.get_packages_to_install():
            run_command(["apt-get", "-qq", "install", name])

        #put packages on hold
        for name in manifest.get_packages_to_hold():
            run_command(["apt-mark", "hold", name])

    #running grub-update
    print "Updating Grub"
    run_command(["update-grub"])

    #running update-initramfs
    print "Updating Initramfs"
    run_command(["update-initramfs", "-k", "all", "-u"])

    #updating the release version
    print "Updating the version number in /etc/distroshare_release"
    update_release_version(manifest_base.get_version(), 
                           manifest_machine.get_version())


if __name__ == "__main__": main()
