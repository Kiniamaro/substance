Installation
============

Substance supports all three main desktop operating systems: macOS, Windows,
and Linux. Its main prerequisite is `Oracle VirtualBox`_, which also supports
these platforms.

On macOS
--------

Substance is not compatible with the Python distribution that ships with macOS.
You must use `Homebrew`_ to install the latest Python 2.x release.

#. Download and install `Oracle VirtualBox`_. Make sure ``VBoxManage`` is in
   your ``PATH`` environment variable.
#. Make sure Xcode CLI is installed::

    $ xcode-select --install

#. Ensure `Homebrew`_ is installed::

    $ /usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"

#. Install Homebrew's Python distribution::

    $ brew install python

#. Make sure that running the command ``python`` executes the one under
   ``/usr/local/bin``::

    $ which python
    /usr/local/bin/python
    $ which pip
    /usr/local/bin/pip

   If this command outputs some other path like ``/usr/bin/python``, you're in
   trouble. You should add the following line to your ``.profile`` or
   ``.bash_profile`` file::

     export PATH=/usr/local/bin:$PATH

   Start a new terminal, and that should fix the issue (test it with the
   ``which`` commands above). The command ``brew doctor`` can also help with
   ``PATH``-related problems.

#. Ensure pip is up to date::

    $ sudo pip install -U pip

#. Install ``substance``::

    $ sudo pip install substance

#. Finally, install ``watchdog``, which is required for ``substance sync``
   under macOS::

    $ sudo pip install watchdog

On Windows
----------

Due to poor support for command-line utilities on Windows, Cygwin is required
to run Substance on Windows.

Disclaimer: Substance has only been tested on Windows 10 Pro 64-bit edition.
Installation on 32-bit Windows is NOT supported.

#. Install `Oracle VirtualBox`_. Make sure VBoxManage is in your ``PATH``
   environment variable (System -> Advanced System Settings -> Environment
   Variables -> Path -> add path to your VirtualBox installation directory).
#. Install Cygwin 64-bit. Here are the steps:

   #. Create a directory ``C:\cygwin64`` on your main drive. Create a subdirectory
      named "setup" inside that directory.
   #. Download ``setup-x86-64.exe`` from ``https://www.cygwin.com/`` and place
      it in ``C:\cygwin64\setup``
   #. Double-click on ``setup-x86-64.exe``, and perform the install. Keep the
      default location and make sure the following packages are selected:

      * ``mintty`` (under "Shells")
      * ``make`` (under "Devel")
      * ``git`` (under "Devel")
      * ``gcc-core`` (under "Devel")
      * ``python2`` (under "Python")
      * ``python2-devel`` (under "Python")
      * ``libffi-devel`` (under "Libs")
      * ``openssl-devel`` (under "Net")

   #. Optionally, you can create a shortcut to ``setup-x86-64.exe`` and add it
      to your Start menu; you can re-run the setup whenever you want to add or
      remove packages to your Cygwin install.

#. Launch Cygwin Terminal (``mintty``). All the magic happens from there!
#. Run ``which python && which pip`` to make SURE that you are running both
   executables from ``/usr/bin``, NOT something like ``C:\Python``!
#. Execute the command ``python --version``. You should see an output like
   ``Python 2.7.12``.
#. Make sure ``pip`` is installed and is upgraded to the latest version by running
   the commands::

     $ python -m ensurepip
     $ pip install -U pip

#. Install ``substance``::

     $ pip install substance

On Linux
--------

Make sure you are running a 64-bit Linux distribution. 32-bit is NOT supported.
Substance has been tested on Mint, Ubuntu, and Arch Linux.

#. Install `Oracle VirtualBox`_. Make sure ``VBoxManage`` is in your ``PATH``
   environment variable.
#. Install the following software using your package manager. Of course,
   depending on the distribution, the package names may slightly vary (but you
   will usually find a proper equivalent):

   * ``git``
   * ``build-essential``
   * ``libffi-devel``
   * ``openssl-devel``

#. Make sure to have Python 2 available. On some distributions (like Ubuntu
   14.04), this is the default Python interpreter, which means you can use
   ``python`` and ``pip``. On other, more state-of-the-art distributions (like
   Arch), you need to install a separate ``python2`` package and use the
   commands ``python2`` and ``pip2`` for the rest of this guide. Also install
   ``python-devel`` or ``python2-devel``, depending on your distribution.

#. Install ``substance``::

     $ sudo pip install substance

Upgrading Substance to a new version
------------------------------------

On all supported platforms, these commands will allow you to update the
Substance on your machine without losing data or engines::

  $ sudo pip uninstall substance
  $ sudo pip install substance

.. _Oracle VirtualBox: https://www.virtualbox.org/wiki/Downloads
.. _Homebrew: https://brew.sh/

