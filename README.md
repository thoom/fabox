Fabox
=====

I was working on some personal projects the other day, and I wanted to add my code to version control. I've gotten so used to ensuring that my code is backed up (primarily using SVN) that it makes me nervous to only rely on Time Machine for my backups.

While I was investigating free/cheap svn and git solutions (github was not an option because I don't want a public repo for this work), I realized that I had the perfect backup solution already: *Dropbox*. I'm sure I'm like most people and have at least a free Dropbox account. If not feel free to get a free 2GB account using this [referral link and get an extra 250MB][1].

 [1]: http://db.tt/MSfDXv9p

## Why Dropbox?

Dropbox is a popular way to share files across computers and mobile devices. I have had an account for years and appreciate its simplicity. I have several other people that I share folders with and use it frequently to move files to my iPhone and iPad.

What you may not know is that Dropbox comes standard with a 30 day version history. This means that every time you save a file, Dropbox will keep a copy of the old version available for you for a month. If you want, you can also upgrade your account to have unlimited version history but for most use cases I think 30 days is plenty.

Since I'm the primary or sole developer on many of my side projects, this simple versioning system was perfect for my needs. I don't anticipate needing anything like tags or branching, though honestly it wouldn't be hard to just create a copy of the code and stick it in another folder for a pseudo-tagging system. (See the deployment section for an example of how this might work).

## Using Dropbox as a Deployment tool

After the initial idea of using Dropbox as a VCS, my thoughts went to using it as part of a deployment tool. One of my areas of expertise involves configuration management and deployment. Since most of the code I've worked with used SVN, I've written several deployment tools based on it. I figured that I could build a similar system with Dropbox and my favorite deployment tool: [*Python's fabric*][2].

 [2]: http://fabfile.org

### Dropbox on the server

Setting up Dropbox on my server was pretty simple but required a little bit of preparation since I had very specific goals.

1.  Only sync specific folders
2.  Always have an up-to-date copy of code

#### Enabling specific folders

There are a few ways to synchronize specific folders with Dropbox. The easiest way, and the way that I went is to create a new Dropbox account. Then I share the folders I want on the server with this new account.

Now when I installed the Dropbox command line client, I attach it to this new account. The great thing with using a separate account is that I can use the account to store backups of my deployment bundles. This keeps the bundles out of personal Dropbox, but also allows me to potentially share the backups with other web servers.

#### Up-to-date code

Dropbox provides a nice python script to manage the daemon. If you are using Ubuntu, you can enable autostart simply:

    python dropbox.py autostart
    

Using Amazon's Linux, you can use cron to enable the daemon on start. Just add the following to your user's crontab:

    @reboot $HOME/.dropbox-dist/dropboxd
    

### Deployment tool

The deployment tool that we're going to build is based on Fabric. Since the set up right now is pretty basic, I'm not using much of its power, but by building on top of it, I can extend it easily as I need.

Install fabric

Since I'm currently running on Amazon Linux, I'll explain what I did. Ubuntu/Debian installs will probably differ.

To install fabric, we're going to use Python's **easy_install**. We need to do the following:

    yum install gcc python-devel
    easy_install fabric
    

#### Fabfile.py

We need to create a fabfile.py wherever we plan on running fabric. Since I am just creating a simple local deployment, I want my fabfile to do the following:

1.  Present a list of web applications available for deployment
2.  Create a tar of the application I want deployed with a unique identifier
3.  Add the tarred files to my Dropbox server repo
4.  Present a list of tarred files available for deployment
5.  Create a backup of the existing code that is easy to rollback
6.  Move the tarred code to the correct location
7.  Perform application specific tasks
    1.  Warm-up any caches
    2.  Create any symlinks
    3.  Repair permissions

#### Deployment

Rather than explain all of the features of my fabfile, I've posted it to my [github][3] for download and tweaking. I've tried to make it generic enough to where you can just put the file in your Dropbox user's home folder and run it.

 [3]: https://github.com/thoom/fabox

Any of your personal application options would go into the _deploy function.

Deployments are pretty simple. It is currently a two step process:

    fab tag
    fab prod deploy
    

*Tag* will take the folder you want deployed and create a tarred gz file. *Deploy* will take the tarred gz file and put it in the /var/www directory along with creating the backup, etc. There are a few other options available. just type

    fab help
    

to learn about any other options available.