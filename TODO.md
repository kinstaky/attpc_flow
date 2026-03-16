# Todo
## Analysis
- [ ] wrap spyral point cloud phase
- [ ] check trace

## UI
- [x] beautify task progress
- [x] delete node, delete link
- [x] all tab MUST attach to file
- [x] undo and redo
- [x] unify workflow graph edit command: pop_node, push_node, insert_node, delete_node, ..link, move node,
- [x] change to unsave when edit node property, worksapce, core, run
- [x] history execution and status
- [x] versbose options for workflow and node command
- [x] discarded/cached task
- [x] fail task
- [x] memory of executing
- [ ] queued execution
- [ ] dependency to node itself

### tabs
- [x] welcome page for no tabs
- [ ] test rename, delete, save tab
- [ ] implement copy tab
- [ ] implement saveas tab

### nodes
- [x] attpc_merger rust->python
- [x] check merged
- [x] node category
- [x] record bad events
- [ ] renew bad events, first delete the old bad events, then create new bad events

## processor
- [x] special treatment to "run_loader", less discard
- [x] adapt workflow in processor
- [ ] dependency to node itself

## framework
- [x] run statiscs (time, size, trigger...)
- [x] run tag, experiment valid, data valid, merged, checked merge.
- [x] better launch, run w/o UI
- [x] execution log: time, node and node version
- [ ] execution node version control
- [x] execution workspace record
- [x] memory of execution log and execution status
- [x] memory of last opened workflow
- [x] sqlite node meta
- [ ] is it good to overwrite the older node log when the new one just cached?
- [ ] move attpc_flow_cpp to package
- [x] solve frontend dependency and let uv handle frontend
- [ ] instant nodes without execution

## run tag
- [x] write new run tag
- [x] write tag after check_graw_event_id
- [x] use sqlite instead of parquet

## other
- [ ] better dialog in TopAppBar and FloatingButtons
- [ ] remove check_graw_event_id and move it into attpc_merger_wrapper