# Todo
## UI
- [x] beautify task progress
- [x] delete node, delete link
- [x] all tab MUST attach to file
- [x] undo and redo
- [x] unify workflow graph edit command: pop_node, push_node, insert_node, delete_node, ..link, move node,
- [x] change to unsave when edit node property, worksapce, core, run
- [x] history execution and status

### tabs
- [x] welcome page for no tabs
- [ ] test rename, delete, save tab
- [ ] implement copy tab
- [ ] implement saveas tab

### nodes
- [ ] attpc_merger rust->python
- [ ] check merged
- [x] node category
- [x] record bad events

## processor
- [x] special treatment to "run_loader", less discard
- [x] adapt workflow in processor

## framework
- [x] run statiscs (time, size, trigger...)
- [x] run tag, experiment valid, data valid, merged, checked merge.
- [x] better launch, run w/o UI
- [x] execution log: time, node and node version
- [ ] execution node version control
- [x] execution workspace record
- [x] memory of execution log and execution status
- [x] memory of last opened workflow
- [ ] sqlite node meta

## run tag
- [x] write new run tag
- [x] write tag after check_graw_event_id
- [ ] use sqlite instead of parquet

## other
- [ ] better dialog in TopAppBar and FloatingButtons