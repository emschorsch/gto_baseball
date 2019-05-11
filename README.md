# baseball

[![Build Status](https://magnum.travis-ci.com/emschorsch/baseball.svg?token=z9WTWNatzJqPE3hUhg2m&branch=master)](https://magnum.travis-ci.com/emschorsch/baseball)

A python simulator to predict player stats

To get coverage from top level directory:

```
coverage run --source baseball -m py.test
coverage report
coverage html
```

To generate html docs navigate to docs/ and run:

```
make html
```

To get lines of code by file type and comment statistics run:

```
git ls-files | xargs cloc
```
