#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" 
Демон запуска задач Python.

Установка демона в Ubuntu Linux:
Создать файл icdaemon в /etc/init.d

Содержание:

-------------------------------------------------------------------------------
# !/bin/sh
# /etc/init.d/icdaemon

### BEGIN INIT INFO
# Provides:          icdaemon
# Required-Start:    $network
# Required-Stop:     $network
# Default-Start:     2
# Default-Stop:      0 6
# Description:       Start icservices daemon
### END INIT INFO

case "$1" in
        start)
                /usr/bin/python /path/to/icdaemon/icdaemon.py start
        ;;

        stop)
                /usr/bin/python /path/to/icdaemon/icdaemon.py stop
        ;;

        restart)
               /usr/bin/python /path/to/icdaemon/icdaemon.py restart
        ;;

        *)
                echo "Usage: $0 start | stop | restart " >&2
                exit 1
        ;;
esac
exit 0
-------------------------------------------------------------------------------

После этого можно управлять демоном:

sudo /etc/init.d/icdaemon start
sudo /etc/init.d/icdaemon stop
sudo /etc/init.d/icdaemon restart

Добавление в автозагрузку демона:
sudo update-rc.d icdaemon defaults
Удаление из автозагрузки:
sudo update-rc.d -f icdaemon remove

Сообщения icdaemon:
/tmp/icdaemon.out

