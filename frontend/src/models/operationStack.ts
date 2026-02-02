
export interface Operation<T extends any[] = [], R = any> {
	call: (...params: T) => R,
	parameters: T,
}

export interface OperationPair<
	Tredo extends any[] = [],
	Tundo extends any[] = [],
	Rredo = any,
	Rundo = any,
> {
	redo: Operation<Tredo, Rredo>,
	undo: Operation<Tundo, Rundo>,
	bind: boolean,
}

export class OperationStack {
	private stack: OperationPair<any[], any[], any, any>[] = [];
	private top: number = 0;

	constructor() {
		this.stack = []
		this.top = 0
	}

	// push new operation, find pair from register and push pair to stack at top, delete things behind stack
	push<Tredo extends any[], Tundo extends any[], Rredo = any, Rundo = any>(
		pair: OperationPair<Tredo, Tundo, Rredo, Rundo>
	): void {
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
			operation.redo.call(...operation.redo.parameters)
			this.top++
		}
		while (this.top < this.stack.length && this.stack[this.top-1].bind) {
			const operation = this.stack[this.top]
			operation.redo.call(...operation.redo.parameters)
			this.top++
		}
	}

	// move top 1 step to bottom and call undo
	undo(): void {
		if (this.top > 0) {
			this.top--
			const operation = this.stack[this.top]
			operation.undo.call(...operation.undo.parameters)
		}
		while (this.top > 0 && this.stack[this.top-1].bind) {
			this.top--
			const operation = this.stack[this.top]
			operation.undo.call(...operation.undo.parameters)
		}
	}

	// clear all operation
	clear(): void {
		this.stack = [];
		this.top = 0;
	}
}