To test for DV table propagation and stabilization:
- Run
```
./test_base.sh <topology>
```
- allow the DV tables to stabalize

To testing for the handling of node failures:
- Run
```
./test_base.sh <topology>
```
- allow the DV tables to stabalize
- kill a node by running `pgrep Dvr.py` and selecting a node to kill (check this with ps 'pid' and then kill with kill 'pid')
- allow the DV tables to stabalize
