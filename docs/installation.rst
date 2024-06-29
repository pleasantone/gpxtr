Installation
============

.. _installation:

Install this library in a virtual environment using `venv`_. `venv`_ is a tool
that creates isolated Python environments. These isolated environments can have
separate versions of Python packages, which allows you to isolate one project's
dependencies from the dependencies of other projects.

With `venv`_, it's possible to install this library without needing system
install permissions, and without clashing with the installed system
dependencies.

.. _`venv`: https://docs.python.org/3/library/venv.html


Mac/Linux
^^^^^^^^^

.. code-block:: console

    python3 -m venv <your-env>
    source <your-env>/bin/activate
    pip install gpxtable


Windows
^^^^^^^

.. code-block:: console

    py -m venv <your-env>
    .\<your-env>\Scripts\activate
    pip install gpxtable[web]


Also included in the package is an optional web service component using `wsgi_`.
If you are comfortable with WSGI services and wish to play with this service,
substitute `gpxtable` above with `"gpxtable[web]"` when installing with PIP.

.. `wsgi`: https://wsgi.readthedocs.io/en/latest/learn.html