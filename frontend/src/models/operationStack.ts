export interface OperationPair {
	redo: () => void,
	undo: () => void,
	bind: boolean,
}

export class OperationStack {
	private stack: OperationPair[] = [];
	private top: number = 0;

	constructor() {
		this.stack = []
		this.top = 0
	}

	// push new operation, find pair from register and push pair to stack at top, delete things behind stack
	push(pair: OperationPair): void {
		// Remove any operations after current top (new branch)
		this.stack = this.stack.slice(0, this.top)
		// Add new operation pair at current top position
		this.stack.push(pair)
		// Move top to the new top
		this.top = this.stack.length
	}

	// call redo and move top 1 step to top
	redo(): void {
		if (this.top < this.stack.length) {
			const operation = this.stack[this.top]
			operation.redo()
			this.top++
		}
		while (this.top < this.stack.length && this.stack[this.top-1].bind) {
			const operation = this.stack[this.top]
			operation.redo()
			this.top++
		}
	}

	// move top 1 step to bottom and call undo
	undo(): void {
		if (this.top > 0) {
			this.top--
			const operation = this.stack[this.top]
			operation.undo()
		}
		while (this.top > 0 && this.stack[this.top-1].bind) {
			this.top--
			const operation = this.stack[this.top]
			operation.undo()
		}
	}

	// clear all operation
	clear(): void {
		this.stack = [];
		this.top = 0;
	}
}