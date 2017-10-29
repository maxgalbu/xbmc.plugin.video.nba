# NBA League pass [![Build Status](https://travis-ci.org/maxgalbu/xbmc.plugin.video.nba.svg?branch=master)](https://travis-ci.org/maxgalbu/xbmc.plugin.video.nba)

***As of October 2017, in order to login correctly, you need to go into the addon settings and change your username with your account's email.***

## Introduction

[International NBA League Pass](http://www.nba.com/leaguepass/) is an online service offering streaming video of NBA games.

This [XBMC](http://xbmc.org/) plugin features:

* Archive and condensed games for the current NBA season and previous seasons, starting from 2012/2013
* Home and Away feeds for archive games
* Highlights and Top Plays
* NBA TV live (League Pass Premium is required)
* Live game support
* Fanart from feeds, and thumbnails

The first version of this plugin was written by [robla](http://forum.xbmc.org/showthread.php?tid=124716). Petros Tsampoukas then modified it to work with the 2012 and 2013 NBA seasons, and added images. It requires a valid International League Pass account.


## Installation

### Requirements

As of 24 March 2014, all games require XBMC/Kodi v13 (Gotham) or higher versions. The archive and condensed games used to work in Frodo but the streams switched to using encryption with HLS, which does not work with Frodo due to faulty cookie support.

### From the kodi repositories

Go into Addons > Install from repository > Video Addons > NBA League Pass > Install

### Using a zip file

First download the latest version from the [download page](https://bitbucket.org/maxgalbu/plugin.video.nba/downloads#available-downloads). Then install the addon from a zip file in xbmc ([instructions](http://wiki.xbmc.org/index.php?title=Add-on_manager#How_to_install_from_a_ZIP_file)).

You can also download an unreleased (nightly) version from [GitHub releases](https://github.com/maxgalbu/xbmc.plugin.video.nba/releases/download/latest/plugin.video.nba-latest.zip). This version is automatically updated every time a commit is made to the repository, so it always has the latest changes.

### Using git

    #if you are on OSX/linux:
    cd ~/.xbmc/addons

    #if you are on Windows:
    cd c:\Users\<username>\AppData\Roaming\XBMC\addons

    #Clone the repository:
    git clone https://github.com/maxgalbu/xbmc.plugin.video.nba

    #To get the latest changes:
    git pull

Issues and discussions
=======================

If you have a bug to report, please report it on [BitBucket](https://bitbucket.org/maxgalbu/plugin.video.nba/issues?status=new&status=open) or [GitHub](https://github.com/maxgalbu/xbmc.plugin.video.nba/issues).

If you have a question or want to discuss an improvement, please head to the [Kodi forums topic for this plugin](http://forum.kodi.tv/showthread.php?tid=124716).

Changes
=======================

### Changelog:

See changelog.txt

### Potential new features:

* Better thumbnails: display both teams logos. If you are interested to help, let me know!
* Playoff mode: hide the next game of a playoff series
* Filter for favorite team: only show games from your three favorite teams

### Changelog of robla's version:

    0.1.6- bugfix for missing 2012 finals games
    0.1.1- bugfix for missing 2012 finals games
    0.1.0- added listing for complete 2011/2012 season
    0.0.9- fix for new domain watch.nba.com
    0.0.8- fix for playoff game recaps
    0.0.7- fix for archived playoff games
    0.0.6- fix for strange schedule js response
    0.0.5- apply quality settings for highlights, high = 720p
    0.0.4- added highlights and scores
    0.0.3- video idx check
    0.0.2- initial release
    0.0.1- initial test version

### Producing a new zip version

    zip -r plugin.video.nba.v0_6_6.zip -x\*/.hg/\* -x\*/.hgignore -x\*/docs/\* -x\*/*.pyc -x\*/*.pyo plugin.video.nba/
