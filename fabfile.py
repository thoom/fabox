'''
Fabric file based on Dropbox VCS
--------------------------------

This script is based on using fabric for deployment on the same server as the Dropbox is on. Here are 
the assumptions:
/home/user
  - fabfily.py
  - Dropbox
    - web (maps to /var/www when deployed to production)
    - tag (where the tag.gz files are)
/var/www (where your web files reside)

'''
from fabric.api import *
from operator import itemgetter

import datetime
import os
import os.path
import re
import tarfile

'''
  Define environment object properties
'''
env.deploy_base = '/var/www'
env.deploy_to = None

env.environment = None
env.repository = {
    'command': 'cp -R',
    'tag_url': 'Dropbox/tag',
    'trunk_url': 'Dropbox/web',
    'env_url': 'Dropbox/env'
}

env.user = 'www-data'
env.group = 'www-data'

'''
  Set up environment deployment values
'''

def prod():
    _exit_no_product()
    env.environment = "production"

'''
  Command-line functions available
'''
# Deploys a bundle for a particular environment
def deploy(bundle=None):
    _exit_no_env() 

    tag = bundle
    selected = None
    build = None
    buildlist = _get_previous_builds(tag)
    while selected == None:
        #print "build = %s, buildlist = %i" % (build, len(buildlist))
        if build != None:
            _exit_request(build)

            try:
                build = int(build)
                if build <= len(buildlist):
                    selected = buildlist[build - 1]['tag']
                    confirm = prompt("Deploy bundle '%s'? (y/N)" % selected)

                    if confirm != "y":
                        selected = None
                        build = None
            except ValueError:
                for b in buildlist:
                    if build == b['tag']:
                        selected = build
        if selected:
            break

        print "Available Bundles are:"
        i = 1
        for b in buildlist:
            print "\t %i. %s  Bundles: %s" % (i, b['tag'], b['build'])
            i += 1
        build = prompt("Which bundles do you want to deploy? ")

    builds = _get_previous_builds(selected)
    b = builds.pop()
    print "I will deploy bundle: %s " % b['filename']

    # Future... add apache config deployment
    _deploy(b)

# Displays help information, duh ;)
def help():
    _exit_complete("""
Fabox (Dropbox VCS + Fabric)
----------------------------------------------------------------

This script eases the deployment process for web projects. It utilizes the Dropbox repository
by creating tags and bundling code into discreet chunks that can be deployed across staging and
production servers.

By accessing this help system, you are already partially there! The command-line code uses the following
format: fab {request}:{parameters}

For instance, 

  fab tag:tagName=110528

tells the deploy script to create a 110528 tag in the Dropbox tag directory. Described below is more 
information about the options available in the deployment process. Note that if parameters are not passed, 
the script will prompt the user to enter parameters when needed. The user can also abort the script at any 
of the prompts by typing "exit".

For certain requests, the environment should also be passed. Requests with an * denote that the environment is 
required. Note that this version does not include any environment checking and assumes a production environment.

Supported requests and their parameters:
  build:tag
    - Will use the tag provided to build a tarball. A build is required for deployment, and is part of the tagging process.

  *deploy:bundle
    - Will deploy the tagged tarball to the requested environment.
  
  *prev_version
    - Print a list of all of the previous version bundles in a particular environment
  
  *rollback:project
    - Rollback the project to the previous bundle.

  tag:tagName
    - Create a tagname for the product.

  *version
    - Print a list of all of the bundled version in a particular environment
  """)

# Displays a list of all previous version bundles for a requested environment
def prev_version():
    _exit_no_env()
    env.warn_only = True
    local('find %(d)s -maxdepth 2 -wholename \'*_previous/version.txt\' -print0 | xargs -0 more | grep "Tag" | sort' % {
        'd': env.deploy_base}, True)

# Reverts a bundle to its previous version for the requested environment
def rollback(project=None):
    """Build deployable package of code"""
    _exit_no_env()
    tag = project
    selected = None
    taglist = _get_products()
    while selected == None:
        _exit_request(tag)
        if tag in taglist:
            selected = tag
            break

        print "Available Products are:"
        for t in taglist:
            print "\t %s" % t
        tag = prompt("Which project do you want to rollback? ")

    _rollback(tag)

# Generates a tag for a requested product
def tag(tagName=None, project=None, build=True):
    #_exit_no_product()
    tag = project
    
    if env.deploy_to == None:
        selected = None
        product = None
        productlist = _get_products()

        while selected == None:
            if product != None:
                _exit_request(product)
                if product not in productlist:
                    product = None
            if product != None:
                selected = product
                break
            print "Available products are:"
            for p in productlist:
                print "\t %s" % p
            
            product = prompt("Which product do you want to tag?")
        
        _deploy_to(product)
        
    if tagName == None:
        tempTagName = ""
        default = None
        defaultTagName = datetime.datetime.today().strftime("%y%m%d")

    while tagName == None:
        if default == None:
            default = prompt("Do you want to use default tag '%s'? (y/N)" % defaultTagName)
        elif default == "Y" or default == "y":
            tagName = defaultTagName
            break
        else:
            _exit_request(default)   
            if tempTagName != "":
                tagName = tempTagName
                break
            tempTagName = prompt("Name the tag you want to create: ")

    _exit_request(tagName)

    _export(product, tagName)
    _exit_complete()

