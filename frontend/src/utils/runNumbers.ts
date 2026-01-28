// Utility functions for converting between run number formats

/**
 * Convert array of numbers to compact string representation
 * Groups consecutive numbers into ranges for better readability
 *
 * @param runList - Array of run numbers (sorted)
 * @returns Compact string representation (e.g., "1-5, 8, 10-12")
 */
export function formatRunNumbers(runList: number[]): string {
  if (runList.length === 0) return ''

  // Group consecutive numbers into ranges
  const ranges: string[] = []
  let start = runList[0]
  let prev = runList[0]

  for (let i = 1; i < runList.length; i++) {
    const curr = runList[i]
    if (curr === prev + 1) {
      // Consecutive
      prev = curr
    } else {
      // Break in sequence
      if (start === prev) {
        ranges.push(start.toString())
      } else {
        ranges.push(`${start}-${prev}`)
      }
      start = curr
      prev = curr
    }
  }

  // Add last range
  if (start === prev) {
    ranges.push(start.toString())
  } else {
    ranges.push(`${start}-${prev}`)
  }

  return ranges.join(', ')
}

/**
 * Parse string representation of run numbers into array
 * Supports individual numbers and ranges (e.g., "1,2,3" or "1-5, 8, 10-15")
 *
 * @param runNumbers - String representation of run numbers
 * @returns Sorted array of unique run numbers
 */
export function parseRunNumbers(runNumbers: string): number[] {
  if (!runNumbers.trim()) return []

  const parsedRuns: number[] = []
  const parts = runNumbers.split(',').map(part => part.trim())

  for (const part of parts) {
    if (part.includes('-')) {
      // Handle range (e.g., 1-5)
      const [start, end] = part.split('-').map(n => parseInt(n.trim()))
      if (!isNaN(start) && !isNaN(end) && start <= end) {
        for (let i = start; i <= end; i++) {
          parsedRuns.push(i)
        }
      }
    } else {
      // Handle individual number
      const num = parseInt(part)
      if (!isNaN(num)) {
        parsedRuns.push(num)
      }
    }
  }

  // Remove duplicates and sort from small to big
  return [...new Set(parsedRuns)].sort((a, b) => a - b)
}

/**
 * Validate run number string format
 *
 * @param runNumbers - String to validate
 * @returns True if valid, error message if invalid
 */
export function validateRunNumbers(runNumbers: string): true | string {
  if (!runNumbers) return 'Run numbers are required'

  // Allow empty string after trimming (user might clear it)
  if (runNumbers.trim() === '') return true

  // Pattern to match: numbers separated by commas, with optional ranges (e.g., 1,2,3 or 1-5, 8, 10-15)
  const pattern = /^\s*(?:\d+(?:-\d+)?)(?:\s*,\s*\d+(?:-\d+)?)*\s*$/

  if (!pattern.test(runNumbers)) {
    return 'Invalid format. Use comma-separated numbers or ranges (e.g., 1,2,3 or 1-5, 8, 10-15)'
  }

  // Additional validation: ensure ranges are valid (start <= end)
  const parts = runNumbers.split(',').map(part => part.trim())
  for (const part of parts) {
    if (part.includes('-')) {
      const [start, end] = part.split('-').map(n => parseInt(n.trim()))
      if (isNaN(start) || isNaN(end) || start > end) {
        return `Invalid range: ${part}. Start must be less than or equal to end.`
      }
    }
  }

  return true
}
