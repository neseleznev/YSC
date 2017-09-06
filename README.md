# YSC
Present bunch of scripts was used to prepare the paper for Youth Science Conference 2017.
As it was done quickly, code is ugly, but self-explanatory.
Contributions are highly appreciated.

Take a look at the bottom of `usa.py` and `russia.py` in order to
launch experiments.

## Installation

We recommend you to use a virtual environment for this project.
Read more [here][venv-python]

```sh
$ git clone https://github.com/neseleznev/YSC
$ cd YSC
$ python -m venv .venv
$ source .venv/bin/activate  # for Windows ".venv/scripts/activate"
(.venv) $ pip install -r requirements.txt
```

If you have troubles with requirements installation, ensure that you don't
have any spaces in path to your python interpreter. If so, create it in
another place.
If you still have problems, follow installation process for
[linux][venv-linux], [windows][venv-windows] or [os x][venv-osx].

## License

This project is licensed under the terms of the [GNU GPLv3](LICENSE) license.



[//]: # (these are reference links used in the body of this note and get stripped out when the markdown processor does its job. there is no need to format nicely because it shouldn't be seen. thanks so - http://stackoverflow.com/questions/4823468/store-comments-in-markdown-syntax)

   [venv-python]: <https://docs.python.org/3/library/venv.html>
   [venv-linux]: <http://docs.python-guide.org/en/latest/dev/virtualenvs/>
   [venv-windows]: <https://zignar.net/2012/06/17/install-python-on-windows/>
   [venv-osx]: <http://www.marinamele.com/2014/07/install-python3-on-mac-os-x-and-use-virtualenv-and-virtualenvwrapper.html>
   [InfluenzaInstitute]: <http://www.influenza.spb.ru/en/>
