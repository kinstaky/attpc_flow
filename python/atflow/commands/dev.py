import logging
import subprocess
import os

from ..utils.launcher import setup_logging
from .webui import start_webui

def start_dev_servers(verbose=False):
	"""Start both frontend and backend with hot reload for development."""

	# Set up logging
	setup_logging(
		level=logging.DEBUG if verbose else logging.INFO
	)
	logger = logging.getLogger(__name__)
	logger.info("Starting ATTPC Flow development servers...")

	# Get project root directory
	project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
	frontend_dir = os.path.join(project_root, "frontend")

	try:
		# Start frontend with Vite first, capturing output
		logger.info("Starting Vite frontend with hot reload...")
		frontend_cmd = ["pnpm", "dev", "--host"]
		frontend_proc = subprocess.Popen(
			frontend_cmd,
			cwd=frontend_dir,
			stdout=subprocess.PIPE,
			stderr=subprocess.STDOUT,
			universal_newlines=True,
			bufsize=1
		)

		# Start backend directly in main process for visible logs
		logger.info("Starting FastAPI backend with hot reload...")

		# Store original print function
		original_print = print

		# Add prefix to backend logs
		import builtins
		def prefixed_print(*args, **kwargs):
			original_print("[BACKEND] ", end='')
			original_print(*args, **kwargs)

		# Temporarily replace print for backend logs
		builtins.print = prefixed_print

		# Function to read and prefix frontend logs
		def read_frontend_output():
			for line in iter(frontend_proc.stdout.readline, ''):
				if line:
					# Use original print to avoid backend prefix
					original_print(f"[FRONTEND] {line}", end='')

		# Start thread to read frontend output
		import threading
		frontend_thread = threading.Thread(target=read_frontend_output)
		frontend_thread.start()

		try:
			# Run backend in main process so logs are visible
			start_webui(host="127.0.0.1", port=8000, verbose=verbose)
		finally:
			# Restore original print
			builtins.print = original_print

		# Wait for processes
		try:
			# Backend runs in main process, so just wait for frontend
			frontend_proc.wait()
		except KeyboardInterrupt:
			logger.info("Received interrupt signal, shutting down development servers...")
			frontend_proc.terminate()
			frontend_proc.wait()
			logger.info("Development servers stopped")

	except Exception as e:
		logger.error(f"Failed to start development servers: {e}")