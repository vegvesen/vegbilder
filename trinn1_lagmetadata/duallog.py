#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Duallog

This module contains a function "setup()" that sets up dual logging. All 
subsequent log messages are sent both to the console and to a logfile. Log
messages are generated via the "logging" package.

https://github.com/acschaefer/duallog

Example:
    >>> import duallog
    >>> import logging
    >>> duallog.setup('mylogs')
    >>> logging.info('Test message')

If run, this module illustrates the usage of the duallog package.

Jan Kristian Jensen: Slight modifications to suit the "vegbilder" use case
"""


# Import required standard packages.
import datetime
import logging.handlers
import os

def duallogSetup(logdir='log', logname='mylog'):
    """ Set up dual logging to console and to logfile.

    When this function is called, it first creates the given directory. It then 
    creates a logfile and passes all log messages to come to it. The logfile
    name encodes the date and time when it was created, for example 
    "20181115-153559.txt". All messages with a log level of at least "WARNING" 

    are also forwarded to the console.

    Keywords:
        logdir: path of the directory where to store the log files. Both a
            relative or an absolute path may be specified. If a relative path is
            specified, it is interpreted relative to the working directory.
            If no directory is given, the logs are written to a folder called 

            "log" in the working directory. 

        logname: Prefix for the generated log file

    """

    # Create the root logger.
    logger = logging.getLogger()

    # Sjekker om det finnes "handlers" fra før. 
    # I så fall skal vi ikke klusse med dem, men respektere at andre funksjoner kan 
    # ha satt opp sitt eget system. 
    if len(  logger.handlers) > 0: 
        logger.info( "duallog.duallogSetup: Logger finnes fra før, klusser ikke med den" ) 
    else: 

        logger.setLevel(logging.INFO)

        # 

        # Validate the given directory.
        logdir = os.path.normpath(logdir)

        # Create a folder for the logfiles.
        if not os.path.exists(logdir):
            os.makedirs(logdir)

        # Construct the logfile name.
        t = datetime.datetime.now()
        logfile = '{year:04d}{mon:02d}{day:02d}-' \
            '{hour:02d}{min:02d}{sec:02d}.log'.format(
                year=t.year, mon=t.month, day=t.day, 
                hour=t.hour, min=t.minute, sec=t.second)
        logfile = logname + logfile
        logfile = os.path.join(logdir, logfile)

        # Set up logging to the logfile.
        filehandler = logging.handlers.RotatingFileHandler(
            filename=logfile,
            maxBytes=10*1024*1024,
            backupCount=100)
        filehandler.setLevel(logging.INFO)
        fileformatter = logging.Formatter( '%(asctime)s %(levelname)-8s: %(message)s' )
        filehandler.setFormatter(fileformatter)
        
        logger.addHandler(filehandler)
        
        
        streamhandler = logging.StreamHandler()
        streamhandler.setLevel(logging.INFO)
        streamformatter = logging.Formatter('%(levelname)s: %(message)s')
        streamhandler.setFormatter(streamformatter)
        logger.addHandler(streamhandler)



if __name__ == '__main__':

    """Illustrate the usage of the duallog package.

    """



    # Set up dual logging.

    logdir = 'log'
    logname = 'thisIsMyLog'
    duallogSetup(logdir=logdir, logname=logname)


    # Generate some log messages.
    logging.debug('Debug messages are only sent to the logfile. (CHANGED for vegbilder-case!)')
    logging.info('Info messages are not shown on the console, too. (CHANGED for vegbilder-case!)')
    logging.warning('Warnings appear both on the console and in the logfile.')
    logging.error('Errors get the same treatment.')
    logging.critical('And critical messages, of course.')
    
    