/**
 * Models sometimes emit GFM tables on a single line, e.g.
 *   | Col | Col | |---|---| | Row | Row |
 * remark-gfm requires newline-separated rows. We only rewrite lines that look
 * like tables (contain both `|` and `---`) to avoid touching normal prose.
 */
export function normalizeChatMarkdown(source: string): string {
  return source
    .split('\n')
    .map(line => {
      if (!line.includes('|') || !line.includes('---')) {
        return line
      }
      let s = line
      for (let i = 0; i < 40; i++) {
        const next = s
          // Header (or any row) glued to delimiter row: "...| |---" or "...| | ---"
          .replace(/\|\s+\|(\s*-{3,})/g, '|\n|$1')
          // Delimiter or cell row glued to next row: "...| |NextCell"
          .replace(/\|\s+\|(\s*[^\s|])/g, '|\n|$1')
        if (next === s) break
        s = next
      }
      return s
    })
    .join('\n')
}
