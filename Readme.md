
Introduction
======================

[NBA League Pass](http://www.nba.com/leaguepass/) is an online service offering streaming video of NBA games.

This [XBMC](http://xbmc.org/) plugin features: 

* Archive and condensed games for the NBA 2012 and 2013 seasons. 
* Selection of video qualities (from 720p to 360p).
* Fanart and thumbnails.

The first version of this plugin was written by [robla](http://forum.xbmc.org/showthread.php?tid=124716). Petros Tsampoukas then modified it to work with the 2012 and 2013 NBA seasons.

Installation
=======================

### Requirements

It requires some extra Python modules, which can be installed as below:

    sudo pip install httplib2 py-dom-xpath

### Using mercurial



It has to be installed as an XBMC plugin. 

Changes
=======================

### Changelog:

    0.3- First released version
    0.2- Patched for the 2012-2013 season playoffs

### Potential new features:

* Better thumbnails: display both teams logos. If you are interested to help, let me know!
* Playoff mode: hide the next game of a playoff series
* Filter for favourite team: only show games from your three favourite teams

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
