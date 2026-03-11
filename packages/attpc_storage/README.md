# ATTPC Storage

HDF5 storage helpers and storage-boundary nodes for ATTPC Flow.

This package provides:

- `Hdf5Reader`
- `Hdf5Writer`
- `Hdf5ReaderNode`
- `Hdf5WriterNode`
- `Hdf5CheckpointNode`

The reader and writer are the primary programmatic API. The node classes are
thin wrappers for workflow use.
