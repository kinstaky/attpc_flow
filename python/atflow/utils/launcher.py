import logging
import zmq

class AlignedFormatter(logging.Formatter):
	"""Custom formatter that aligns all log levels perfectly with colors."""

	def __init__(self, log_colors=None):
		super().__init__()
		self.log_colors = log_colors or {}
		self.color_codes = {
			'DEBUG': '\033[36m',    # cyan
			'INFO': '\033[32m',     # green
			'WARNING': '\033[33m',  # yellow
			'ERROR': '\033[31m',    # red
			'CRITICAL': '\033[35m', # magenta
		}
		self.reset_code = '\033[0m'

	def format(self, record):
		level_name = record.levelname

		# Apply colors
		color = self.color_codes.get(level_name, '')
		reset = self.reset_code if color else ''

		# Normalize all levels to match uvicorn's format exactly
		if level_name == 'INFO':
			level_display = f"{color}INFO{reset}:     "
		elif level_name == 'DEBUG':
			level_display = f"{color}DEBUG{reset}:    "
		elif level_name == 'ERROR':
			level_display = f"{color}ERROR{reset}:    "
		elif level_name == 'WARNING':
			level_display = f"{color}WARNING{reset}:  "
		elif level_name == 'CRITICAL':
			level_display = f"{color}CRITICAL{reset}: "
		else:
			level_display = f"{color}{level_name}{reset}:"

		message = record.getMessage()
		return f"{level_display}{message}"

def setup_logging(
	level=logging.INFO,
	log_file: str | None = None
):
	root = logging.getLogger()
	root.handlers.clear()
	root.setLevel(level)

	formatter = AlignedFormatter()
	formatter.ALIGN = True

	if log_file:
		handler = logging.FileHandler(log_file, mode='w')
	else:
		handler = logging.StreamHandler()
	handler.setFormatter(formatter)
	root.addHandler(handler)

def send_terminal_message():
	"""This function sends terminal message to zmq socket."""
	ctx = zmq.Context()
	publisher = ctx.socket(zmq.PUSH)
	publisher.connect("ipc://@attpc_flow_zmq")
	publisher.send_string("termination")