# Displays a list of all bundle version for the requested environment
def version():
    _exit_no_env()
    env.warn_only = True
    local(
        'find %(d)s -maxdepth 2 -name \'*_previous\' -prune -o -name \'*_rollback\' -prune -o -name \'version.txt\' -print0 | xargs -0 more | grep "Tag" | sort' % {
            'd': env.deploy_base}, True)

'''
  Private functions shared by various scripts
'''
# Uploads bundle to the environments hosts, moving the current bundle to previous status
def _deploy(build):
    env.warn_only = True
    tag = build['tag'].split('_')[0]
    _deploy_to(tag)
    local('sudo cp %(t)s/%(f)s %(b)s' % {'t': env.repository['tag_url'], 'f': build['filename'], 'b': env.deploy_base })
    with lcd('%(d)s' % {'d': env.deploy_base }):
        local('sudo tar xfj %(f)s' % {'f': build['filename']})
        local('sudo rm -rf %(f)s_previous/' % {'f': tag})
        local('sudo mv %(f)s/ %(f)s_previous/' % {'f': tag})
        local('sudo mv new %(f)s' % {'f': tag})
        local('sudo rm -f %(f)s' % {'f': build['filename']})  
    
        local('sudo chown -R %(u)s.%(g)s %(f)s' % {'u': env.user, 'g': env.group, 'f': tag})
        local('sudo chmod -R 775 %(f)s' % {'f': tag})
    
    _exit_complete()


def _deploy_to(product):
    env.deploy_to = '%(b)s/%(p)s' % {'b': env.deploy_base, 'p': product}

def _exit_complete(msg="\nCompleted request.\n"):
    exit(msg)

# Validates that the environment has been set
def _exit_no_env():
    if _exit_no_product() and env.environment != None:
        return

    avail = "prod"

    exit('''
Environment is missing.
Available environments:
  %s

See "fab help" for more information.
  ''' % avail)

# Validates that the product has been set
def _exit_no_product():
    return True #Short circuited since products are not separate with my simplified rollout
    if env.deploy_to != None:
        return True

    exit('''
Product is missing.
Available products:
  perch
  uatu
  
See "fab help" for more information.
  ''')

# Checks the variable value and exits if appropriate
def _exit_request(var):
    if var == 'exit':
        exit('\nExiting application as requested\n');


# Builds a bundle from the tag in the SVN repo
def _export(product, tagName):
    tag = '%(p)s_%(t)s' % {'p': product, 't': tagName}
    print "I will build bundle: %s " % tag
	
    """Export the project from the Subversion repository"""
    local("rm -rf new")
    local('%(c)s %(l)s/%(r)s new/' %\
          {'c': env.repository['command'],\
           'l': env.repository['trunk_url'],\
           'r': product}, True)
    today = datetime.datetime.now().ctime()
    local('find new -type d -name .git -exec rm -rf {} +', True)
    local('find new -type d -name .idea -exec rm -rf {} +', True)

    prev = _get_previous_builds(tag)
    if prev:
        buildnum = str(int(max(prev)['build']) + 1).zfill(3)
    else:
        buildnum = '001'

    local('echo "Tag: %(r)s - Build %(b)s - Built: %(t)s" > %(d)s/version.txt' % {'r': tag, 'b': buildnum, 't': today, 'd': 'new'}, True)

    rollname = tag + "--" + buildnum + ".tar.bz2"
    tar = tarfile.open(rollname, "w:bz2")
    tar.add('new')
    tar.add('new/version.txt')
    tar.close()
    if not os.path.isdir(env.repository['tag_url']):
        local('mkdir %s/' % env.repository['tag_url'], True)

    local('mv %(f)s %(d)s' % {'f': rollname, 'd': env.repository['tag_url']}, True)
    local("rm -rf new", True)

# Builds a dictionary of existing bundles on the deployment server
def _get_previous_builds(tag=None):
    # create list
    prevBuilds = []

    # loop through directory listing looking for .bz2 files
    # take bz2 files and append their stats in dictionary form to the
    # list created above.
    if os.path.isdir(env.repository['tag_url']):
        for filename in os.listdir(env.repository['tag_url']):
            if filename.endswith('bz2'):
                btag, build = filename.rsplit('--', 1)
                buildnum = build.split('.')[0]
                if tag:
                    if tag == btag:
                        prevBuilds.append({'tag': btag, 'build': buildnum, 'filename': filename})
                else:
                    prevBuilds.append({'tag': btag, 'build': buildnum, 'filename': filename})

        # Sort list of dictionaries based on date and revision numbers
        prevBuilds.sort(key=itemgetter('tag', 'build'))
        
    # return created list
    return prevBuilds

# Builds a dictionary of existing bundles on the deployment server
def _get_products():
    # create list
    prods = list()

    # loop through the Dropbox web directory looking for directories that don't start with an underscore
    if os.path.isdir(env.repository['trunk_url']):
        for filename in os.listdir(env.repository['trunk_url']):                
        	if os.path.isdir(os.path.join(env.repository['trunk_url'], filename)) and not filename.startswith('_') and not filename == 'bin':
        	    prods.append(filename)

        prods.sort()
    
    # return created list
    return prods


# Reverts to the previous bundle for a particular project and environment
def _rollback(project):
    env.warn_only = True
    with cd('%(d)s' % {'d': env.deploy_base}):
        local('mv %(f)s/ %(f)s_rollback/' % {'f': project})
        local('mv %(f)s_previous/ %(f)s/' % {'f': project})
