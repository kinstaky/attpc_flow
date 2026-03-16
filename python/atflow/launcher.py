"""
Simple launcher functions for ATTPC Flow.
Lightweight alternative to the manager class.
"""
import argparse

def main():
	"""Main entry point for command line interface."""
	parser = argparse.ArgumentParser(description="ATTPC Flow launcher")
	subparsers = parser.add_subparsers(dest='command', help='Available commands')

	# Server command
	webui_parser = subparsers.add_parser('webui', help='Start ATTPC Flow server')
	webui_parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
	webui_parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
	webui_parser.add_argument(
		"--end-point",
		default="ipc://@attpc_flow_zmq",
		help="ZMQ endpoint to bind to"
	)
	webui_parser.add_argument("--verbose", action="store_true", help="Show debug information.")


	# Workflow command
	workflow_parser = subparsers.add_parser('workflow', help='Run a workflow from file')
	workflow_parser.add_argument("workflow_file", help="Path to workflow file")
	workflow_parser.add_argument("--verbose", action="store_true", help="Show debug information.")
	workflow_parser.add_argument("--dry-run", action="store_true", help="Initialize the processor but do not execute tasks")

	# Node command
	node_parser = subparsers.add_parser('node', help='Run a single node')
	node_parser.add_argument("name", nargs='?', help="Name of the node to run")
	node_parser.add_argument('--list', '-l', action='store_true', help='List available nodes')
	node_parser.add_argument("--verbose", action="store_true", help="Show verbose run node information.")
	node_parser.add_argument('node_args', nargs=argparse.REMAINDER,
						   help='Arguments to pass to the node (e.g., --value 42)')

	subparsers.add_parser("dev", help="Run development server")

	args = parser.parse_args()

	if args.command == "webui":
		from .commands.webui import start_webui
		start_webui(
			host=args.host,
			port=args.port,
			end_point=args.end_point,
			verbose=args.verbose
		)
	elif args.command == "workflow":
		from .commands.workflow import process_workflow
		process_workflow(
			args.workflow_file,
			verbose=args.verbose,
			dry_run=args.dry_run
		)
	elif args.command == "node":
		from .commands.node import run_node
		run_node(args.name, args.node_args, args.verbose, args.list)
	elif args.command == "dev":
		from .commands.dev import start_dev_servers
		start_dev_servers()
	else:
		parser.print_help()