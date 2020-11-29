# tcp device connector Library

### For all steps set username first (if not already set by system)
```bash
set USERNAME=XXXXXX
```


### Installation from Repository (online)
```bash
pip install git+https://github.com/srw2ho/tcpconnector.git
```

### Build distributable package (without dependencies -> online installation)
```bash
python setup.py bdist_wheel
```

### Download all dependencies (for offline installation)
```bash
cd dist

pip wheel git+https://github.com/srw2ho/tcpconnector.git

# copy dist to offline device

# install (on offline device)

```

### Usage
```python

```