Ошибки icdaemon:
/tmp/icdaemon.err
"""

import sys
import os
import os.path
import traceback
import time
import atexit
from signal import SIGTERM 
import config

__version__ = (0, 1, 1, 1)


class icDaemon:
    """
    A generic daemon class.
    
    Usage: subclass the Daemon class and override the run() method
    """
    
    def __init__(self, pidfile, 
                 stdin='/dev/null', stdout='/dev/null', stderr='/dev/null'):
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.pidfile = pidfile

    def daemonize(self):
        """
        do the UNIX double-fork magic, see Stevens' 'Advanced 
        Programming in the UNIX Environment' for details (ISBN 0201563177)
        http://www.erlenstar.demon.co.uk/unix/faq_2.html#SEC16
        """
        if config.DEBUG_MODE:
            print('INFO. DEMONIZE')
            
        if config.DEBUG_MODE:
            print('INFO. #1 fork')
            
        try: 
            pid = os.fork() 
            if pid > 0:
                # exit first parent
                sys.exit(0) 
        except OSError as e:
            sys.stderr.write('ERROR! fork #1 failed: %d (%s)\n' % (e.errno, e.strerror))
            print('ERROR! fork #1 failed: %d (%s)\n' % (e.errno, e.strerror))
            sys.exit(1)

        # decouple from parent environment
        os.chdir('/') 
        os.setsid() 
        os.umask(0) 

        # do second fork
        if config.DEBUG_MODE:
            print('INFO. #2 fork')
            
        try: 
            pid = os.fork() 
            if pid > 0:
                # exit from second parent
                sys.exit(0) 
        except OSError as e:
            sys.stderr.write('ERROR! fork #2 failed: %d (%s)\n' % (e.errno, e.strerror))
            print('ERROR! fork #2 failed: %d (%s)\n' % (e.errno, e.strerror))
            sys.exit(1) 

        # redirect standard file descriptors
        if config.DEBUG_MODE:
            print('INFO. redirect standard file descriptors')
        
        sys.stdout.flush()
        sys.stderr.flush()
        si = open(self.stdin, 'r')
        so = open(self.stdout, 'a+')
        se = open(self.stderr, 'a+', 0)
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())

        # write pidfile
        if config.DEBUG_MODE:
            print('INFO. write pidfile', self.pidfile)
        atexit.register(self.delpid)
        pid = str(os.getpid())

        pid_file = open(self.pidfile, 'w+')
        pid_file.write('%s\n' % pid)
        pid_file.close()

        if config.DEBUG_MODE:
            print('INFO. write pidfile', os.path.exists(self.pidfile))

    def is_ok_pidfile(self):
        """
        Checking the correctness of initializing the PID file.
        @return: True - PID the file is filled correctly.
            False - error writing PID file.
        """
        return os.path.exists(self.pidfile) and bool(os.path.getsize(self.pidfile))

    def delpid(self):
        os.remove(self.pidfile)

    def start(self):
        """
        Start the daemon
        """
        if config.DEBUG_MODE:
            print('INFO. START')
            
        # Check for a pidfile to see if the daemon already runs
        try:
            pf = open(self.pidfile, 'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None

        if config.DEBUG_MODE:
            print('INFO. Check for a pidfile to see if the daemon already runs', pid)
            
        if pid:
            message = 'pidfile %s already exist. Daemon already running?\n'
            sys.stderr.write(message % self.pidfile)
            sys.exit(1)

        # Start the daemon
        self.daemonize()
        self.run()

    def stop(self):
        """
        Stop the daemon
        """
        if config.DEBUG_MODE:
            print('INFO. STOP')
            
        # Get the pid from the pidfile
        try:
            pf = open(self.pidfile, 'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None
        if config.DEBUG_MODE:
            print('INFO. Get the pid from the pidfile', pid)

        if not pid:
            message = 'pidfile %s does not exist. Daemon not running?\n'
            sys.stderr.write(message % self.pidfile)
            return  # not an error in a restart

        # Try killing the daemon process
        if config.DEBUG_MODE:
            print('INFO. Try killing the daemon process')
            
        try:
            while 1:
                os.kill(pid, SIGTERM)
                time.sleep(0.1)
        except OSError as err:
            err = str(err)
            if err.find('No such process') > 0:
                if os.path.exists(self.pidfile):
                    os.remove(self.pidfile)
            else:
                print(str(err))
                sys.exit(1)

    def restart(self):
        """
        Restart the daemon
        """
        self.stop()
        self.start()

    def run(self):
        """
        You should override this method when you subclass Daemon. It will be called after the process has been
        daemonized by start() or restart().
        """
        pass


class icTaskDaemon(icDaemon):
    """
    Демон запуска выполнения задач Python.
    """
    
    def __init__(self, *args, **kwargs):
        """
        Конструктор.
        """
        icDaemon.__init__(self, *args, **kwargs)
        
    def run(self):
        """
        Функция запуска демона.
        Переопределяется в потомке демона.
        """
        print('For EXIT press <Ctrl+C> ...')

        # Основной цикл обработки
        while 1:
            # Сделаем задержку между циклами выполнения
            time.sleep(config.LOOP_SLEEP)
            try:
               self.work()
            except KeyboardInterrupt:
                if config.DEBUG_MODE:
                    print('INFO. Stop icdaemon')
                break

    def work(self):
        """
        Функция цикла обработки задач.
        """
        for task in config.TASKS:
            if task:
                try:
                    task()
                except:
                    if config.DEBUG_MODE:
                        print('TASK ERROR.', traceback.format_exc())
            # Сделаем задержку между выполнением задач
            time.sleep(config.TASK_SLEEP)


def daemon_control(*args, **kwargs):
    """
    Функция запуска/останова демона.
    """
    
    if config.DEBUG_MODE:
        print('INFO. icServicesDaemon in debug mode') 
        daemon = icTaskDaemon('/tmp/icdaemon.pid',
                              stdout='/tmp/icdaemon.out',
                              stderr='/tmp/icdaemon.err')
    else:
        daemon = icTaskDaemon('/tmp/icdaemon.pid')
        
    if len(args) == 1:
        if 'start' == args[0]:
            daemon.start()
        elif 'stop' == args[0]:
            daemon.stop()
        elif 'restart' == args[0]:
            daemon.restart()
        else:
            print('Unknown command: %s' % args)
            sys.exit(2)
        sys.exit(0)
    else:
        print('Usage: python icdaemon.py start|stop|restart')
        sys.exit(2)    


if __name__ == '__main__':
    daemon_control(*sys.argv[1:])
